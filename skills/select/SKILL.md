---
name: select
description: Proses pemilihan referensi design oleh user dari kandidat yang sudah dicari via /inspo. Gunakan skill ini ketika user menjawab/merespon daftar kandidat referensi dengan memilih salah satu, beberapa, atau menolak semuanya (mis. "pakai referensi 2 dan 4", "gabungin yang pertama sama ketiga", "gak ada yang cocok, cari lagi"). Skill ini HANYA mencatat pilihan ke registry — TIDAK melakukan ekstraksi spec, TIDAK develop apapun. Selalu jalankan skill ini setelah /inspo menampilkan kandidat dan user merespon dengan pilihan.
---

# /select — Checkpoint Pemilihan Referensi

Tugas skill ini: menerjemahkan jawaban bebas user jadi update status yang
jelas di registry. Ini bukan tempat menilai kualitas referensi — user yang
mutusin, skill ini cuma mencatat dengan benar.

## Langkah

### 1. Baca kandidat yang ada
Baca `.design/registry/references.json`, cari entry dengan status
`"candidate"` yang paling baru (biasanya hasil `/design-agent:inspo` terakhir).

### 2. Interpretasikan jawaban user
Jawaban user bisa dalam berbagai bentuk — cocokkan ke ID atau ke urutan
tampilan kandidat terakhir (kandidat #1 = ID candidate pertama yang
ditampilkan, dst). Kalau ambigu (misal user bilang "yang biru" tapi ada dua
kandidat biru), tanyakan konfirmasi singkat sebelum menulis apapun ke
registry — jangan menebak.

Kasus yang mungkin:
- **Pilih satu** — 1 referensi jadi `"selected"`, sisanya di kandidat batch
  itu jadi `"rejected"`.
- **Pilih beberapa/gabungan** — semua yang disebut jadi `"selected"`, sisanya
  `"rejected"`.
- **Tolak semua** — semua di batch itu jadi `"rejected"`. Tawarkan ke user:
  "Mau saya cari kandidat baru dengan arahan berbeda? Kasih tau apa yang
  kurang cocok dari yang tadi."

### 3. Update registry
Untuk tiap referensi yang dipilih, ubah di `references.json`:
```json
{
  "status": "selected",
  "selectedAt": "<ISO 8601 sekarang>"
}
```
Untuk yang tidak dipilih di batch yang sama, ubah status jadi `"rejected"`.
Jangan hapus entry — riwayat kandidat yang ditolak tetap berguna buat
konteks nanti.

### 4. Append journal
```json
{"ts":"<ISO 8601>","event":"reference_selected","refId":"R-00X"}
```
Satu baris per referensi yang dipilih. Kalau semua ditolak, catat:
```json
{"ts":"<ISO 8601>","event":"reference_rejected","refIds":["R-00X","R-00Y"],"reason":"user menolak semua kandidat"}
```

### 5. Konfirmasi ke user dan tawarkan langkah berikutnya
Tampilkan ringkasan singkat: referensi mana yang jadi `selected` dengan ID-nya.
Akhiri dengan:
> "Referensi sudah dicatat. Lanjut ekstrak jadi design spec sekarang ([nama
> fitur/halaman])?"

Tunggu konfirmasi user sebelum memanggil `/design-agent:spec` — jangan otomatis lanjut,
walau ini kelihatan seperti langkah logis berikutnya. User mungkin masih mau
menambah referensi lain dulu, atau mengerjakan fitur lain.

## Yang TIDAK boleh dilakukan skill ini
- Menilai atau menyarankan referensi mana yang "lebih bagus" — itu bukan
  perannya, murni mencatat keputusan user
- Langsung lanjut ke `/design-agent:spec` tanpa konfirmasi eksplisit
- Menebak referensi mana yang dimaksud user kalau jawabannya ambigu
