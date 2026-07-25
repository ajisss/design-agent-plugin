---
name: inspo
description: Cari dan kurasi referensi UI/UX design dari sumber kredibel, dibagi ke kategori real-production (Mobbin, Land-book, SaaS Landing Page, Lapa Ninja, Really Good UI, One Page Love, Screenlane) dan concept/eksplorasi (Dribbble, Behance, Awwwards, Godly). Mendukung 3 mode: user kasih link spesifik (langsung dipakai sebagai referensi), user sebut nama situs tertentu (search khusus di situs itu, relevan atau random sesuai command), atau tidak spesifik (search lintas sumber, campur real + concept). WAJIB dipanggil sebagai langkah PERTAMA setiap kali user minta bikin/build/develop UI baru apapun — landing page, dashboard, halaman, komponen, fitur — baik disebut eksplisit ("cari referensi", "cari inspirasi design") ATAUPUN disebut sebagai permintaan build langsung (mis. "buat landing page minimalis", "bikin dashboard fintech", "develop halaman login"), ATAUPUN user menyebut nama situs desain tertentu atau kasih link referensi. Jika brief tidak menyebutkan mau bikin apa dan konten/section apa saja, skill ini WAJIB bertanya dulu sebelum mencari apapun, dan bisa memberi saran susunan section kalau user bingung. Jangan langsung menulis kode atau membuat artifact untuk permintaan UI apapun sebelum referensi dicari dan dipilih user lewat pipeline ini — itu justru masalah "AI slop" yang skill ini dirancang untuk dicegah. Skill ini HANYA mencari dan mengurasi — TIDAK menulis kode, TIDAK develop apapun, TIDAK membuat artifact/preview. Selalu jalankan skill ini sebelum masuk ke tahap select, spec, build, atau tool artifact apapun, jika belum ada kandidat referensi di registry untuk brief ini.
---

# /inspo — Research Referensi Design

Tugas skill ini cuma satu: ubah brief user jadi kumpulan kandidat referensi
yang kredibel dan relevan. Jangan lompat ke development, jangan menilai mana
yang "terbaik" secara sepihak — itu keputusan user di tahap `/design-agent:select`.

## Langkah

### 1. Baca konteks dulu
- Baca `.design/registry/project.json` untuk tau konteks proyek (kalau ada).
- Baca `.design/registry/references.json` — cek apakah brief serupa sudah
  pernah dicari sebelumnya, biar tidak duplikat kandidat.

### 2. Cek kelengkapan brief — HARD STOP kalau belum jelas
Sebelum cari referensi apapun, pastikan dulu 2 hal ini jelas dari brief user:
1. **Mau bikin apa** (halaman/fitur apa — landing page, dashboard, form
   checkout, dll)
2. **Isi/section apa aja yang diinginkan** (mis. hero, fitur, testimoni,
   pricing, footer — atau kalau dashboard: chart apa, tabel apa, dll)

Kalau salah satu atau keduanya belum jelas dari perintah user, STOP di sini
— JANGAN mulai cari referensi dulu. Tanyakan:
> "Sebelum saya cari referensi, ini mau bikin apa dan konten/section-nya apa
> aja? Kalau belum kepikiran, saya bisa kasih beberapa opsi umum buat
> [jenis halaman yang disebut/diduga user]."

Kalau user bilang bingung/belum tau, kasih 2-4 opsi susunan section yang
umum dipakai untuk jenis halaman itu (mis. untuk landing page SaaS: "hero +
fitur unggulan + social proof + pricing + CTA akhir" sebagai salah satu
opsi), biar user tinggal pilih atau modifikasi.

Tunggu jawaban eksplisit sebelum lanjut ke Langkah 3. Kalau brief user SUDAH
menyebutkan keduanya dengan jelas di pesan awal, lewati langkah ini —
jangan tanya ulang hal yang sudah dijawab.

### 3. Tentukan mode pencarian
Cek apakah user menyebut sumber spesifik atau kasih link langsung:

