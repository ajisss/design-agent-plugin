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


def _sample(dominant_colors, sections):
    return {"colors": {"dominant": dominant_colors}, "sections": sections}


def _section(index, font_size=40, radius=8, btn_bg="#4f46e5"):
    return {
        "index": index,
        "bbox": {"y": index * 800, "width": 1440, "height": 800},
        "typography": [{
            "level": 1, "font_size": font_size, "font_weight": "700",
            "line_height": font_size + 8, "font_family": "Inter, sans-serif",
            "color": "#111827",
        }],
        "buttons": [{
            "background_color": btn_bg, "color": "#ffffff",
            "border_radius": radius, "padding": "12px 24px", "box_shadow": "none",
        }],
        "containers": [{
            "border_radius": radius, "box_shadow": "none",
            "padding": "24px", "gap": 16,
        }],
    }


def test_compare_sections_all_match():
    ref = _sample(["#4f46e5", "#ffffff"], [_section(0)])
    build = _sample(["#4f46e5", "#ffffff"], [_section(0)])
    result = compare_tokens.compare_sections(ref, build)
    assert result["structural"] == "match"
    assert result["sections"][0]["typography"][0]["font_size"] == "match"
    assert result["sections"][0]["buttons"][0]["background_color"] == "match"
    assert result["missing_colors"] == []


def test_compare_sections_detects_font_size_mismatch():
    ref = _sample(["#4f46e5"], [_section(0, font_size=40)])
    build = _sample(["#4f46e5"], [_section(0, font_size=24)])
    result = compare_tokens.compare_sections(ref, build)
    assert result["sections"][0]["typography"][0]["font_size"] == "mismatch"


def test_compare_sections_detects_missing_section():
    ref = _sample(["#4f46e5"], [_section(0), _section(1)])
    build = _sample(["#4f46e5"], [_section(0)])
    result = compare_tokens.compare_sections(ref, build)
    assert result["structural"] == "missing_in_build"
    assert result["missing_section_indexes"] == [1]


def test_compare_sections_detects_extra_section_as_no_reference():
    ref = _sample(["#4f46e5"], [_section(0)])
    build = _sample(["#4f46e5"], [_section(0), _section(1)])
    result = compare_tokens.compare_sections(ref, build)
    assert result["structural"] == "no_reference"
    assert result["extra_section_indexes"] == [1]


def test_compare_sections_detects_missing_color():
    ref = _sample(["#4f46e5", "#22c55e"], [_section(0)])
    build = _sample(["#4f46e5"], [_section(0)])
    result = compare_tokens.compare_sections(ref, build)
    assert result["missing_colors"] == ["#22c55e"]


def test_has_mismatch_false_when_only_no_reference():
    # Build punya section ekstra yang memang diminta user (bukan dari
    # referensi) — section yang cocok semuanya match, tidak ada warna
    # hilang. structural == "no_reference" saja TIDAK boleh dihitung
    # sebagai mismatch (ini yang bikin loop QA di /build bisa konvergen
    # untuk skenario section tambahan yang sah).
    ref = _sample(["#4f46e5"], [_section(0)])
    build = _sample(["#4f46e5"], [_section(0), _section(1)])
    result = compare_tokens.compare_sections(ref, build)
    assert result["structural"] == "no_reference"
    assert compare_tokens._has_mismatch(result) is False


def test_has_mismatch_true_when_missing_in_build():
    ref = _sample(["#4f46e5"], [_section(0), _section(1)])
    build = _sample(["#4f46e5"], [_section(0)])
    result = compare_tokens.compare_sections(ref, build)
    assert result["structural"] == "missing_in_build"
    assert compare_tokens._has_mismatch(result) is True


def test_compare_sections_matches_purely_by_position_not_content():
    # Dokumentasi behavior saat ini: compare_sections mencocokkan section
    # murni by index/urutan list, BUKAN by identitas semantik (mis. nama
    # class DOM atau isi heading). Section 0 di ref dan build di bawah ini
    # secara konseptual adalah "section" yang berbeda total (heading besar
    # vs kecil), tapi tetap dibandingkan satu sama lain karena sama-sama di
    # index 0. Test ini TIDAK menambah deteksi baru — hanya memastikan
    # (pin) behavior positional-matching yang sudah ada, sebagai
    # dokumentasi batasan yang disadari (lihat design spec).
    ref = _sample(["#4f46e5"], [_section(0, font_size=40)])
    build = _sample(["#4f46e5"], [_section(0, font_size=16)])
    result = compare_tokens.compare_sections(ref, build)
    assert result["structural"] == "match"
    assert result["sections"][0]["typography"][0]["font_size"] == "mismatch"
