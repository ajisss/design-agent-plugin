import os
import importlib.util
import tempfile
from PIL import Image

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


def test_crop_section_screenshots_writes_one_file_per_section():
    with tempfile.TemporaryDirectory() as tmp:
        full_page_path = os.path.join(tmp, "full.png")
        Image.new("RGB", (1440, 1600), color="white").save(full_page_path)

        sections = [
            {"index": 0, "bbox": {"y": 0, "width": 1440, "height": 800}},
            {"index": 1, "bbox": {"y": 800, "width": 1440, "height": 800}},
        ]
        output_dir = os.path.join(tmp, "sections")
        paths = extract_styles.crop_section_screenshots(full_page_path, sections, output_dir)

        assert len(paths) == 2
        assert all(os.path.exists(p) for p in paths)
        cropped = Image.open(paths[0])
        assert cropped.size == (1440, 800)


def test_crop_section_screenshots_clamps_overflow():
    """Verify that crop_section_screenshots clamps bbox overflow to image height."""
    with tempfile.TemporaryDirectory() as tmp:
        full_page_path = os.path.join(tmp, "full.png")
        # Create a 1000px tall image
        Image.new("RGB", (1440, 1000), color="white").save(full_page_path)

        # Define a section that claims to go from y=900 to y=1400 (height=500)
        # but the image is only 1000px tall, so it should be clamped to 100px
        sections = [
            {"index": 0, "bbox": {"y": 900, "width": 1440, "height": 500}},
        ]
        output_dir = os.path.join(tmp, "sections")
        paths = extract_styles.crop_section_screenshots(full_page_path, sections, output_dir)

        assert len(paths) == 1
        assert os.path.exists(paths[0])
        cropped = Image.open(paths[0])
        # bottom = min(900 + 500, 1000) = 1000
        # So crop height = 1000 - 900 = 100
        assert cropped.size == (1440, 100)


def test_dominant_colors_from_image_orders_by_frequency():
    with tempfile.TemporaryDirectory() as tmp:
        img = Image.new("RGB", (100, 100), color=(255, 255, 255))
        # Paint a small red square (5x5 = 25px) into a mostly-white 100x100 image (10000px)
        # so white is clearly dominant and red is clearly secondary.
        for x in range(5):
            for y in range(5):
                img.putpixel((x, y), (255, 0, 0))
        img_path = os.path.join(tmp, "screenshot.png")
        img.save(img_path)

        colors = extract_styles.dominant_colors_from_image(img_path, top_n=2)

        assert len(colors) == 2
        assert colors[0] == "#ffffff"
        assert colors[1] == "#ff0000"


def test_dominant_colors_from_image_respects_top_n():
    with tempfile.TemporaryDirectory() as tmp:
        img = Image.new("RGB", (60, 60), color=(255, 255, 255))
        img_path = os.path.join(tmp, "solid.png")
        img.save(img_path)

        colors = extract_styles.dominant_colors_from_image(img_path, top_n=3)

        assert len(colors) <= 3
        assert colors[0] == "#ffffff"


def test_crop_section_screenshots_empty_sections():
    """Verify that crop_section_screenshots handles empty sections list gracefully."""
    with tempfile.TemporaryDirectory() as tmp:
        full_page_path = os.path.join(tmp, "full.png")
        Image.new("RGB", (1440, 1000), color="white").save(full_page_path)

        sections = []
        output_dir = os.path.join(tmp, "sections")
        paths = extract_styles.crop_section_screenshots(full_page_path, sections, output_dir)

        assert paths == []
