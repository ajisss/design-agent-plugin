# Replikasi Presisi 1:1 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Ganti fondasi ekstraksi token & visual QA plugin `design-agent` dari "tebakan visual + pixel diff" jadi "pengukuran computed-style terstruktur + perbandingan token iteratif", supaya hasil `/design-agent:build` mendekati referensi 1:1.

**Architecture:** Satu tool ekstraksi Playwright (`extract-styles.py`) dijalankan di URL referensi live (dipakai `/spec`) dan di dev server hasil build (dipakai `/build`). Hasil dua ekstraksi itu dibandingkan token-per-token oleh `compare-tokens.py` — bukan pixel diff — untuk menggerakkan loop perbaikan iteratif di `/build`. Pixel diff (`visual-diff.py`) tetap ada tapi jadi bukti visual pelengkap, bukan penentu lolos/tidak.

**Tech Stack:** Python 3, Playwright (sync API), Pillow, pytest (dev-only, untuk unit test fungsi murni).

## Global Constraints

- Semua script baru harus bisa jalan standalone lewat `python3 <script>.py <args>` — konsisten dengan `visual-diff.py`/`validate-tokens.py` yang sudah ada (bukan diimpor sebagai module).
- Jangan tambah dependency baru di `hooks/requirements.txt` — `playwright` dan `pillow` sudah cukup untuk semua script baru.
- Fungsi yang butuh browser (Playwright) dan fungsi murni (transformasi data/perbandingan) harus dipisah ke fungsi berbeda, supaya fungsi murni bisa di-unit-test tanpa browser sungguhan.
- Ikuti gaya komentar Bahasa Indonesia yang sudah dipakai di `hooks/*.py` yang ada.
- Nama field/skema baru harus persis seperti di spec: `docs/superpowers/specs/2026-07-27-precise-replication-design.md`.

---

## File Structure

```
hooks/
  ├── extract-styles.py       (baru) — ekstraksi computed-style via Playwright
  ├── compare-tokens.py       (baru) — bandingkan 2 JSON hasil extract-styles.py
  ├── visual-diff.py          (modif) — fix bug resize-stretch
  └── tests/                 (baru, dev-only, tidak di-ship ke requirements.txt)
      ├── test_extract_styles.py
      ├── test_compare_tokens.py
      └── test_visual_diff.py
skills/
  ├── spec/
  │   ├── SKILL.md            (modif) — integrasi extract-styles.py + aturan confidence baru
  │   └── SCHEMA.md           (modif) — field measuredTokens + journal event baru
  └── build/
      └── SKILL.md            (modif) — loop QA iteratif token-based
README.md                     (modif) — update struktur plugin
.claude-plugin/plugin.json    (modif) — bump version 1.1.0 -> 1.2.0
```

---

### Task 1: `compare-tokens.py` — util warna & perbandingan numerik (pure functions)

**Files:**
- Create: `hooks/compare-tokens.py`
- Test: `hooks/tests/test_compare_tokens.py`

**Interfaces:**
- Produces: `hex_to_rgb(hex_str: str) -> tuple[int,int,int]`, `color_distance(hex_a: str, hex_b: str) -> float`, `compare_numeric(a: float, b: float, tolerance: float) -> str` (`"match"|"close"|"mismatch"`), `compare_color(hex_a: str, hex_b: str, tolerance: float) -> str`, `DEFAULT_TOLERANCES: dict`

- [ ] **Step 1: Buat folder test & tulis test yang gagal**

```bash
mkdir -p hooks/tests
```

`hooks/tests/test_compare_tokens.py`:
```python
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
```

- [ ] **Step 2: Jalankan test, pastikan gagal (file belum ada)**

Run: `pip install pytest && cd hooks && python3 -m pytest tests/test_compare_tokens.py -v`
Expected: FAIL — `FileNotFoundError` atau `ModuleNotFoundError` karena `compare-tokens.py` belum ada.

- [ ] **Step 3: Tulis implementasi minimal**

`hooks/compare-tokens.py`:
```python
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
```

- [ ] **Step 4: Jalankan test, pastikan lolos**

