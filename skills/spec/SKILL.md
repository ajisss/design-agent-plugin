---
name: spec
description: Ekstrak referensi design yang sudah dipilih user (status "selected" di registry) menjadi design spec terstruktur dan terukur — color roles, typography scale, spacing, radius, shadow, motion, DAN struktur/section halaman (hero, fitur, pricing, dll) — masing-masing dengan confidence marker. Gunakan skill ini ketika user minta lanjut ke "extract spec", "bikin token", atau setelah /select selesai dan user konfirmasi lanjut. Skill ini TIDAK menulis kode aplikasi — hanya menghasilkan file spec yang nanti dibaca /build. Ini lapisan paling penting untuk mencegah AI menebak-nebak (AI slop) saat replikasi referensi, termasuk menebak struktur halaman tanpa konfirmasi user.
---

# /spec — Ekstraksi Referensi jadi Design Spec

Tugas skill ini: ubah referensi visual jadi angka dan nilai yang konkret,
bukan deskripsi "vibe" yang samar. Setiap nilai token WAJIB dilabeli
confidence marker — ini yang membedakan spec yang bisa diandalkan dari
tebakan yang dibungkus rapi.

## Langkah

### 1. Baca referensi terpilih
Baca `.design/registry/references.json`, ambil semua entry berstatus
`"selected"` untuk fitur/halaman yang mau di-spec sekarang. Kalau ada lebih
dari satu, spec ini akan menggabungkan pola dari semuanya.

### 2. Amati referensi secara visual
Untuk tiap referensi: lihat screenshot (kalau ada) atau fetch URL-nya.
Cek juga field `category` di `references.json` — ini mempengaruhi confidence
default:
- `category: "real"` — produk sudah live, jadi nilai yang terlihat jelas
  (warna, spacing yang konsisten) boleh dilabeli `stated`/`discussed` kalau
  memang terlihat jelas dan konsisten
- `category: "concept"` — ini eksplorasi/mockup, belum tentu bisa
  diimplementasi persis (mis. efek visual yang gak realistis di web
  sungguhan). Turunkan confidence default satu tingkat dibanding kalau nilai
  yang sama terlihat di referensi `"real"` — kalau ragu, pakai `inferred`
  bukan `discussed`.

Perhatikan detail konkret, bukan kesan umum:
- Skala warna: warna dominan, peran tiap warna (primary/surface/muted/accent/
  border), bukan cuma hex acak
- Skala tipografi: ukuran heading vs body, line-height, font-weight per level
- Skala spacing: jarak antar elemen, padding komponen — cari pola grid
  (mis. kelipatan 4px/8px)
- Radius: sudut komponen (button, card, input) — apakah konsisten satu nilai
  atau bertingkat
- Shadow/elevation: seberapa kuat, dipakai di komponen mana saja
- Motion/interaksi: transisi, hover state, kalau terlihat dari referensi

### 3. Beri confidence marker di SETIAP nilai
Untuk tiap token, tentukan levelnya jujur:
- `stated` (1.0) — terlihat jelas & terukur langsung dari referensi
- `discussed` (0.8) — pola konsisten tapi butuh sedikit interpretasi
  (mis. terlihat pakai skala 8px tapi tidak semua nilai kelihatan persis)
- `inferred` (0.5) — logical inference dari pola yang ada (mis. dari 3 ukuran
  yang keliatan, menyimpulkan skala penuhnya)
- `assumed` (0.2) — tidak ada bukti visual langsung, ini tebakan

Jangan optimis. Kalau ragu antara dua level, pilih yang lebih rendah.

### 3.5. Tentukan & konfirmasi struktur halaman (sections) — HARD STOP
Ini terpisah dari token visual, tapi sama pentingnya: sebelum spec dianggap
siap dipakai `/design-agent:build`, struktur halaman (urutan section: hero, fitur,
testimoni, pricing, footer, dll) HARUS jelas dan dikonfirmasi user.

- Amati referensi terpilih, susun daftar section yang terlihat di sana.
- Cek juga apakah brief awal user sudah menyebut section spesifik yang
  wajib ada/tidak ada.
