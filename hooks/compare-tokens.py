#!/usr/bin/env python3
"""
compare-tokens.py — bandingkan dua file JSON hasil extract-styles.py
(referensi vs hasil build) token-per-token, bukan pixel-per-pixel.

Kenapa bukan pixel diff: pixel diff gampang kotor oleh perbedaan panjang
teks (placeholder vs konten asli referensi yang sengaja tidak disalin —
lihat skills/build/SKILL.md langkah 2.5). Perbandingan token numerik kebal
terhadap itu karena tidak pernah menyentuh isi teks.

Cara pakai:
    python3 hooks/compare-tokens.py <reference.json> <build.json>
"""
import json
import sys

DEFAULT_TOLERANCES = {
    "spacing_px": 2,
    "radius_px": 2,
    "font_size_px": 2,
    "line_height_px": 2,
    "color_distance": 30,
}


def hex_to_rgb(hex_str):
    h = hex_str.lstrip("#")
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))


def color_distance(hex_a, hex_b):
    ra, ga, ba = hex_to_rgb(hex_a)
    rb, gb, bb = hex_to_rgb(hex_b)
    return ((ra - rb) ** 2 + (ga - gb) ** 2 + (ba - bb) ** 2) ** 0.5


def compare_numeric(a, b, tolerance):
    if a == b:
        return "match"
    if abs(a - b) <= tolerance:
        return "close"
    return "mismatch"


def compare_color(hex_a, hex_b, tolerance):
    dist = color_distance(hex_a, hex_b)
    if dist == 0:
        return "match"
    if dist <= tolerance:
        return "close"
    return "mismatch"


def _compare_typography(ref_list, build_list, tol):
    out = []
    for i in range(min(len(ref_list), len(build_list))):
        r, b = ref_list[i], build_list[i]
        out.append({
            "font_size": compare_numeric(r["font_size"], b["font_size"], tol["font_size_px"]),
            "line_height": compare_numeric(r["line_height"], b["line_height"], tol["line_height_px"]),
            "font_weight": "match" if r["font_weight"] == b["font_weight"] else "mismatch",
            "font_family": "match" if r["font_family"] == b["font_family"] else "mismatch",
            "color": compare_color(r["color"], b["color"], tol["color_distance"]),
        })
    return out


def _compare_buttons(ref_list, build_list, tol):
    out = []
    for i in range(min(len(ref_list), len(build_list))):
        r, b = ref_list[i], build_list[i]
        out.append({
            "background_color": compare_color(r["background_color"], b["background_color"], tol["color_distance"]),
            "color": compare_color(r["color"], b["color"], tol["color_distance"]),
            "border_radius": compare_numeric(r["border_radius"], b["border_radius"], tol["radius_px"]),
            "padding": "match" if r["padding"] == b["padding"] else "mismatch",
            "box_shadow": "match" if r["box_shadow"] == b["box_shadow"] else "mismatch",
        })
    return out


def _compare_containers(ref_list, build_list, tol):
    out = []
    for i in range(min(len(ref_list), len(build_list))):
        r, b = ref_list[i], build_list[i]
        out.append({
            "border_radius": compare_numeric(r["border_radius"], b["border_radius"], tol["radius_px"]),
            "box_shadow": "match" if r["box_shadow"] == b["box_shadow"] else "mismatch",
            "padding": "match" if r["padding"] == b["padding"] else "mismatch",
            "gap": compare_numeric(r["gap"], b["gap"], tol["spacing_px"]),
        })
    return out


def compare_sections(ref_data, build_data, tolerances=None):
    tol = tolerances or DEFAULT_TOLERANCES
    ref_sections = ref_data["sections"]
    build_sections = build_data["sections"]

    if len(ref_sections) == len(build_sections):
        structural = "match"
    elif len(build_sections) < len(ref_sections):
        structural = "missing_in_build"
    else:
        structural = "extra_in_build"

    missing_section_indexes = list(range(len(build_sections), len(ref_sections)))
    extra_section_indexes = list(range(len(ref_sections), len(build_sections)))

    section_results = []
    for i in range(min(len(ref_sections), len(build_sections))):
        r, b = ref_sections[i], build_sections[i]
        section_results.append({
            "index": i,
            "typography": _compare_typography(r["typography"], b["typography"], tol),
            "buttons": _compare_buttons(r["buttons"], b["buttons"], tol),
            "containers": _compare_containers(r["containers"], b["containers"], tol),
        })

    build_colors = build_data["colors"]["dominant"]
    missing_colors = [
        c for c in ref_data["colors"]["dominant"]
        if not any(color_distance(c, bc) <= tol["color_distance"] for bc in build_colors)
    ]

    return {
        "structural": structural,
        "missing_section_indexes": missing_section_indexes,
        "extra_section_indexes": extra_section_indexes,
        "sections": section_results,
        "missing_colors": missing_colors,
    }


def _has_mismatch(diff):
    if diff["structural"] != "match":
        return True
    if diff["missing_colors"]:
        return True
    for section in diff["sections"]:
        for category in ("typography", "buttons", "containers"):
            for item in section[category]:
                if "mismatch" in item.values():
                    return True
    return False


def main():
    if len(sys.argv) < 3:
        print("Usage: compare-tokens.py <reference.json> <build.json>")
        sys.exit(1)

    with open(sys.argv[1]) as f:
        ref_data = json.load(f)
    with open(sys.argv[2]) as f:
        build_data = json.load(f)

    diff = compare_sections(ref_data, build_data)
    print(json.dumps(diff, indent=2))

    sys.exit(1 if _has_mismatch(diff) else 0)


if __name__ == "__main__":
    main()