Run: `cd hooks && python3 -m pytest tests/test_compare_tokens.py -v`
Expected: PASS (8 tests)

- [ ] **Step 5: Commit**

```bash
git add hooks/compare-tokens.py hooks/tests/test_compare_tokens.py
git commit -m "feat: tambah util warna & perbandingan numerik di compare-tokens.py"
```

---

### Task 2: `compare-tokens.py` — perbandingan section & CLI

**Files:**
- Modify: `hooks/compare-tokens.py`
- Test: `hooks/tests/test_compare_tokens.py`

**Interfaces:**
- Consumes: `hex_to_rgb`, `color_distance`, `compare_numeric`, `compare_color`, `DEFAULT_TOLERANCES` (dari Task 1)
- Produces: `compare_sections(ref_data: dict, build_data: dict, tolerances: dict = DEFAULT_TOLERANCES) -> dict` — dikonsumsi oleh `skills/build/SKILL.md` (dipanggil lewat CLI, bukan diimpor)

Input `ref_data`/`build_data` mengikuti skema output `extract-styles.py` (didefinisikan di Task 3):
```json
{
  "colors": {"dominant": ["#4f46e5", "#ffffff", "#111827"]},
  "sections": [
    {
      "index": 0,
      "bbox": {"y": 0, "width": 1440, "height": 812},
      "typography": [{"level": 1, "font_size": 40, "font_weight": "700", "line_height": 48, "font_family": "Inter, sans-serif", "color": "#111827"}],
      "buttons": [{"background_color": "#4f46e5", "color": "#ffffff", "border_radius": 8, "padding": "12px 24px", "box_shadow": "none"}],
      "containers": [{"border_radius": 12, "box_shadow": "rgba(0,0,0,0.1) 0px 4px 6px", "padding": "24px", "gap": 16}]
    }
  ]
}
```

- [ ] **Step 1: Tambah test untuk `compare_sections`**

Tambahkan ke `hooks/tests/test_compare_tokens.py`:
```python
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
    assert result["structural"] == "extra_in_build"
    assert result["extra_section_indexes"] == [1]


def test_compare_sections_detects_missing_color():
    ref = _sample(["#4f46e5", "#22c55e"], [_section(0)])
    build = _sample(["#4f46e5"], [_section(0)])
    result = compare_tokens.compare_sections(ref, build)
    assert result["missing_colors"] == ["#22c55e"]
```

- [ ] **Step 2: Jalankan, pastikan gagal**

Run: `cd hooks && python3 -m pytest tests/test_compare_tokens.py -v`
Expected: FAIL pada 5 test baru — `AttributeError: module 'compare_tokens' has no attribute 'compare_sections'`

- [ ] **Step 3: Implementasikan `compare_sections` + CLI**

Ganti bagian bawah `hooks/compare-tokens.py` (baris `if __name__ ...` ke bawah) jadi:
```python
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
```

- [ ] **Step 4: Jalankan test, pastikan lolos**

Run: `cd hooks && python3 -m pytest tests/test_compare_tokens.py -v`
Expected: PASS (13 tests total)

- [ ] **Step 5: Commit**

```bash
git add hooks/compare-tokens.py hooks/tests/test_compare_tokens.py
git commit -m "feat: perbandingan section & CLI di compare-tokens.py"
```

---

### Task 3: `extract-styles.py` — agregasi data (pure functions)

**Files:**
- Create: `hooks/extract-styles.py`
- Test: `hooks/tests/test_extract_styles.py`

**Interfaces:**
- Produces: `rgb_string_to_hex(rgb_str: str) -> str`, `aggregate_extraction(raw_sections: list[dict], color_freq: dict[str,int]) -> dict` — output-nya adalah skema yang dikonsumsi `compare_sections` (Task 2) dan disimpan sebagai file JSON oleh Task 5.