**Mode A — User kasih link spesifik** (mis. "pakai referensi dari
`dribbble.com/shots/xxxxx` ini")
- Langsung fetch link itu, jangan search lagi. Perlakukan sebagai kandidat
  referensi langsung (skip proses kurasi 4-6 kandidat — ini permintaan
  eksplisit satu sumber).
- Tetap tentukan `category` (`real`/`concept`) berdasarkan sumbernya.

**Mode B — User sebut nama situs tanpa link spesifik** (mis. "cari dari
Dribbble" atau "ambil dari One Page Love")
- Search KHUSUS di situs itu saja (pakai filter `site:namadomain.com` di
  query), jangan campur sumber lain.
- Kalau user kasih arahan tema/kata kunci di command → filter hasil biar
  relevan sama itu.
- Kalau user bilang eksplisit "random" atau "terserah" → boleh ambil
  beberapa hasil dari situs itu tanpa filter ketat, asal masih masuk akal
  buat brief (jangan asal apapun yang gak nyambung sama sekali).

**Mode C — User tidak sebut sumber spesifik**
- Search lintas sumber seperti biasa (lihat Langkah 4), campur Kategori A
  dan B sesuai brief.

### 4. Cari referensi
Ada dua kategori sumber, dan penting buat dibedain karena mempengaruhi
seberapa yakin nanti spec-nya di tahap `/design-agent:spec`:

**Kategori A — Real production (produk yang beneran live/diimplementasi)**
Prioritaskan kategori ini kalau user butuh sesuatu yang bisa direplikasi
persis, karena struktur/spacing/interaksinya sudah terbukti jalan di
produksi nyata:
- **Mobbin** — pola UI mobile & web dari produk production sungguhan
- **Land-book** — landing page lengkap yang sudah live
- **SaaS Landing Page (saaslandingpage.com)** — kumpulan landing page SaaS
  real, bagus khusus buat brief SaaS/produk digital
- **Lapa Ninja** — landing page real per kategori/industri
- **Really Good UX / UI (goodui.design, uigarage.net)** — pola UI produksi
  dengan penjelasan alasan desainnya
- **One Page Love** — landing page single-page yang sudah live
- **Screenlane** — pola komponen dari aplikasi real

**Kategori B — Concept & eksplorasi (belum tentu diimplementasi)**
Bagus buat cari vibe/mood/arah visual, tapi tandai ke user bahwa ini
eksplorasi, bukan bukti itu bisa/pernah diimplementasi beneran:
- **Dribbble** — eksplorasi visual, kuat untuk mood, tapi sering shot statis
  tanpa interaksi/responsive nyata
- **Behance** — mirip Dribbble, kadang berupa studi kasus lengkap
- **Awwwards / Godly** — situs dengan interaksi/motion kuat, biasanya sudah
  live tapi sering situs kampanye/portofolio (bukan produk SaaS umum)

Lakukan pencarian terpisah per aspek brief (jangan gabung semua jadi satu
query) — misal kalau brief minta "dashboard fintech minimalis", cari
`"fintech dashboard UI"` dan `"minimalist dashboard design"` secara terpisah
biar hasil lebih lengkap. Kalau user gak spesifik minta salah satu kategori
(Mode C), usahakan campur — beberapa dari Kategori A (buat kepastian
struktural) dan beberapa dari Kategori B (buat variasi visual/vibe).

### 5. Kurasi jadi 4-6 kandidat (kecuali Mode A — 1 kandidat langsung)
Untuk tiap kandidat, catat:
- URL sumber
- Screenshot (kalau bisa diambil)
- 1 kalimat alasan relevansi ke brief
- Kategori: `"real"` (Kategori A, produk production) atau `"concept"`
  (Kategori B, eksplorasi/belum tentu diimplementasi)

Jangan sekadar dump semua hasil pencarian — filter yang benar-benar cocok
sama brief, prioritaskan variasi (jangan 6 kandidat yang mirip semua).

### 6. Tulis ke registry
Tambahkan tiap kandidat ke `.design/registry/references.json` dengan status
`"candidate"`:

```json
{
  "id": "R-00X",
  "url": "...",
  "source": "mobbin | dribbble | land-book | saas-landing-page | lapa-ninja | really-good-ui | one-page-love | screenlane | behance | awwwards | godly | lainnya",
  "category": "real | concept",
  "query": "query pencarian yang menghasilkan ini",
  "reason": "1 kalimat kenapa relevan",
  "screenshotPath": null,
  "status": "candidate",
  "selectedAt": null
}
```

ID lanjut dari ID terakhir yang ada di file (jangan mulai dari R-001 lagi
kalau sudah ada referensi sebelumnya).

Append event ke `.design/registry/journal.jsonl`:
```json
{"ts":"<ISO 8601 sekarang>","event":"references_researched","count":<jumlah kandidat>,"brief":"<ringkasan brief>","mode":"link_spesifik | situs_spesifik | bebas"}
```

### 7. Tampilkan ke user dan STOP
Tampilkan kandidat (gambar via image_search hasil kalau ada, atau link) ke
user dengan format ringkas: nama/deskripsi singkat, kategori (real
production / concept-eksplorasi), alasan relevansi, link. Kalau ada
kandidat dari Kategori B (concept), sebutkan singkat bahwa itu eksplorasi
visual yang belum tentu pernah diimplementasi — biar user tau
konsekuensinya saat memilih nanti.

Kalau Mode A (link spesifik langsung dari user), tetap tampilkan
konfirmasi singkat sebelum lanjut — jangan asumsikan otomatis "selected"
walau usernya sendiri yang kasih link itu.

Akhiri dengan kalimat eksplisit:
> "Referensi mana yang mau dipakai? Bisa pilih satu atau gabungan — jawab di
> pesan berikutnya sebelum lanjut ke ekstraksi spec."

JANGAN lanjut sendiri ke `/design-agent:select` atau `/design-agent:spec`. Ini hard stop — tunggu
jawaban eksplisit user di giliran berikutnya.

## Yang TIDAK boleh dilakukan skill ini
- Menulis kode atau membuat komponen apapun
- Memutuskan sendiri referensi mana yang "terbaik" lalu langsung lanjut
- Mereproduksi aset visual persis dari brand/produk berhak cipta — ambil pola
  struktural (grid, hierarki komponen), bukan aset asli (logo, foto, ilustrasi)
- Langsung mulai cari referensi kalau brief belum jelas soal mau bikin apa
  dan konten/section apa saja — tanya dulu, kasih saran kalau user bingung
- Mencampur sumber lain kalau user sudah spesifik minta 1 situs tertentu
  (Mode B) — cari khusus di situs itu saja
- Search ulang kalau user sudah kasih link spesifik (Mode A) — langsung
  fetch link itu, jangan cari-cari lagi
