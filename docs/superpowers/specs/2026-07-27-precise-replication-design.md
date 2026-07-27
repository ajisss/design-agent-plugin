# Replikasi Presisi 1:1 — Design Spec

## Masalah

Hasil `/design-agent:build` sekarang jauh dari referensi di tiga dimensi
sekaligus: warna & tipografi, spacing/layout, dan struktur/bentuk komponen.
Referensi yang diuji campuran (live site + screenshot statis).

Dua akar masalah:

1. `/spec` mengekstrak token dengan cara Claude "melihat" screenshot/URL dan
   menebak nilainya — bukan mengukur. Confidence marker `stated` dipakai
   walau sebenarnya cuma interpretasi visual, bukan angka terverifikasi.
2. `/build` melakukan visual QA satu kali di akhir (build → screenshot →
   pixel diff → laporan), tanpa mekanisme koreksi. Pixel diff juga gampang
   "kotor" oleh perbedaan konten teks (placeholder vs teks asli referensi
   yang sengaja tidak disalin — lihat aturan pemisahan style/konten di
   `skills/build/SKILL.md`), sehingga skor jelek walau style-nya sudah pas.

## Solusi

Satu tool ekstraksi baru (`extract-styles.py`, Playwright-based) dipakai di
dua titik pipeline:

- **Saat `/spec`**: dijalankan di URL referensi live (`category: "real"`
  dengan URL fetchable) untuk mengambil computed style asli — bukan
  tebakan. Ini jadi dasar utama pengisian token.
- **Saat `/build`**: dijalankan di dev server lokal hasil build, lalu
  dibandingkan **token-vs-token** (bukan pixel-vs-pixel) dengan hasil
  ekstraksi referensi via `compare-tokens.py`. Ini jadi mekanisme QA utama
  yang kebal terhadap perbedaan konten teks, dan cukup presisi buat
  menggerakkan loop perbaikan iteratif.

Pixel diff (`visual-diff.py`, yang sudah ada) tetap dipakai, tapi turun
peran jadi bukti visual pelengkap untuk direview manual user — bukan lagi
penentu lolos/tidaknya QA.

## Komponen

### 1. `hooks/extract-styles.py` (baru)

Input: `<url>` (referensi live ATAU dev server lokal), viewport opsional.

Proses:
- Load page via Playwright (`wait_until="networkidle"`).
- Deteksi section utama secara heuristik (`<section>`, `<header>`,
  `<footer>`, atau direct child `<body>`/`<main>` dengan tinggi
  signifikan) — catat urutan, bounding box (y-offset, height).
- Ambil computed style dari elemen representatif tiap section: warna
  bg/text dominan, heading (font-size/weight/line-height/font-family),
  body text, tombol (bg, text color, border-radius, padding, box-shadow),
  card/container (border-radius, box-shadow, padding, gap antar child).
- Kumpulkan semua warna unik yang terpakai + frekuensi pemakaian — dipakai
  untuk membantu penentuan role (`primary`/`surface`/`muted`/`accent`)
  berdasar data pemakaian nyata, bukan tebakan.
- Screenshot per section (crop dari full-page screenshot sesuai bbox).
- Output: satu file JSON terstruktur (bukan cuma print stdout), supaya
  bisa dibaca ulang oleh `/spec`, `/build`, dan `compare-tokens.py`.

Error handling: kalau load gagal (butuh login, bot-blocked, JS-heavy yang
tidak pernah `networkidle`) → keluar dengan pesan jelas dan exit code
non-zero. Tidak ada fallback dalam script ini — pemanggil (skill `/spec`
atau `/build`) yang menentukan fallback-nya.

### 2. `hooks/compare-tokens.py` (baru)

Input: dua file JSON hasil `extract-styles.py` (referensi vs hasil build).

Proses, per section (dicocokkan by name/order):
- Warna: bandingkan hex dengan toleransi delta-E kecil → `match` / `close`
  / `mismatch`.
- Tipografi: font-size/weight/line-height per level heading, toleransi
  beberapa px.
- Spacing/radius/shadow: bandingkan nilai dengan toleransi (±2px default).
- Struktur: jumlah & urutan section vs section di spec — mismatch di sini
  ditandai prioritas tertinggi (bug struktural, bukan gaya).
- Tidak pernah membandingkan isi teks — comparator ini murni style &
  layout numerik.

Section yang ada di hasil build tapi tidak ada padanan di referensi (mis.
section tambahan yang memang diminta user, bukan dari referensi) ditandai
`no_reference` — bukan dihitung sebagai mismatch/error.

Output: JSON diff terstruktur (section → token → status) yang bisa dibaca
Claude untuk memutuskan perbaikan spesifik.

### 3. Perubahan `/spec`

Sub-langkah baru sebelum "Amati referensi secara visual" yang sudah ada:

- Untuk tiap referensi terpilih `category: "real"` dengan URL fetchable →
  jalankan `extract-styles.py` dulu. Hasilnya jadi sumber utama pengisian
  token — Claude memetakan nilai mentah ke role semantik spec, bukan
  menebak angkanya.
- Field yang diisi dari hasil ekstraksi ini boleh dilabeli `stated`.
  **Aturan baru**: `stated` TIDAK BOLEH lagi dipakai hanya karena
  "kelihatan jelas di screenshot" tanpa data terukur — itu di-cap maksimal
  `discussed`. ini mengetatkan disiplin confidence yang sudah ada di
  `SCHEMA.md`.
