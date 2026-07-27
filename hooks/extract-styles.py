#!/usr/bin/env python3
"""
extract-styles.py — ekstrak computed style asli dari sebuah halaman (URL
referensi live ATAU dev server hasil build) via Playwright, jadi JSON
terstruktur. Dipakai /design-agent:spec (untuk referensi) dan
/design-agent:build (untuk hasil build) supaya token dibandingkan dari
angka terukur, bukan tebakan visual.

Cara pakai:
    python3 hooks/extract-styles.py <url> <output.json> [--screenshots-dir <dir>]

Butuh: playwright + pillow.
    pip install playwright pillow
    playwright install chromium
"""
import json
import sys


def rgb_string_to_hex(rgb_str):
    nums = rgb_str[rgb_str.index("(") + 1: rgb_str.index(")")].split(",")
    r, g, b = (int(n.strip()) for n in nums[:3])
    return "#{:02x}{:02x}{:02x}".format(r, g, b)


def _to_hex(value):
    return rgb_string_to_hex(value) if value.startswith("rgb") else value


def aggregate_extraction(raw_sections, color_freq):
    dominant = sorted(color_freq.items(), key=lambda kv: kv[1], reverse=True)
    dominant_hex = [_to_hex(color) for color, _count in dominant]

    sections = []
    for raw in sorted(raw_sections, key=lambda s: s["index"]):
        sections.append({
            "index": raw["index"],
            "bbox": raw["bbox"],
            "typography": [
                {**h, "color": _to_hex(h["color"])} for h in raw["headings"]
            ],
            "buttons": [
                {**btn, "background_color": _to_hex(btn["background_color"]),
                 "color": _to_hex(btn["color"])}
                for btn in raw["buttons"]
            ],
            "containers": list(raw["containers"]),
        })

    return {"colors": {"dominant": dominant_hex}, "sections": sections}


if __name__ == "__main__":
    print("extract-styles.py: fungsi agregasi siap, ekstraksi browser menyusul di Task 5")
