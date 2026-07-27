import os
import importlib.util

spec = importlib.util.spec_from_file_location(
    "extract_styles", os.path.join(os.path.dirname(__file__), "..", "extract-styles.py")
)
extract_styles = importlib.util.module_from_spec(spec)
spec.loader.exec_module(extract_styles)


def test_rgb_string_to_hex():
    assert extract_styles.rgb_string_to_hex("rgb(79, 70, 229)") == "#4f46e5"
    assert extract_styles.rgb_string_to_hex("rgb(255, 255, 255)") == "#ffffff"


def test_aggregate_extraction_maps_colors_to_hex():
    raw_sections = [{
        "index": 0,
        "bbox": {"y": 0, "width": 1440, "height": 812},
        "headings": [{
            "level": 1, "font_size": 40, "font_weight": "700", "line_height": 48,
            "font_family": "Inter, sans-serif", "color": "rgb(17, 24, 39)",
        }],
        "buttons": [{
            "background_color": "rgb(79, 70, 229)", "color": "rgb(255, 255, 255)",
            "border_radius": 8, "padding": "12px 24px", "box_shadow": "none",
        }],
        "containers": [{
            "border_radius": 12, "box_shadow": "none", "padding": "24px", "gap": 16,
        }],
    }]
    color_freq = {"rgb(255, 255, 255)": 20, "rgb(79, 70, 229)": 5, "rgb(17, 24, 39)": 8}

    result = extract_styles.aggregate_extraction(raw_sections, color_freq)

    assert result["colors"]["dominant"][0] == "#ffffff"  # frekuensi tertinggi duluan
    assert result["sections"][0]["typography"][0]["color"] == "#111827"
    assert result["sections"][0]["buttons"][0]["background_color"] == "#4f46e5"
    assert result["sections"][0]["bbox"] == {"y": 0, "width": 1440, "height": 812}


def test_aggregate_extraction_preserves_section_order():
    raw_sections = [
        {"index": 0, "bbox": {"y": 0, "width": 100, "height": 100},
         "headings": [], "buttons": [], "containers": []},
        {"index": 1, "bbox": {"y": 100, "width": 100, "height": 100},
         "headings": [], "buttons": [], "containers": []},
    ]
    result = extract_styles.aggregate_extraction(raw_sections, {})
    assert [s["index"] for s in result["sections"]] == [0, 1]
