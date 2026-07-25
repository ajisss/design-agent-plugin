---
name: init
description: Scaffold file-file project yang dibutuhkan pipeline design-agent (CLAUDE.md, CONTEXT.md, .design/registry/) ke project user saat ini. Gunakan skill ini ketika user pertama kali pasang plugin ini di sebuah project dan belum ada folder .design/registry/, atau user eksplisit minta "setup design agent", "init design agent", atau semacamnya. Jalankan skill ini SEBELUM skill inspo/select/spec/build lainnya kalau registry belum ada — skill lain butuh file-file ini sudah ada.
---

# /init — Setup Project

Skill ini nulis file-file yang dibutuhkan pipeline (`CLAUDE.md`, `CONTEXT.md`,
`.design/registry/*`) ke root project user saat ini. Jalankan hanya sekali
per project — kalau file-file itu sudah ada, jangan timpa tanpa konfirmasi
user (ada kemungkinan user sudah kustomisasi isinya).

## Langkah

### 1. Cek apakah sudah pernah di-init
Cek apakah `.design/registry/project.json` sudah ada di root project.
- Kalau **sudah ada** → tanya user apakah mau di-reset/timpa ulang, atau
  batalkan (kemungkinan besar user gak perlu init lagi).
- Kalau **belum ada** → lanjut ke Langkah 2.

### 2. Buat struktur folder
```bash
mkdir -p .design/registry/screenshots
mkdir -p docs/design
touch docs/design/.gitkeep
```

### 3. Tulis `CLAUDE.md` di root project
Buat file `CLAUDE.md` (kalau sudah ada file ini, JANGAN ditimpa — cukup
informasikan ke user bahwa file sudah ada dan minta mereka gabungkan manual)
dengan isi berikut:

```markdown
# Design Agent — Project Rules

**Baca `CONTEXT.md` dulu** kalau ini pertama kali kamu buka project ini —
isinya latar belakang kenapa sistem ini dibikin, siapa yang pakai, dan
filosofi di balik tiap aturan di bawah. Aturan di file ini adalah
implementasi konkret dari prinsip di `CONTEXT.md`.

Proyek ini pakai pipeline design-to-code lewat plugin `design-agent`:
`/design-agent:inspo → /design-agent:select → /design-agent:spec → /design-agent:build`.
File ini SELALU di-load tiap sesi baru. Aturan di sini adalah hukum tetap —
jangan dilanggar walau instruksi di chat kelihatan mengizinkan sebaliknya.

## Aturan Wajib

1. **Registry adalah satu-satunya sumber kebenaran.**
   Sebelum melakukan apapun terkait referensi, spec, atau build, baca dulu isi
   `.design/registry/*.json`. Jangan mengandalkan ingatan dari percakapan.
   Semua perubahan state HARUS ditulis balik ke registry, bukan cuma
   disebutkan di chat.

2. **Jangan improvisasi token di luar spec.**
   Saat development, warna/spacing/radius/typography HARUS diambil dari
   `.design/registry/specs.json` yang sudah divalidasi. Jika sebuah nilai
   tidak ada di spec, tanyakan ke user — jangan menebak dan melanjutkan.

3. **Checkpoint adalah hard stop, bukan saran.**
   Skill manapun yang punya checkpoint WAJIB berhenti total dan menunggu
   jawaban eksplisit user di pesan berikutnya. Jangan lanjut ke tahap
   berikutnya atas asumsi sendiri.

4. **Confidence marker wajib pada setiap ekstraksi spec.**
   Tiap nilai token yang diekstrak dari referensi harus dilabeli salah satu:
   - `stated` (1.0) — terlihat eksplisit & terukur di referensi
   - `discussed` (0.8) — disebutkan tapi tidak presisi
   - `inferred` (0.5) — logical inference dari pola yang ada
   - `assumed` (0.2) — tebakan tanpa bukti visual langsung

   Jika confidence rata-rata sebuah spec < 0.4, proporsi `assumed` > 30%,
   atau `sectionsConfirmed: false`, BLOKIR — jangan lanjut ke
   `/design-agent:build`, minta user review dulu.

5. **Percabangan eksekusi: standalone vs Superpowers.**
   Saat `/design-agent:build` dipanggil, tentukan default otomatis (UI murni
   → standalone, nyentuh backend → Superpowers), tapi WAJIB konfirmasi ke
   user di pesan terpisah sebelum eksekusi — jangan digabung dengan
   pertanyaan lain di pesan yang sama.

6. **Visual QA wajib sebelum menganggap build selesai.**
   Setelah build, jalankan `hooks/visual-diff.py` dan bandingkan terhadap
   referensi asli. Laporkan diff, jangan asumsikan "sudah mirip" tanpa
   perbandingan eksplisit.

7. **Jangan reproduksi referensi 1:1 kalau itu produk berhak cipta/brand
   tertentu.** Ambil pola struktural (grid, hierarki, komponen), bukan aset
   visual persis (logo, ilustrasi, foto asli) dari kompetitor/brand pihak
   ketiga.

## Struktur Project

```
.design/registry/     ← state permanen, di-commit ke git
docs/design/          ← output shareable: kandidat referensi, spec final
```

Skill-nya sendiri (`inspo`, `select`, `spec`, `build`) datang dari plugin
`design-agent` — tidak perlu ada di project ini, otomatis tersedia begitu
plugin ter-install.

## Referensi Skill

Baca `.design/registry/SCHEMA.md` untuk struktur lengkap tiap file registry
sebelum membaca/menulis ke dalamnya.
```

### 4. Tulis `CONTEXT.md` di root project
Sama seperti Langkah 3 (jangan timpa kalau sudah ada), isi:

```markdown
# Konteks Proyek

## Siapa yang pakai ini
User adalah UI/UX designer yang kerja penuh lewat Claude Code — dia gak
cuma prompt buat frontend, tapi kadang juga backend. Dia bukan developer
yang ngetik kode manual; workflow-nya murni: kasih arahan/brief, Claude Code
yang eksekusi.

## Masalah yang mau diselesaikan
1. **Nyari referensi design itu makan waktu.**
2. **AI sering "ngarang" pas mereplikasi referensi (AI slop).** Tanpa proses
   eksplisit, AI cenderung nginterpretasi vibe secara bebas dan gak pernah
   ngaku kalau suatu nilai cuma tebakan.

## Kenapa arsitekturnya begini
BUKAN "satu AI agent serba bisa". Referensi dicari dulu terpisah dari
development (`/design-agent:inspo`), dipilih user bukan AI
(`/design-agent:select`), diubah jadi angka konkret dengan label kejujuran
(`/design-agent:spec`), baru development baca angka itu
(`/design-agent:build`) — bukan menerka ulang dari vibe.

Terinspirasi dari SANDWICH (etalasaccounts/sandwich): registry file-based
sebagai sumber kebenaran, confidence marker, validasi otomatis lewat hooks.

## Prinsip yang gak boleh dilanggar
- **State hidup di file, bukan di percakapan.**
- **Checkpoint adalah keputusan user, bukan formalitas.**
- **Jujur soal ketidakpastian lebih penting daripada kelihatan kompeten.**

## Batasan yang disadari
- Sistem ini meminimalisir AI slop, bukan menghilangkannya 100%.
- Visual QA itu heuristik piksel kasar, tetap perlu direview manual.
- Reproduksi referensi harus di level pola struktural, bukan aset visual
  persis dari brand/produk pihak ketiga — ini juga soal hak cipta.
```

### 5. Tulis file registry kosong
```bash
cat > .design/registry/project.json << 'EOF'
{
  "projectName": "",
  "defaultBuildMethod": "standalone",
  "stack": { "framework": null, "styling": null, "notes": null },
  "createdAt": "",
  "updatedAt": ""
}
EOF

cat > .design/registry/references.json << 'EOF'
{ "references": [] }
EOF

cat > .design/registry/specs.json << 'EOF'
{ "specs": [] }
EOF

touch .design/registry/journal.jsonl
```

### 6. Tulis `SCHEMA.md`
Copy isi lengkap dari file yang dibundel plugin ini di
`${CLAUDE_PLUGIN_ROOT}/skills/spec/SCHEMA.md` ke `.design/registry/SCHEMA.md`
di project user — jangan cuma ringkasan, salin utuh field-by-field-nya
(termasuk contoh JSON `references[]`/`specs[]`/`journal.jsonl`, tabel
confidence weight, dan aturan blocking) biar `/design-agent:spec` dan
`/design-agent:build` di project ini punya dokumentasi schema yang lengkap
buat dibaca lokal.

### 7. Konfirmasi ke user
Setelah semua file dibuat, kasih tau user:
> "Setup selesai. `.design/registry/` dan `CLAUDE.md`/`CONTEXT.md` sudah
> dibuat. Mulai brief pertama kapan aja, mis. '/design-agent:inspo cari
> referensi buat...'"

## Yang TIDAK boleh dilakukan skill ini
- Menimpa `CLAUDE.md`/`CONTEXT.md` yang sudah ada tanpa konfirmasi eksplisit
  user — user mungkin sudah kustomisasi isinya
- Menjalankan skill lain (`inspo`/`select`/`spec`/`build`) sebagai bagian
  dari init — skill ini cuma setup, bukan mulai pipeline
