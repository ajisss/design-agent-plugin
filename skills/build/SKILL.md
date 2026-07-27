---
name: build
description: Implementasi UI/komponen dari design spec yang sudah divalidasi (status "validated" atau "draft" dengan confidence cukup di specs.json). Gunakan skill ini ketika user konfirmasi lanjut development setelah /spec, atau minta "build", "develop", "implementasi" dari spec yang sudah ada. Skill ini menentukan otomatis apakah dikerjakan standalone atau diserahkan ke metodologi Superpowers, HANYA mengambil gaya visual & bentuk komponen dari referensi (bukan konten teks/copy asli), lalu WAJIB melakukan QA berbasis perbandingan token (extract-styles.py + compare-tokens.py) sebelum dianggap selesai. Jangan gunakan skill ini jika spec masih berstatus "blocked" — arahkan user ke /spec dulu untuk resolve masalah confidence.
---

# /build — Implementasi dari Spec

Tugas skill ini: ubah design spec jadi kode nyata, dengan disiplin — tidak
improvisasi di luar token, dan tidak dianggap selesai sebelum divalidasi
visual terhadap referensi asli.

## Langkah

### 0. Cek prasyarat
Baca `.design/registry/specs.json`, ambil spec yang dimaksud user.
- Jika `status: "blocked"` → STOP, arahkan user ke `/design-agent:spec` untuk resolve dulu.
  Jangan lanjut dengan alasan apapun.
- Jika `sectionsConfirmed: false` → STOP, arahkan user balik ke `/design-agent:spec` buat
  mastiin dulu struktur halaman (section apa aja yang mau ada) sebelum
  develop. Jangan menebak struktur sendiri di sini.
- Jika `status: "built"` sudah ada → konfirmasi ke user apakah ini rebuild/
  update, bukan build baru.

### 1. Cek stack — tanya HANYA jika belum ada
Baca `.design/registry/project.json` → field `stack`.
- Jika `stack.framework` dan `stack.styling` **sudah terisi** → langsung
  pakai itu, JANGAN tanya lagi.
- Jika **masih null** (biasanya run pertama kali) → tanyakan singkat ke user:
  framework (mis. Next.js/React plain/Vue) dan styling (mis. Tailwind+shadcn/
  plain CSS/lainnya). Simpan jawabannya ke `project.json` sebelum lanjut, jadi
  run berikutnya tidak perlu tanya lagi.

### 2. Tentukan metode eksekusi — HARD STOP TERPISAH

**PENTING: ini WAJIB jadi giliran/pesan terpisah dari Langkah 1.** Jangan
gabungkan pertanyaan stack (Langkah 1) dengan konfirmasi metode build
(langkah ini) dalam satu pesan yang sama, dan jangan putuskan sendiri lalu
langsung lanjut coding — walau kelihatan "jelas" jawabannya. Setelah user
menjawab pertanyaan stack, kirim pesan BARU khusus buat konfirmasi ini, lalu
BENAR-BENAR BERHENTI menunggu balasan user sebelum menyentuh kode apapun.

Cek isi `tokens` di spec:
- Spec hanya menyentuh komponen visual/UI murni (warna, layout, typography,
  komponen tampilan) → default **standalone**
- Spec juga menyentuh kebutuhan backend/API/data model/state management
  kompleks → default **superpowers**

Tampilkan default itu ke user secara singkat dan tawarkan override:
> "Fitur ini kelihatannya [murni UI / juga nyentuh backend]. Saya build
> [standalone / lewat Superpowers]. Mau lanjut atau ganti metode?"

Tunggu konfirmasi (boleh cuma "ya"/"lanjut") sebelum eksekusi. Jika user
override, catat itu di journal sebagai `build_method_overridden`.

Kalau kamu mendapati dirimu ingin langsung menjawab "iya standalone karena
ini cuma UI" lalu lanjut nulis kode di pesan yang sama — itu tandanya kamu
lagi menggabungkan langkah ini dengan langkah sebelumnya. Berhenti, kirim
sebagai pertanyaan terpisah, tunggu balasan.

Update `specs.json` → `buildMethod` sesuai keputusan final.

### 2.5. Pisahkan style dari konten — WAJIB, cegah salah replikasi