- Untuk referensi `category: "concept"` atau tanpa URL fetchable → tetap
  observasi visual (cara lama), ditambah sampling warna dominan dari file
  screenshot pakai color quantization (PIL) — supaya token warna tetap
  presisi walau struktur/spacing tetap estimasi.
- Section boundaries + screenshot per-section disimpan ke registry (field
  baru `measuredTokens`, lihat bagian schema) untuk dipakai `/build`.

### 4. Perubahan `/build` — loop QA iteratif

Menggantikan langkah "Visual QA" lama:

1. Build selesai, dev server jalan.
2. Jalankan `extract-styles.py` di URL dev server lokal.
3. Jalankan `compare-tokens.py` (JSON referensi vs JSON hasil build).
4. Kalau ada mismatch di luar toleransi → perbaiki nilai spesifik itu di
   kode (tetap dari spec, bukan nilai baru) → ulangi dari langkah 2.
5. Maksimal 3 putaran. Kalau masih ada mismatch setelah putaran ke-3 →
   berhenti, laporkan apa adanya.
6. Setelah loop selesai (konvergen atau mentok 3x) → jalankan
   `visual-diff.py` (pixel, full-page) satu kali sebagai bukti visual
   pelengkap untuk user — bukan penentu lolos/tidak.
7. Laporan akhir: tabel per section (match/close/mismatch), sebutkan
   eksplisit mismatch yang dibiarkan karena mentok iterasi.

### 5. Fallback & error handling

- URL referensi tidak fetchable / block bot / butuh login → `/spec`
  fallback ke observasi visual manual, confidence di-cap `discussed`.
- Dev server belum jalan / port salah saat `/build` extract → loop QA
  tidak jalan, kasih tahu user terus terang, jangan klaim beres.
- Playwright/Pillow belum terinstall → pesan jelas + instruksi install,
  seperti behavior `visual-diff.py` sekarang.
- Jumlah section referensi vs hasil build beda → section ekstra ditandai
  `no_reference`, bukan error/mismatch.
- Toleransi warna/spacing (±2px, delta-E kecil) di-hardcode di
  `compare-tokens.py` sebagai baseline masuk akal — mencegah loop
  infinite-churn mengejar beda sub-piksel yang tidak kasat mata.

### 6. Perubahan schema

Tambahan field di tiap entry `specs[]` (`SCHEMA.md` + registry
`specs.json`):
```json
"measuredTokens": {
  "source": "extract-styles | vision",
  "referenceJsonPath": "string | null",
  "sections": [
    { "name": "hero", "screenshotPath": "string", "bbox": {"y": 0, "height": 800} }
  ]
}
```

Journal event baru:
```json
{"ts":"...","event":"styles_extracted","specId":"S-00X","source":"live-url","refId":"R-001"}
{"ts":"...","event":"token_compare","specId":"S-00X","iteration":1,"mismatches":3}
{"ts":"...","event":"token_compare_converged","specId":"S-00X","iteration":2}
```

Tidak ada breaking change — field lama tetap valid, spec lama tanpa
`measuredTokens` fallback ke behavior lama (vision-based, pixel diff satu
kali).

## Testing

- `extract-styles.py`: uji manual di beberapa live site publik (termasuk
  yang JS-heavy) — pastikan output JSON konsisten & section terdeteksi
  masuk akal; uji juga kasus gagal (URL invalid, site block bot) exit
  jelas.
- `compare-tokens.py`: uji dengan dua JSON sintetis — satu identik (harus
  semua `match`), satu dengan deviasi terkontrol per kategori token (warna
  beda, spacing beda, section hilang) — pastikan tiap kasus terdeteksi
  dengan status yang benar.
- `/spec` & `/build` end-to-end: jalankan pipeline penuh terhadap minimal
  satu referensi live nyata, verifikasi `measuredTokens` terisi dan loop
  `/build` benar-benar mengoreksi mismatch di putaran berikutnya (bukan
  cuma laporan kosong).

## Batasan yang disadari

- `extract-styles.py` tidak bisa menembus site yang butuh auth atau
  bot-protection — untuk kasus itu tetap fallback ke observasi visual.
- Toleransi diff bersifat heuristik tetap (bukan per-project configurable
  di iterasi pertama) — bisa disesuaikan nanti kalau ternyata terlalu
  ketat/longgar di praktik nyata.
- Loop iteratif dibatasi 3 putaran untuk mencegah biaya token tak
  terkendali — tidak menjamin konvergensi penuh di semua kasus.
- `compare_sections` mencocokkan section referensi vs hasil build murni
  by posisi (urutan index di list), bukan by identitas semantik (mis.
  nama class DOM atau isi heading). Kalau struktur DOM hasil build beda
  urutan/heuristik deteksinya dari referensi (mis. section hero
  referensi ke-index 0 tapi di build ke-index 2 karena elemen lain
  duluan terdeteksi), perbandingan bisa salah pasang secara diam-diam
  (mis. hero referensi dibandingkan ke pricing build) tanpa error apapun.
  Memperbaiki ini butuh algoritma pencocokan berbasis konten atau
  signature DOM (bukan cuma index) — di luar cakupan iterasi ini.