- Kalau brief user TIDAK menyebut struktur section secara eksplisit dan
  referensi juga tidak cukup jelas (atau user menggabungkan beberapa
  referensi dengan struktur berbeda) → STOP, tampilkan daftar section yang
  kamu identifikasi sebagai usulan, dan tanyakan:
  > "Halaman ini mau pakai section apa aja? Ini usulan dari referensi yang
  > dipilih: [daftar]. Mau dipakai semua, dikurangi, atau ditambah?"
- Tunggu jawaban eksplisit user sebelum lanjut. JANGAN asumsikan struktur
  standar (hero-fitur-footer) tanpa konfirmasi kalau brief tidak menyebutnya.
- Kalau user SUDAH menyebutkan section secara detail di brief awal (mis.
  "landing page dengan hero, 3 fitur unggulan, testimoni, dan CTA akhir"),
  section sudah dianggap terkonfirmasi — tidak perlu tanya ulang, langsung
  catat sebagai `sections`.

Simpan hasil akhir ke field `sections` di spec (lihat `SCHEMA.md`), dengan
`sectionsConfirmed: true` setelah dikonfirmasi user.

### 4. Hitung confidence summary
```
average = jumlah(weight tiap field) / jumlah(field)
assumedRatio = jumlah(field berlabel "assumed") / jumlah(field)
blocked = average < 0.4 ATAU assumedRatio > 0.3
```
Spec juga TIDAK BOLEH berstatus `"validated"` kalau `sectionsConfirmed`
masih `false` — treat itu sebagai blocking condition tambahan di luar
confidence numerik.

### 5. Tulis ke registry
Tambahkan entry baru ke `.design/registry/specs.json` (di project yang
sedang dikerjakan) mengikuti struktur di `SCHEMA.md` yang dibundel bareng
skill ini (cari file itu relatif ke lokasi `SKILL.md` ini, di
`${CLAUDE_PLUGIN_ROOT}/skills/spec/SCHEMA.md` — bukan file per-project).
ID lanjut dari ID spec terakhir yang ada. Kalau `.design/registry/specs.json`
belum ada sama sekali (project belum pernah di-`/design-agent:init` atau
belum ada kandidat dari `/design-agent:inspo`), buat dulu isinya
`{"specs": []}` sebelum nambah entry.

Jika `blocked: true`:
- JANGAN lanjutkan ke `/design-agent:build`
- Tampilkan ke user field mana yang confidence-nya rendah dan kenapa
- Tanyakan: user mau kasih klarifikasi manual, pilih referensi tambahan yang
  lebih jelas, atau tetap lanjut dengan risiko yang diketahui?

Append journal:
```json
{"ts":"<ISO 8601>","event":"spec_extracted","specId":"S-00X","confidence":<average>}
```
atau jika blocked:
```json
{"ts":"<ISO 8601>","event":"spec_blocked","specId":"S-00X","reason":"average 0.35 < 0.4"}
```

### 6. Tampilkan ringkasan ke user dan STOP
Tampilkan tabel singkat: token utama + nilai + confidence marker-nya, plus
skor rata-rata keseluruhan. Kalau ada field `assumed`, sebutkan eksplisit
mana yang perlu diwaspadai user sebelum develop.

Akhiri dengan:
> "Spec sudah tersimpan (`S-00X`). Lanjut ke development sekarang?"

Jangan panggil `/design-agent:build` sendiri — tunggu konfirmasi eksplisit user.

## Yang TIDAK boleh dilakukan skill ini
- Menulis kode komponen apapun — output-nya cuma file spec
- Melabeli semua field `stated` demi terlihat percaya diri — kejujuran
  confidence marker adalah inti dari skill ini
- Melanjutkan ke `/design-agent:build` saat `blocked: true` atau `sectionsConfirmed: false`
  tanpa keputusan eksplisit user
- Mengasumsikan struktur section standar (hero-fitur-footer) tanpa
  konfirmasi user kalau brief tidak menyebutnya secara eksplisit
- Mengekstrak/menyalin aset visual persis (logo, foto, ilustrasi asli) dari
  referensi berhak cipta — yang diekstrak adalah pola struktural, angka
  ukuran, dan peran warna, bukan aset itu sendiri