Bentuk `raw_sections` (ini yang akan dihasilkan JS in-page di Task 5 — didefinisikan di sini dulu supaya Task 3 bisa ditest independen dari Playwright):
```json
[
  {
    "index": 0,
    "bbox": {"y": 0, "width": 1440, "height": 812},
    "headings": [{"level": 1, "font_size": 40, "font_weight": "700", "line_height": 48, "font_family": "Inter, sans-serif", "color": "rgb(17, 24, 39)"}],
    "buttons": [{"background_color": "rgb(79, 70, 229)", "color": "rgb(255, 255, 255)", "border_radius": 8, "padding": "12px 24px", "box_shadow": "none"}],
    "containers": [{"border_radius": 12, "box_shadow": "none", "padding": "24px", "gap": 16}]
  }
]
```

- [ ] **Step 1: Tulis test yang gagal**

`hooks/tests/test_extract_styles.py`:
```python
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
```

- [ ] **Step 2: Jalankan, pastikan gagal**

Run: `cd hooks && python3 -m pytest tests/test_extract_styles.py -v`
Expected: FAIL — file `extract-styles.py` belum ada.

- [ ] **Step 3: Implementasi minimal**

`hooks/extract-styles.py`:
```python
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
```

- [ ] **Step 4: Jalankan test, pastikan lolos**

Run: `cd hooks && python3 -m pytest tests/test_extract_styles.py -v`
Expected: PASS (3 tests)

- [ ] **Step 5: Commit**

```bash
git add hooks/extract-styles.py hooks/tests/test_extract_styles.py
git commit -m "feat: agregasi data ekstraksi style di extract-styles.py"
```

---

### Task 4: `extract-styles.py` — crop screenshot per section

**Files:**
- Modify: `hooks/extract-styles.py`
- Test: `hooks/tests/test_extract_styles.py`

**Interfaces:**
- Consumes: hasil `aggregate_extraction()["sections"]` (field `bbox`) dari Task 3
- Produces: `crop_section_screenshots(full_page_path: str, sections: list[dict], output_dir: str) -> list[str]` (list path file yang ditulis, urut sesuai index section)

- [ ] **Step 1: Tulis test yang gagal**

Tambahkan ke `hooks/tests/test_extract_styles.py`:
```python
import tempfile
from PIL import Image


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
```

- [ ] **Step 2: Jalankan, pastikan gagal**

Run: `cd hooks && python3 -m pytest tests/test_extract_styles.py -v`
Expected: FAIL — `AttributeError: module 'extract_styles' has no attribute 'crop_section_screenshots'`

- [ ] **Step 3: Implementasi**

Tambahkan di `hooks/extract-styles.py`, sebelum blok `if __name__ ...`:
```python
import os
from PIL import Image


def crop_section_screenshots(full_page_path, sections, output_dir):
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
```

- [ ] **Step 4: Jalankan test, pastikan lolos**

Run: `cd hooks && python3 -m pytest tests/test_extract_styles.py -v`
Expected: PASS (4 tests)

- [ ] **Step 5: Commit**

```bash
git add hooks/extract-styles.py hooks/tests/test_extract_styles.py
git commit -m "feat: crop screenshot per section di extract-styles.py"
```

---

### Task 5: `extract-styles.py` — Playwright glue & CLI penuh

**Files:**
- Modify: `hooks/extract-styles.py`

**Interfaces:**
- Consumes: `aggregate_extraction`, `crop_section_screenshots` (Task 3 & 4)
- Produces: `run(url: str, output_json_path: str, screenshots_dir: str, viewport: dict = None) -> dict` (dipanggil CLI; juga dipanggil manual saat verifikasi). Ini bagian yang butuh browser sungguhan — tidak ada unit test otomatis untuk fungsi ini (konsisten dengan `visual-diff.py` yang sudah ada, yang juga tidak punya automated test untuk bagian Playwright-nya); diverifikasi manual di Step 3.

- [ ] **Step 1: Tulis JS extraction script + fungsi `run()`**

Tambahkan di `hooks/extract-styles.py`, sebelum blok `if __name__ ...` (setelah `crop_section_screenshots`):
```python
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
```

- [ ] **Step 2: Tulis CLI**

Ganti blok `if __name__ ...` di akhir `hooks/extract-styles.py` jadi:
```python
def main():
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
```

- [ ] **Step 3: Verifikasi manual (butuh browser sungguhan, tidak bisa di-unit-test)**

