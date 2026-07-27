#!/usr/bin/env python3
"""
extract-styles.py — ekstrak computed style asli dari sebuah halaman (URL
referensi live ATAU dev server hasil build) via Playwright, jadi JSON
terstruktur. Dipakai /design-agent:spec (untuk referensi) dan
/design-agent:build (untuk hasil build) supaya token dibandingkan dari
angka terukur, bukan tebakan visual.

Cara pakai:
    python3 hooks/extract-styles.py <url> <output.json> [screenshots_dir]
    python3 hooks/extract-styles.py --from-image <screenshot.png> <output.json>

Mode kedua (--from-image) dipakai untuk referensi concept/non-fetchable:
sampling warna dominan langsung dari file screenshot via color quantization
(PIL), tanpa perlu browser/network.

Butuh: playwright + pillow.
    pip install playwright pillow
    playwright install chromium
"""
import json
import os
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


def crop_section_screenshots(full_page_path, sections, output_dir):
    from PIL import Image

    os.makedirs(output_dir, exist_ok=True)
    full_image = Image.open(full_page_path)
    paths = []
    for section in sorted(sections, key=lambda s: s["index"]):
        bbox = section["bbox"]
        top = bbox["y"]
        bottom = min(bbox["y"] + bbox["height"], full_image.height)
        crop = full_image.crop((0, top, bbox["width"], bottom))
        out_path = os.path.join(output_dir, f"section-{section['index']}.png")
        crop.save(out_path)
        paths.append(out_path)
    return paths


def dominant_colors_from_image(image_path, top_n=5):
    from PIL import Image

    img = Image.open(image_path).convert("RGB")
    img_small = img.resize((150, 150), Image.Resampling.NEAREST)
    quantized = img_small.quantize(colors=top_n, method=Image.Quantize.MEDIANCUT)
    palette = quantized.getpalette()
    color_counts = sorted(quantized.getcolors(), reverse=True, key=lambda item: item[0])

    hex_colors = []
    for _count, idx in color_counts[:top_n]:
        r, g, b = palette[idx * 3: idx * 3 + 3]
        hex_colors.append("#{:02x}{:02x}{:02x}".format(r, g, b))
    return hex_colors


_EXTRACT_JS = """
() => {
  function pickSections() {
    const candidates = Array.from(document.querySelectorAll('body > *'))
      .concat(Array.from(document.querySelectorAll('section, header, footer')));
    const seen = new Set();
    const sections = [];
    for (const el of candidates) {
      if (seen.has(el)) continue;
      const rect = el.getBoundingClientRect();
      if (rect.height < 80) continue; // skip elemen kecil (nav item, dsb)
      seen.add(el);
      sections.push(el);
    }
    return sections.sort((a, b) => a.getBoundingClientRect().top - b.getBoundingClientRect().top);
  }

  function styleOf(el) { return window.getComputedStyle(el); }

  const colorFreq = {};
  function tally(value) {
    if (!value || value === 'rgba(0, 0, 0, 0)' || value === 'transparent') return;
    colorFreq[value] = (colorFreq[value] || 0) + 1;
  }
  document.querySelectorAll('*').forEach((el) => {
    const s = styleOf(el);
    tally(s.backgroundColor);
    tally(s.color);
  });

  const sections = pickSections().map((el, index) => {
    const rect = el.getBoundingClientRect();
    const headings = Array.from(el.querySelectorAll('h1, h2, h3, h4')).slice(0, 3).map((h) => {
      const s = styleOf(h);
      return {
        level: parseInt(h.tagName[1], 10),
        font_size: parseFloat(s.fontSize),
        font_weight: s.fontWeight,
        line_height: parseFloat(s.lineHeight) || parseFloat(s.fontSize),
        font_family: s.fontFamily,
        color: s.color,
      };
    });
    const buttons = Array.from(el.querySelectorAll('button, a.button, [role="button"]')).slice(0, 3).map((b) => {
      const s = styleOf(b);
      return {
        background_color: s.backgroundColor,
        color: s.color,
        border_radius: parseFloat(s.borderRadius) || 0,
        padding: s.padding,
        box_shadow: s.boxShadow,
      };
    });
    const containers = Array.from(el.querySelectorAll('[class*="card"]')).slice(0, 3).map((c) => {
      const s = styleOf(c);
      return {
        border_radius: parseFloat(s.borderRadius) || 0,
        box_shadow: s.boxShadow,
        padding: s.padding,
        gap: parseFloat(s.gap) || 0,
      };
    });
    return {
      index,
      bbox: { y: Math.round(rect.top + window.scrollY), width: Math.round(rect.width), height: Math.round(rect.height) },
      headings, buttons, containers,
    };
  });

  return { sections, colorFreq };
}
"""


def run(url, output_json_path, screenshots_dir, viewport=None):
    from playwright.sync_api import sync_playwright

    viewport = viewport or {"width": 1440, "height": 900}

    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page(viewport=viewport)
        page.goto(url, wait_until="networkidle")
        raw = page.evaluate(_EXTRACT_JS)
        full_page_path = os.path.join(screenshots_dir, "_full-page.png")
        os.makedirs(screenshots_dir, exist_ok=True)
        page.screenshot(path=full_page_path, full_page=True)
        browser.close()

    result = aggregate_extraction(raw["sections"], raw["colorFreq"])
    section_screenshots = crop_section_screenshots(full_page_path, result["sections"], screenshots_dir)
    for section, path in zip(result["sections"], section_screenshots):
        section["screenshot_path"] = path

    with open(output_json_path, "w") as f:
        json.dump(result, f, indent=2)

    return result


def main():
    if len(sys.argv) >= 2 and sys.argv[1] == "--from-image":
        if len(sys.argv) < 4:
            print("Usage: extract-styles.py --from-image <screenshot.png> <output.json>")
            sys.exit(1)
        image_path, output_json_path = sys.argv[2], sys.argv[3]
        try:
            colors = dominant_colors_from_image(image_path)
        except ImportError:
            print("[extract-styles] Pillow belum terinstall.")
            print("Jalankan: pip install pillow")
            sys.exit(1)
        except Exception as exc:
            print(f"[extract-styles] Gagal ekstrak warna dari {image_path}: {exc}")
            sys.exit(1)

        with open(output_json_path, "w") as f:
            json.dump({"colors": {"dominant": colors}}, f, indent=2)

        print(f"[extract-styles] {len(colors)} warna dominan diekstrak dari {image_path}.")
        print(f"[extract-styles] Hasil tersimpan: {output_json_path}")
        sys.exit(0)

    if len(sys.argv) < 3:
        print("Usage: extract-styles.py <url> <output.json> [screenshots_dir]")
        sys.exit(1)

    url, output_json_path = sys.argv[1], sys.argv[2]
    screenshots_dir = sys.argv[3] if len(sys.argv) > 3 else os.path.join(
        os.path.dirname(output_json_path) or ".", "sections"
    )

    try:
        result = run(url, output_json_path, screenshots_dir)
    except ImportError:
        print("[extract-styles] Playwright/Pillow belum terinstall.")
        print("Jalankan: pip install playwright pillow && playwright install chromium")
        sys.exit(1)
    except Exception as exc:
        print(f"[extract-styles] Gagal ekstraksi dari {url}: {exc}")
        sys.exit(1)

    print(f"[extract-styles] {len(result['sections'])} section terdeteksi, "
          f"{len(result['colors']['dominant'])} warna dominan.")
    print(f"[extract-styles] Hasil tersimpan: {output_json_path}")
    sys.exit(0)


if __name__ == "__main__":
    main()
