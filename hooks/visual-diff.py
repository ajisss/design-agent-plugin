#!/usr/bin/env python3
"""
visual-diff.py — dipanggil manual oleh skill /build (bukan hook otomatis),
karena butuh URL dev server yang lagi jalan.

Cara pakai:
    python3 .claude/hooks/visual-diff.py <url-dev-server> <path-screenshot-referensi> <output-dir>

Contoh:
    python3 .claude/hooks/visual-diff.py http://localhost:3000 \
        .design/registry/screenshots/R-001.png \
        .design/registry/screenshots/diff

Butuh: playwright (python) + pillow.
    pip install playwright pillow
    playwright install chromium
"""
import sys
import os


def main():
    if len(sys.argv) < 4:
        print("Usage: visual-diff.py <url> <reference_screenshot> <output_dir>")
        sys.exit(1)

    url, reference_path, output_dir = sys.argv[1], sys.argv[2], sys.argv[3]
    os.makedirs(output_dir, exist_ok=True)

    if not os.path.exists(reference_path):
        print(f"[visual-diff] Referensi tidak ditemukan: {reference_path}")
        print("[visual-diff] Pastikan screenshot referensi sudah disimpan "
              "waktu /select (screenshotPath di references.json).")
        sys.exit(1)

    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        print("[visual-diff] Playwright belum terinstall.")
        print("Jalankan: pip install playwright pillow && playwright install chromium")
        sys.exit(1)

    result_path = os.path.join(output_dir, "result.png")

    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page(viewport={"width": 1440, "height": 900})
        page.goto(url, wait_until="networkidle")
        page.screenshot(path=result_path, full_page=True)
        browser.close()

    try:
        from PIL import Image, ImageChops
    except ImportError:
        print("[visual-diff] Pillow belum terinstall. Screenshot hasil build "
              f"tersimpan di {result_path}, tapi diff otomatis di-skip.")
        print("Jalankan: pip install pillow")
        sys.exit(0)

    ref = Image.open(reference_path).convert("RGB")
    res = Image.open(result_path).convert("RGB")

    # Samakan ukuran biar bisa dibandingkan piksel
    res_resized = res.resize(ref.size)
    diff = ImageChops.difference(ref, res_resized)
    bbox = diff.getbbox()

    diff_path = os.path.join(output_dir, "diff.png")
    diff.save(diff_path)

    # Skor kasar: rata-rata perbedaan piksel, dibalik jadi similarity 0-1
    stat_diff = sum(diff.getdata(band=0)[i] for i in range(0, len(diff.getdata(band=0)), 50))
    max_possible = 255 * (len(diff.getdata(band=0)) // 50)
    similarity = 1 - (stat_diff / max_possible) if max_possible else 0

    print(f"[visual-diff] Screenshot hasil: {result_path}")
    print(f"[visual-diff] Diff map: {diff_path}")
    print(f"[visual-diff] Similarity score (kasar, 0-1): {similarity:.2f}")
    if bbox is None:
        print("[visual-diff] Tidak ada perbedaan piksel terdeteksi.")
    else:
        print(f"[visual-diff] Area berbeda terdeteksi di bounding box: {bbox}")
    print("[visual-diff] CATATAN: skor ini heuristik kasar (pixel diff), "
          "bukan penilaian estetik. Tetap cek diff.png secara visual manual.")


if __name__ == "__main__":
    main()