Run:
```bash
pip install playwright pillow
playwright install chromium
python3 hooks/extract-styles.py https://stripe.com /tmp/stripe-styles.json /tmp/stripe-sections
cat /tmp/stripe-styles.json
```
Expected: exit code 0, `/tmp/stripe-styles.json` berisi JSON dengan `colors.dominant` (list hex) dan `sections` (list dengan `bbox`, `typography`, `buttons`, `containers`, `screenshot_path`), dan file screenshot per section ada di `/tmp/stripe-sections/`.

Juga cek kasus gagal:
```bash
python3 hooks/extract-styles.py https://situs-tidak-ada-xyz123.invalid /tmp/fail.json
```
Expected: exit code 1, pesan error jelas, bukan traceback mentah ke user.

- [ ] **Step 4: Jalankan seluruh test unit yang sudah ada, pastikan tidak ada regresi**

Run: `cd hooks && python3 -m pytest tests/ -v`
Expected: semua test dari Task 1-4 tetap PASS.

- [ ] **Step 5: Commit**

```bash
git add hooks/extract-styles.py
git commit -m "feat: Playwright glue & CLI penuh untuk extract-styles.py"
```

---

### Task 6: `visual-diff.py` — fix bug resize-stretch

**Files:**
- Modify: `hooks/visual-diff.py`
- Test: `hooks/tests/test_visual_diff.py`

**Interfaces:**
- Produces: `prepare_for_diff(ref: Image, res: Image) -> tuple[Image, Image, dict]` (dict berisi `{"reference_size": (w,h), "result_size": (w,h), "size_mismatch": bool}`)

Bug lama: `res.resize(ref.size)` men-stretch screenshot hasil biar ukurannya sama persis dengan referensi — kalau aspect ratio beda, distorsi ini bikin skor diff tidak valid.

- [ ] **Step 1: Tulis test yang gagal**

`hooks/tests/test_visual_diff.py`:
```python
import os
import importlib.util
from PIL import Image

spec = importlib.util.spec_from_file_location(
    "visual_diff", os.path.join(os.path.dirname(__file__), "..", "visual-diff.py")
)
visual_diff = importlib.util.module_from_spec(spec)
spec.loader.exec_module(visual_diff)


def test_prepare_for_diff_same_size_no_mismatch_flag():
    ref = Image.new("RGB", (800, 600), "white")
    res = Image.new("RGB", (800, 600), "white")
    ref_c, res_c, meta = visual_diff.prepare_for_diff(ref, res)
    assert ref_c.size == res_c.size == (800, 600)
    assert meta["size_mismatch"] is False


def test_prepare_for_diff_crops_to_common_region_without_stretching():
    ref = Image.new("RGB", (800, 600), "white")
    res = Image.new("RGB", (1000, 900), "white")  # aspect ratio beda
    ref_c, res_c, meta = visual_diff.prepare_for_diff(ref, res)
    # harus di-crop ke area overlap (800x600), BUKAN di-resize/stretch ke (800,600)
    assert ref_c.size == (800, 600)
    assert res_c.size == (800, 600)
    assert meta["size_mismatch"] is True
    assert meta["reference_size"] == (800, 600)
    assert meta["result_size"] == (1000, 900)
```

- [ ] **Step 2: Jalankan, pastikan gagal**

Run: `cd hooks && python3 -m pytest tests/test_visual_diff.py -v`
Expected: FAIL — `AttributeError: module 'visual_diff' has no attribute 'prepare_for_diff'`

- [ ] **Step 3: Implementasi & wire ke `main()`**

Tambahkan fungsi ini di `hooks/visual-diff.py`, sebelum `def main():`:
```python
def prepare_for_diff(ref, res):
    common_width = min(ref.width, res.width)
    common_height = min(ref.height, res.height)
    ref_cropped = ref.crop((0, 0, common_width, common_height))
    res_cropped = res.crop((0, 0, common_width, common_height))
    meta = {
        "reference_size": ref.size,
        "result_size": res.size,
        "size_mismatch": ref.size != res.size,
    }
    return ref_cropped, res_cropped, meta
```

