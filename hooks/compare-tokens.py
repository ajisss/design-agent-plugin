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


if __name__ == "__main__":
    print("compare-tokens.py: fungsi dasar siap, CLI penuh menyusul di Task 2")
