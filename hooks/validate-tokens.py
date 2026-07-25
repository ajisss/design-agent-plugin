#!/usr/bin/env python3
"""
validate-tokens.py — PostToolUse hook, dibundel sebagai bagian plugin
design-agent. Dipanggil otomatis lewat hooks/hooks.json setelah tool
Write/Edit selesai.

Karena ini jalan dari lokasi cache plugin (bukan dari root project user),
script ini pakai env var CLAUDE_PROJECT_DIR (disediakan Claude Code di semua
hook) buat nemuin registry project yang benar.

PostToolUse TIDAK bisa membatalkan tool call yang sudah jalan — hook ini
cuma kasih feedback balik ke Claude lewat stdout JSON supaya Claude
mengoreksi di giliran berikutnya.
"""
import json
import re
import sys
import os

RELEVANT_EXT = (".css", ".scss", ".tsx", ".jsx", ".ts", ".js", ".html", ".vue")


def registry_path():
    project_dir = os.environ.get("CLAUDE_PROJECT_DIR", os.getcwd())
    return os.path.join(project_dir, ".design", "registry", "specs.json")


def load_allowed_colors():
    path = registry_path()
    if not os.path.exists(path):
        return set()
    try:
        with open(path, "r") as f:
            data = json.load(f)
    except Exception:
        return set()

    allowed = set()
    for spec in data.get("specs", []):
        colors = spec.get("tokens", {}).get("colors", {})
        for _, field in colors.items():
            value = field.get("value", "")
            match = re.findall(r"#[0-9a-fA-F]{3,8}", value)
            allowed.update(m.lower() for m in match)
    return allowed


def main():
    try:
        payload = json.load(sys.stdin)
    except Exception:
        sys.exit(0)  # kalau input tidak valid, jangan block apapun

    file_path = payload.get("tool_input", {}).get("file_path", "")
    if not file_path.endswith(RELEVANT_EXT):
        sys.exit(0)

    if not os.path.exists(file_path):
        sys.exit(0)

    allowed = load_allowed_colors()
    if not allowed:
        # Belum ada spec tervalidasi — tidak ada yang bisa dibandingkan.
        sys.exit(0)

    with open(file_path, "r", errors="ignore") as f:
        content = f.read()

    used = set(m.lower() for m in re.findall(r"#[0-9a-fA-F]{3,8}", content))
    unknown = used - allowed

    if unknown:
        message = (
            f"[validate-tokens] {file_path} pakai hex color di luar spec: "
            f"{', '.join(sorted(unknown))}. Token yang diizinkan: "
            f"{', '.join(sorted(allowed))}. Cek lagi apakah ini disengaja "
            f"atau harus diganti sesuai .design/registry/specs.json."
        )
        print(message, file=sys.stderr)
        print(json.dumps({
            "hookSpecificOutput": {
                "hookEventName": "PostToolUse",
                "additionalContext": message
            }
        }))
    sys.exit(0)


if __name__ == "__main__":
    main()