Di `main()`, ganti baris:
```python
    res_resized = res.resize(ref.size)
    diff = ImageChops.difference(ref, res_resized)
```
jadi:
```python
    ref_cropped, res_cropped, size_meta = prepare_for_diff(ref, res)
    diff = ImageChops.difference(ref_cropped, res_cropped)
    if size_meta["size_mismatch"]:
        print(f"[visual-diff] PERINGATAN: ukuran beda — referensi {size_meta['reference_size']}, "
              f"hasil {size_meta['result_size']}. Diff dihitung dari area overlap saja "
              f"(bukan di-stretch), jadi skor di bawah ini hanya mewakili area yang overlap.")
```

- [ ] **Step 4: Jalankan test, pastikan lolos**

Run: `cd hooks && python3 -m pytest tests/test_visual_diff.py -v`
Expected: PASS (2 tests)

- [ ] **Step 5: Commit**

```bash
git add hooks/visual-diff.py hooks/tests/test_visual_diff.py
git commit -m "fix: hentikan stretch-resize di visual-diff.py, bandingkan area overlap"
```

---

### Task 7: `SCHEMA.md` — field `measuredTokens` & journal event baru

**Files:**
- Modify: `skills/spec/SCHEMA.md`

- [ ] **Step 1: Tambahkan field `measuredTokens` ke contoh JSON `specs[]`**

Di `skills/spec/SCHEMA.md`, tambahkan field baru persis setelah field `"buildMethod"` di contoh JSON `specs[]` (baris ~86 di versi saat ini):
```json
      "buildMethod": "standalone | superpowers | null",
      "measuredTokens": {
        "source": "extract-styles | vision",
        "referenceJsonPath": "string | null",
        "sections": [
          { "name": "hero", "screenshotPath": "string", "bbox": { "y": 0, "height": 800 } }
        ]
      },
      "status": "draft | validated | blocked | built",
```

Tambahkan juga penjelasan di bawah tabel confidence weight (setelah baris "Blokir (...)"):
```markdown
### `measuredTokens`
`source: "extract-styles"` berarti field token di spec ini diisi dari
data terukur (`hooks/extract-styles.py` dijalankan ke URL referensi live),
bukan tebakan visual — field yang bersumber dari sini boleh dilabeli
confidence `stated`. `source: "vision"` berarti referensi tidak fetchable
(screenshot statis atau situs terproteksi) sehingga ekstraksi tetap manual
lewat observasi visual — field dari sumber ini confidence-nya di-cap
maksimal `discussed`, tidak boleh `stated`.

`referenceJsonPath` menunjuk ke file JSON mentah hasil `extract-styles.py`
untuk referensi ini (dipakai `/design-agent:build` buat dibandingkan
dengan hasil build lewat `compare-tokens.py`). `sections[].bbox` dan
`screenshotPath` dipakai untuk QA per-section.
```

- [ ] **Step 2: Tambahkan journal event baru**

Di bagian daftar event types (baris terakhir file), ubah:
```markdown
Event types yang dipakai skill lain: `reference_selected`, `reference_rejected`,
`spec_extracted`, `spec_blocked`, `spec_reanalyzed`, `build_started`,
`build_method_overridden`, `visual_diff`, `build_completed`.
```
jadi:
```markdown
Event types yang dipakai skill lain: `reference_selected`, `reference_rejected`,
`spec_extracted`, `spec_blocked`, `spec_reanalyzed`, `build_started`,
`build_method_overridden`, `visual_diff`, `build_completed`,
`styles_extracted`, `token_compare`, `token_compare_converged`.
```

Dan tambahkan contoh event-nya di blok contoh journal.jsonl sebelum baris itu:
```json
{"ts":"ISO 8601","event":"styles_extracted","specId":"S-001","source":"live-url","refId":"R-001"}
{"ts":"ISO 8601","event":"token_compare","specId":"S-001","iteration":1,"mismatches":3}
{"ts":"ISO 8601","event":"token_compare_converged","specId":"S-001","iteration":2}
```

- [ ] **Step 3: Verifikasi manual**

