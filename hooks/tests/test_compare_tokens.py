import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import importlib.util

spec = importlib.util.spec_from_file_location(
    "compare_tokens", os.path.join(os.path.dirname(__file__), "..", "compare-tokens.py")
)
compare_tokens = importlib.util.module_from_spec(spec)
spec.loader.exec_module(compare_tokens)


def test_hex_to_rgb():
    assert compare_tokens.hex_to_rgb("#ffffff") == (255, 255, 255)
    assert compare_tokens.hex_to_rgb("#000000") == (0, 0, 0)
    assert compare_tokens.hex_to_rgb("#4f46e5") == (79, 70, 229)


def test_color_distance_identical_is_zero():
    assert compare_tokens.color_distance("#4f46e5", "#4f46e5") == 0


def test_color_distance_far_colors_is_large():
    dist = compare_tokens.color_distance("#ffffff", "#000000")
    assert dist > 400


def test_compare_numeric_match():
    assert compare_tokens.compare_numeric(40, 40, tolerance=2) == "match"


def test_compare_numeric_close():
    assert compare_tokens.compare_numeric(40, 41.5, tolerance=2) == "close"


def test_compare_numeric_mismatch():
    assert compare_tokens.compare_numeric(40, 60, tolerance=2) == "mismatch"


def test_compare_color_match():
    assert compare_tokens.compare_color("#4f46e5", "#4f46e5", tolerance=30) == "match"


def test_compare_color_close():
    # #4f46e5 vs #4a41e0 -- beda tipis, harus "close" bukan "match"/"mismatch"
    assert compare_tokens.compare_color("#4f46e5", "#4a41e0", tolerance=30) == "close"


def test_compare_color_mismatch():
    assert compare_tokens.compare_color("#4f46e5", "#22c55e", tolerance=30) == "mismatch"