Dari referensi, HANYA ambil gaya visual dan bentuk komponen:
- Warna, spacing, radius, shadow, motion (dari `tokens` di spec)
- Bentuk/struktur komponen: bentuk card, bentuk tombol, layout grid, jenis
  section (dari `sections` di spec)

JANGAN ambil dari referensi, dan JANGAN timpa dengan itu:
- Headline, body copy, deskripsi produk, nama fitur, testimoni, atau teks
  apapun yang isinya spesifik ke bisnis/produk di referensi
- Kalau user SUDAH menyusun/menyebutkan konten sendiri (di brief awal atau
  pesan manapun sebelumnya) — pakai persis itu, jangan diganti/ditimpa
  dengan wording dari referensi walau referensinya "kelihatan lebih bagus"

Kalau ada section yang strukturnya sudah dikonfirmasi (`sections` di spec)
tapi user BELUM kasih konten spesifik untuk section itu:
- JANGAN otomatis isi pakai teks asli dari situs referensi
- Pakai placeholder yang jelas ditandai sebagai placeholder, mis.
  `[Headline produk di sini]`, `[Deskripsi fitur 1]` — atau lebih baik,
  tanya dulu ke user apa isinya sebelum lanjut menulis kode untuk section
  itu

Kalau kamu mendapati dirimu mau nulis kalimat yang isinya mirip/sama persis
kayak teks di referensi (bukan cuma struktur/gaya) — itu tandanya kamu lagi
salah mengambil konten, bukan style. Berhenti, ganti jadi placeholder atau
tanya user.

### 3a. Jalur Standalone
- Baca token dari spec, terapkan persis nilainya (jangan bulatkan/ubah tanpa
  alasan)
- Ikuti struktur project/stack yang sudah dikonfirmasi di Langkah 1
- Field dengan confidence `assumed` — implementasikan tapi beri komentar
  kode singkat menandai itu asumsi, biar mudah direview user nanti

### 3b. Jalur Superpowers
- Sebelum manggil command apapun, cek dulu apakah Superpowers ter-install
  (mis. via `/help`, cek apakah `/superpowers:write-plan` ada di daftar).
  Kalau belum ter-install, beri tahu user terus terang, kasih command
  install-nya (`/plugin install superpowers@claude-plugins-official`), dan
  tanyakan apakah mau install dulu atau pindah ke jalur standalone.
- Kalau sudah ter-install, serahkan spec sebagai konteks ke alur Superpowers
  (panggil `/superpowers:write-plan` dengan referensi ke file spec, lalu
  `/superpowers:execute-plan`)
- Pastikan instruksi token dari spec ikut masuk ke plan yang dibuat Superpowers
  — jangan biarkan Superpowers menebak ulang nilai visual yang sudah ada di spec

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

### 5. Update registry
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

## Yang TIDAK boleh dilakukan skill ini
- Build dari spec yang `blocked` atau `sectionsConfirmed: false`
- Menebak nilai token yang tidak ada di spec — tanya user, jangan improvisasi
- Menyalin atau menimpa konten teks yang sudah disusun/ditentukan user
  dengan teks asli dari referensi — referensi cuma sumber style & bentuk
  komponen, bukan sumber wording/copy
- Mengisi section yang belum ada kontennya dengan teks asli dari referensi
  sebagai "placeholder" — pakai penanda placeholder yang jelas atau tanya
  user dulu
- Menganggap build selesai tanpa menjalankan perbandingan token (Langkah 4)
  terlebih dahulu — QA berbasis token (compare-tokens.py) adalah mandatory gate,
  bukan opsional. Pixel diff (Langkah 4b) hanya pelengkap, bukan pengganti
- Menanyakan ulang stack yang sudah tersimpan di `project.json`
- Menggabungkan pertanyaan stack (Langkah 1) dengan konfirmasi metode build
  (Langkah 2) jadi satu pesan, atau memutuskan metode build sendiri tanpa
  benar-benar berhenti menunggu jawaban user
- Melanjutkan loop token-compare lebih dari 3 putaran, atau berhenti
  sebelum 3 putaran padahal masih ada mismatch tanpa alasan jelas