Baca ulang `skills/spec/SCHEMA.md` penuh, pastikan tidak ada field yang disebut di prosa tapi tidak ada di contoh JSON (atau sebaliknya).

- [ ] **Step 4: Commit**

```bash
git add skills/spec/SCHEMA.md
git commit -m "docs: tambah field measuredTokens & event ekstraksi/perbandingan token ke SCHEMA.md"
```

---

### Task 8: `skills/spec/SKILL.md` — integrasi `extract-styles.py`

**Files:**
- Modify: `skills/spec/SKILL.md`

- [ ] **Step 1: Tambahkan sub-langkah baru sebelum "2. Amati referensi secara visual"**

Sisipkan section baru di antara langkah "1. Baca referensi terpilih" dan "2. Amati referensi secara visual":
```markdown
### 1.5. Ekstrak computed style asli (kalau referensinya live)
Untuk tiap referensi terpilih dengan `category: "real"` **dan** field
`url`-nya berupa link yang bisa langsung di-fetch (bukan sekadar
screenshot upload) — jalankan dulu tool ekstraksi yang dibundel plugin
ini:
```bash
EXTRACT_STYLES=$(find ~/.claude/plugins/cache -name "extract-styles.py" -path "*design-agent*" 2>/dev/null | head -1)
python3 "$EXTRACT_STYLES" <url-referensi> .design/registry/measured/<refId>.json .design/registry/measured/<refId>-sections
```
Kalau berhasil (exit code 0): hasil JSON ini jadi **sumber utama** buat
mengisi token di Langkah 2 — bukan tebakan. Simpan path file JSON-nya ke
`measuredTokens.referenceJsonPath` di spec (lihat `SCHEMA.md`), dan set
`measuredTokens.source: "extract-styles"`.

Kalau gagal (exit code 1 — situs block bot, butuh login, script tidak
ketemu, atau Playwright/Pillow belum terinstall): catat itu terus terang,
set `measuredTokens.source: "vision"`, dan lanjut ke Langkah 2 seperti
biasa (observasi visual manual) — jangan blokir seluruh proses `/spec`
hanya karena satu referensi gagal diekstrak.

Untuk referensi `category: "concept"` atau tanpa URL fetchable, lewati
langkah ini — langsung ke Langkah 2 (`measuredTokens.source: "vision"`).
```

- [ ] **Step 2: Ketatkan aturan confidence `stated`**

Di section "3. Beri confidence marker di SETIAP nilai", tambahkan kalimat
setelah baris definisi `stated`:
```markdown
- `stated` (1.0) — terlihat jelas & terukur langsung dari referensi.
  **Sejak ada `extract-styles.py`: `stated` HANYA boleh dipakai untuk
  field yang nilainya berasal dari hasil ekstraksi terukur
  (`measuredTokens.source: "extract-styles"`).** Kalau sumbernya
  observasi visual (`source: "vision"`) — walau kelihatan jelas dan
  konsisten di mata — confidence maksimalnya `discussed`, bukan `stated`.
```

- [ ] **Step 3: Update Langkah 5 (Tulis ke registry)**

Tambahkan kalimat di akhir Langkah 5 (setelah kalimat tentang ID lanjut):
```markdown
Isi juga field `measuredTokens` di entry spec sesuai hasil Langkah 1.5
(`source`, `referenceJsonPath`, dan `sections` dari file JSON hasil
ekstraksi kalau ada).
```

- [ ] **Step 4: Verifikasi manual**

Baca ulang `skills/spec/SKILL.md` dari awal — pastikan nomor langkah lain (`3.5`, `4`, `5`, `6`) yang mereferensikan "Langkah 2" atau "Langkah 3" masih konsisten setelah sisipan 1.5 (1.5 tidak menggeser penomoran langkah lain karena pakai notasi desimal).

- [ ] **Step 5: Commit**

```bash
git add skills/spec/SKILL.md
git commit -m "feat: integrasikan extract-styles.py ke alur /design-agent:spec, ketatkan aturan confidence stated"
```

---

### Task 9: `skills/build/SKILL.md` — loop QA iteratif berbasis token

