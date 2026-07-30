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
    r, g, b = (int(float(n.strip())) for n in nums[:3])
    if len(nums) >= 4 and float(nums[3].strip()) == 0:
        # rgba(..., 0) = fully transparent — TIDAK sama dengan hitam solid.
        # Konversi buta ke "#000000" bikin elemen transparan (tombol tanpa
        # bg, overlay, dll) salah dibaca sebagai warna hitam opaque di
        # analisis kontras/konsistensi hilir (measured checks).
        return "transparent"
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
    # NEAREST (bukan default bicubic) biar downscale gak nyampur warna asli
    # jadi warna blended yang gak ada di source-nya.
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


def _goto_with_fallback(page, url):
    """Beberapa situs (embed form pihak ketiga seperti HubSpot, live chat
    widget, analytics polling) bikin network gak pernah benar-benar idle,
    jadi wait_until="networkidle" timeout walau halamannya sendiri sudah
    selesai render. Coba networkidle dulu (paling akurat — computed style
    dijamin sudah settle), fallback berjenjang kalau itu gagal supaya tetap
    dapat data daripada nyerah total.

    Return: nama strategi yang berhasil dipakai (buat dicatat di output,
    biar skill pemanggil tau seberapa "settle" data ini).
    """
    from playwright.sync_api import TimeoutError as PlaywrightTimeoutError

    try:
        page.goto(url, wait_until="networkidle", timeout=15000)
        return "networkidle"
    except PlaywrightTimeoutError:
        pass

    try:
        page.goto(url, wait_until="domcontentloaded", timeout=30000)
        # Jeda manual gantiin networkidle — cukup buat mayoritas konten
        # async (lazy image, font, komponen client-side) selesai render,
        # walau widget yang polling terus-menerus tetap gak akan "idle".
        page.wait_for_timeout(3000)
        return "domcontentloaded-fallback"
    except PlaywrightTimeoutError:
        pass

    # Situs benar-benar berat/lambat — percobaan terakhir paling minimal,
    # cuma nunggu response pertama diterima (HTML mungkin belum full-parsed).
    page.goto(url, wait_until="commit", timeout=45000)
    page.wait_for_timeout(5000)
    return "commit-fallback"


def _scroll_through_page(page, step_delay_ms=250):
    """Banyak landing page modern pakai scroll-reveal (IntersectionObserver:
    konten fade-in/slide-in baru dipicu saat elemen masuk viewport). Kalau
    screenshot langsung diambil di posisi scroll awal tanpa pernah discroll,
    section-section itu keburu ke-capture dalam keadaan kosong/transparan —
    padahal sebenarnya bukan gagal ekstraksi, cuma belum ke-trigger.
    Scroll bertahap dari atas ke bawah (lalu balik ke atas) supaya semua
    animasi reveal sempat jalan sebelum full-page screenshot diambil.
    """
    total_height = page.evaluate("document.body.scrollHeight")
    viewport_height = page.viewport_size["height"]
    if not total_height or not viewport_height:
        return
    steps = max(1, total_height // viewport_height)
    for i in range(steps + 1):
        page.evaluate(f"window.scrollTo(0, {i * viewport_height})")
        page.wait_for_timeout(step_delay_ms)
    page.evaluate("window.scrollTo(0, 0)")
    page.wait_for_timeout(step_delay_ms)


def _neutralize_fixed_position(page):
    """Playwright/Chromium full_page screenshot resize viewport ke tinggi
    penuh dokumen lalu re-render — elemen `position: fixed`/`sticky`
    (navbar, chat widget) yang harusnya nempel di viewport malah "kebeku"
    di posisi scroll terakhir sebelum resize, jadi kelihatan nyangkut di
    tengah halaman di screenshot (padahal user asli gak pernah lihat itu,
    fixed/sticky selalu nempel ke viewport beneran). Netralkan ke
    `position: static` SESAAT sebelum screenshot final — JS/CSS asli page
    sudah gak dipakai lagi setelah ini (browser langsung ditutup), jadi
    aman biarpun reflow jadi berantakan.
    """
    page.evaluate("""() => {
        document.querySelectorAll('*').forEach((el) => {
            const pos = getComputedStyle(el).position;
            if (pos === 'fixed' || pos === 'sticky') {
                el.style.setProperty('position', 'static', 'important');
            }
        });
    }""")


def run(url, output_json_path, screenshots_dir, viewport=None):
    from playwright.sync_api import sync_playwright

    viewport = viewport or {"width": 1440, "height": 900}

    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page(viewport=viewport)
        load_strategy = _goto_with_fallback(page, url)
        _scroll_through_page(page)
        raw = page.evaluate(_EXTRACT_JS)
        full_page_path = os.path.join(screenshots_dir, "_full-page.png")
        os.makedirs(screenshots_dir, exist_ok=True)
        _neutralize_fixed_position(page)
        page.screenshot(path=full_page_path, full_page=True)
        browser.close()

    result = aggregate_extraction(raw["sections"], raw["colorFreq"])
    result["meta"] = {"loadStrategy": load_strategy}
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
    strategy = result.get("meta", {}).get("loadStrategy", "networkidle")
    if strategy != "networkidle":
        print(f"[extract-styles] PERINGATAN: networkidle timeout, dipakai fallback "
              f"'{strategy}'. Halaman mungkin punya widget/polling yang bikin network "
              f"gak pernah idle (mis. live chat, form embed pihak ketiga). Data computed "
              f"style tetap diambil, tapi konten yang lazy-load lambat mungkin belum "
              f"sempat settle sepenuhnya.")
    print(f"[extract-styles] Hasil tersimpan: {output_json_path}")
    sys.exit(0)


if __name__ == "__main__":
    main()
