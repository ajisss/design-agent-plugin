# design-agent

Plugin Claude Code buat pipeline design-to-code: cari referensi (Dribbble,
Mobbin, Land-book, SaaS Landing Page, dll) → pilih → ekstrak jadi design
spec dengan confidence marker → develop dengan visual QA wajib.

Dibuat buat mencegah AI "ngarang" (AI slop) saat mereplikasi referensi
design — setiap nilai token yang gak pasti WAJIB dilabeli, dan build
otomatis di-block kalau confidence terlalu rendah.

## Install

Repo ini **public** — siapapun bisa install langsung, gak perlu akses khusus.

### Dari GitHub
Jalankan **urut**, satu-satu — jangan lompat ke `/plugin install` sebelum
`/plugin marketplace add` selesai:
```
/plugin marketplace add ajisss/design-agent-plugin
/plugin install design-agent@design-agent-marketplace
/reload-plugins
```

**Cara verifikasi udah beneran ke-install** (bukan cuma marketplace-nya
ke-add): buka `~/.claude/settings.json`, pastikan ada
`"design-agent@design-agent-marketplace": true` di `enabledPlugins`.
Kalau gak ada, berarti `/plugin install` belum jalan/belum selesai —
marketplace add doang gak cukup, plugin-nya harus di-install terpisah.

> **Jangan test lewat ketik `/design-agent` di prompt.** Skill di plugin
> ini dipanggil otomatis oleh Claude berdasarkan kalimat lo (natural
> language), BUKAN lewat slash command manual yang diketik — jadi
> `/design-agent` muncul "No commands match" itu **normal**, bukan tanda
> gagal install. Test yang benar: ketik brief biasa, mis. *"cari referensi
> buat landing page SaaS, ada hero, fitur, pricing, CTA"*, dan lihat apakah
> **Skill(inspo)** ke-trigger.

### Test lokal (kalau lo develop plugin ini sendiri)
```bash
claude --plugin-dir /path/ke/folder/design-agent-plugin
```

## Cara pakai

1. **Sekali per project baru**, jalankan setup — ketik kalimat biasa:
   > "Setup design agent di project ini"

   (skill `init` yang otomatis kepanggil dari kalimat ini, gak perlu ketik
   `/design-agent:init` secara literal). Ini bikin `CLAUDE.md`, `CONTEXT.md`,
   dan `.design/registry/` di project lo saat ini.

2. **Install dependency** buat hook & visual QA (sekali per environment):
   ```bash
   pip install -r ~/.claude/plugins/cache/design-agent/*/hooks/requirements.txt
   playwright install chromium
   ```
   (sesuaikan path cache kalau beda di sistem lo — cek lewat
   `find ~/.claude/plugins/cache -name requirements.txt -path "*design-agent*"`)

3. **Mulai brief**, mis: "cari referensi buat landing page SaaS fintech,
   ada hero, fitur, pricing, CTA" — skill `inspo` otomatis kepanggil.

4. Ikuti alur: pilih referensi → konfirmasi lanjut spec → review
   confidence → konfirmasi build → visual QA.

## Struktur plugin

```
.claude-plugin/
  ├── plugin.json        ← manifest plugin
  └── marketplace.json   ← biar repo ini bisa langsung di-add sebagai marketplace
skills/
  ├── init/SKILL.md       ← setup project (sekali per project)
  ├── inspo/SKILL.md      ← cari & kurasi referensi
  ├── select/SKILL.md     ← checkpoint pemilihan referensi
  ├── spec/
  │   ├── SKILL.md          ← ekstrak jadi design token + confidence + struktur section
  │   └── SCHEMA.md         ← dokumentasi struktur registry (di-copy /init ke tiap project)
  └── build/SKILL.md       ← implementasi + visual QA
hooks/
  ├── hooks.json          ← registrasi hook PostToolUse
  ├── validate-tokens.py  ← otomatis: cek hex color di luar spec
  ├── extract-styles.py   ← dipanggil skill spec & build: ekstraksi computed-style terukur (Playwright)
  ├── compare-tokens.py   ← dipanggil skill build: bandingkan token referensi vs hasil build
  ├── visual-diff.py      ← manual (dipanggil skill build): screenshot & pixel diff pelengkap
  ├── requirements.txt
  └── tests/              ← unit test untuk fungsi murni di atas (dev-only)
```

## Prinsip inti
- Registry (`.design/registry/`) adalah sumber kebenaran, bukan chat history
- Checkpoint adalah hard stop, bukan saran
- Confidence marker wajib di tiap token yang diekstrak dari referensi
- Visual QA wajib sebelum build dianggap selesai

## Update plugin
Setelah edit file di repo ini dan sudah dipush ke GitHub, urutannya
**update dulu marketplace-nya, baru reload** — jangan kebalik:
```
/plugin marketplace update
/reload-plugins
```

Kalau plugin ini **sudah pernah di-install sebelumnya** dan `version` di
`plugin.json` di-bump (mis. 1.0.0 → 1.1.0), cache lokal versi lama kadang
gak otomatis ke-replace cuma dengan `marketplace update` + `reload`. Kalau
setelah reload masih kerasa pakai versi lama (cek isi
`~/.claude/plugins/cache/design-agent-marketplace/design-agent/<versi>/`),
uninstall dulu baru install ulang:
```
/plugin uninstall design-agent
/plugin install design-agent@design-agent-marketplace
/reload-plugins
```

**Catatan versi:** `plugin.json` punya field `version` — kalau lo ingin
tiap commit baru otomatis dianggap update tanpa perlu bump versi manual,
hapus field `version` dari `plugin.json` (Claude Code akan pakai git commit
SHA sebagai penanda versi).

## Troubleshooting

| Gejala | Kemungkinan sebab | Solusi |
|---|---|---|
| Ketik `/design-agent` → "No commands match" | **Ini normal**, bukan error — skill dipanggil otomatis lewat natural language, bukan slash command manual | Test pakai kalimat biasa, mis. "cari referensi buat X", bukan ketik command |
| Skill gak ke-trigger sama sekali walau udah pakai kalimat biasa | Plugin belum ke-install (marketplace doang ke-add) | Cek `~/.claude/settings.json` → `enabledPlugins` harus ada `"design-agent@design-agent-marketplace": true`. Kalau gak ada, jalankan `/plugin install design-agent@design-agent-marketplace` |
| Fitur baru yang udah dipush ke GitHub belum kerasa efeknya | Cache plugin lokal masih versi lama | `/plugin marketplace update` dulu, **baru** `/reload-plugins`. Kalau masih lama, uninstall+install ulang (lihat "Update plugin" di atas) |
| Cuma jalan di satu folder project tertentu, gak di folder lain | Kemungkinan besar bukan soal plugin — cek `enabledPlugins` di `~/.claude/settings.json`, kalau plugin beneran enabled, dia aktif di SEMUA folder. `.design/registry/` sendiri memang dibuat per-folder (itu yang diharapkan) | Pastikan plugin enabled secara global (lihat baris di atas), lalu test di folder project lain |