**Files:**
- Modify: `skills/build/SKILL.md`

- [ ] **Step 1: Ganti seluruh Langkah 4 ("Visual QA")**

Ganti section "### 4. Visual QA — wajib, bukan opsional" (baris ~108-130 di
versi saat ini) jadi:
```markdown
### 4. QA berbasis token — wajib, bukan opsional
QA sekarang berbasis perbandingan token terukur (bukan cuma pixel diff),
supaya kebal terhadap perbedaan konten teks (placeholder vs teks asli
referensi yang memang sengaja tidak disalin — lihat Langkah 2.5). Cari
dulu lokasi kedua script yang dibundel plugin ini:
```bash
EXTRACT_STYLES=$(find ~/.claude/plugins/cache -name "extract-styles.py" -path "*design-agent*" 2>/dev/null | head -1)
COMPARE_TOKENS=$(find ~/.claude/plugins/cache -name "compare-tokens.py" -path "*design-agent*" 2>/dev/null | head -1)
VISUAL_DIFF=$(find ~/.claude/plugins/cache -name "visual-diff.py" -path "*design-agent*" 2>/dev/null | head -1)
```

Kalau spec ini tidak punya `measuredTokens.referenceJsonPath` (referensinya
`source: "vision"`, gak ada data terukur buat dibandingkan) — lewati loop
di bawah, langsung ke pixel diff manual (Langkah 4b) dan bilang terus
terang ke user bahwa QA token-based tidak bisa jalan untuk spec ini.

Kalau ada `referenceJsonPath`, jalankan loop berikut (maksimal 3 putaran):

1. Pastikan dev server jalan di `<url-dev-server>`.
2. Ekstrak style dari hasil build:
   ```bash
   python3 "$EXTRACT_STYLES" <url-dev-server> .design/registry/measured/<specId>-build.json .design/registry/measured/<specId>-build-sections
   ```
3. Bandingkan dengan referensi:
   ```bash
   python3 "$COMPARE_TOKENS" <measuredTokens.referenceJsonPath> .design/registry/measured/<specId>-build.json
   ```
   Exit code `0` = semua token dalam toleransi. Exit code `1` = ada
   mismatch — baca output JSON-nya, cari field mana yang `"mismatch"`.
4. Kalau ada mismatch: perbaiki NILAI SPESIFIK itu di kode (tetap dari
   token yang sudah ada di spec — jangan menebak nilai baru), lalu ulangi
   dari langkah 2.
5. Berhenti kalau: exit code `0` (semua match), ATAU sudah 3 putaran.
   Kalau masih ada mismatch di putaran ke-3, JANGAN klaim selesai — lapor
   apa adanya ke user (lihat Langkah 5).

### 4b. Bukti visual pelengkap
Setelah loop di atas selesai (baik konvergen atau mentok 3 putaran),
jalankan pixel diff sekali sebagai bukti visual tambahan untuk user
(bukan penentu lolos/tidak):
```bash
python3 "$VISUAL_DIFF" <url-dev-server> \
  .design/registry/screenshots/<reference-id>.png \
  .design/registry/screenshots/diff
```
Laporkan hasilnya sebagai pelengkap, bukan pengganti hasil `compare-tokens.py`
di Langkah 4. Kalau script/dependency tidak ada, bilang terus terang dan
lanjut tanpa bukti pixel — jangan blokir laporan token-based yang sudah ada.
```

- [ ] **Step 2: Update Langkah 5 (Update registry) — tambah event baru**

Ganti blok journal di "### 5. Update registry" jadi:
```markdown
`specs.json` → `status: "built"`, `updatedAt` terbaru.
Append journal:
```json
{"ts":"<ISO 8601>","event":"build_started","specId":"S-00X","method":"standalone|superpowers"}
{"ts":"<ISO 8601>","event":"token_compare","specId":"S-00X","iteration":<n>,"mismatches":<jumlah>}
{"ts":"<ISO 8601>","event":"token_compare_converged","specId":"S-00X","iteration":<n>}
{"ts":"<ISO 8601>","event":"visual_diff","specId":"S-00X","summary":"<ringkasan hasil banding pixel pelengkap>"}
{"ts":"<ISO 8601>","event":"build_completed","specId":"S-00X"}
```
Kalau loop mentok 3 putaran dengan mismatch tersisa, JANGAN tulis
`token_compare_converged` — cukup event `token_compare` terakhir, dan
sebutkan status "belum konvergen" secara eksplisit di laporan ke user.
```

