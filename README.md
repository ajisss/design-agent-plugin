# design-agent

Plugin Claude Code buat pipeline design-to-code: cari referensi (Dribbble,
Mobbin, Land-book, SaaS Landing Page, dll) → pilih → ekstrak jadi design
spec dengan confidence marker → develop dengan visual QA wajib.

Dibuat buat mencegah AI "ngarang" (AI slop) saat mereplikasi referensi
design — setiap nilai token yang gak pasti WAJIB dilabeli, dan build
otomatis di-block kalau confidence terlalu rendah.

## Install

### Dari GitHub (kalau lo sudah push repo ini ke GitHub)
```
/plugin marketplace add <username-github>/<nama-repo>
/plugin install design-agent@design-agent-marketplace
/reload-plugins
```

### Test lokal dulu sebelum push ke GitHub
```bash
claude --plugin-dir /path/ke/design-agent-plugin
```

Cek `/agents` dan skill list buat pastiin `design-agent:inspo`,
`design-agent:select`, `design-agent:spec`, `design-agent:build`,
`design-agent:init` muncul.

## Cara pakai

1. **Sekali per project baru**, jalankan setup:
   > "Setup design agent di project ini" (atau langsung sebut
   > `/design-agent:init` kalau plugin command style itu didukung versi
   > Claude Code lo)

   Ini bikin `CLAUDE.md`, `CONTEXT.md`, dan `.design/registry/` di project
   lo saat ini.

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
  ├── spec/SKILL.md        ← ekstrak jadi design token + confidence + struktur section
  └── build/SKILL.md       ← implementasi + visual QA
hooks/
  ├── hooks.json          ← registrasi hook PostToolUse
  ├── validate-tokens.py  ← otomatis: cek hex color di luar spec
  ├── visual-diff.py      ← manual (dipanggil skill build): screenshot & diff
  └── requirements.txt
```

## Prinsip inti
- Registry (`.design/registry/`) adalah sumber kebenaran, bukan chat history
- Checkpoint adalah hard stop, bukan saran
- Confidence marker wajib di tiap token yang diekstrak dari referensi
- Visual QA wajib sebelum build dianggap selesai

## Update plugin
Setelah edit file di repo ini, kalau sudah dipush ke GitHub:
```
/plugin marketplace update
/reload-plugins
```

**Catatan versi:** `plugin.json` punya field `version` — kalau lo ingin
tiap commit baru otomatis dianggap update tanpa perlu bump versi manual,
hapus field `version` dari `plugin.json` (Claude Code akan pakai git commit
SHA sebagai penanda versi).