- [ ] **Step 3: Update daftar "Yang TIDAK boleh dilakukan skill ini"**

Tambahkan poin baru:
```markdown
- Melaporkan build "sudah sesuai referensi" berdasarkan pixel diff
  (Langkah 4b) tanpa menjalankan perbandingan token (Langkah 4) dulu —
  pixel diff cuma pelengkap, bukan pengganti
- Melanjutkan loop token-compare lebih dari 3 putaran, atau berhenti
  sebelum 3 putaran padahal masih ada mismatch tanpa alasan jelas
```

- [ ] **Step 4: Verifikasi manual**

Baca ulang seluruh `skills/build/SKILL.md`, pastikan referensi ke
"Langkah 4" di bagian lain file (kalau ada) masih konsisten dengan
struktur baru (4 dan 4b).

- [ ] **Step 5: Commit**

```bash
git add skills/build/SKILL.md
git commit -m "feat: ganti visual QA jadi loop QA berbasis token di /design-agent:build"
```

---

### Task 10: Dokumentasi & versi plugin

**Files:**
- Modify: `README.md`
- Modify: `.claude-plugin/plugin.json`

- [ ] **Step 1: Update struktur plugin di README**

Di `README.md`, bagian "## Struktur plugin", ubah blok `hooks/` jadi:
```markdown
hooks/
  ├── hooks.json          ← registrasi hook PostToolUse
  ├── validate-tokens.py  ← otomatis: cek hex color di luar spec
  ├── extract-styles.py   ← dipanggil skill spec & build: ekstraksi computed-style terukur (Playwright)
  ├── compare-tokens.py   ← dipanggil skill build: bandingkan token referensi vs hasil build
  ├── visual-diff.py      ← manual (dipanggil skill build): screenshot & pixel diff pelengkap
  ├── requirements.txt
  └── tests/              ← unit test untuk fungsi murni di atas (dev-only)
```

- [ ] **Step 2: Bump versi plugin**

Di `.claude-plugin/plugin.json`, ubah:
```json
  "version": "1.1.0"
```
jadi:
```json
  "version": "1.2.0"
```

- [ ] **Step 3: Verifikasi manual**

```bash
cat .claude-plugin/plugin.json
```
Expected: `"version": "1.2.0"`.

- [ ] **Step 4: Commit**

```bash
git add README.md .claude-plugin/plugin.json
git commit -m "docs: update struktur plugin di README, bump versi ke 1.2.0"
```

---

## Self-Review Notes

- **Spec coverage**: Task 1-2 = `compare-tokens.py` (komponen 2 di spec). Task 3-5 = `extract-styles.py` (komponen 1). Task 6 = fix bug pixel diff (bagian arsitektur #1). Task 7 = schema (komponen 6). Task 8 = perubahan `/spec` (komponen 3). Task 9 = perubahan `/build` (komponen 4 + 4b pixel pelengkap). Task 10 = dokumentasi. Semua 6 komponen di design spec punya task yang mengimplementasikannya.
- **Placeholder scan**: tidak ada `TBD`/`TODO`/"tambahkan validasi yang sesuai" — semua step berisi kode/instruksi konkret.
- **Type consistency**: skema JSON `{"colors": {"dominant": [...]}, "sections": [{"index", "bbox", "typography", "buttons", "containers"}]}` dipakai identik di Task 3 (`aggregate_extraction`), Task 2 (`compare_sections`), dan Task 5 (`run()`) — dicek konsisten field-by-field.
- **Toleransi & batas iterasi**: `DEFAULT_TOLERANCES` (Task 1) dan cap 3 putaran (Task 9) sesuai batasan yang sudah disepakati di design spec, tidak ada tambahan asumsi baru.
