# Registry Schema

Semua file di sini di-commit ke git. Ini state permanen — skill mana pun yang
jalan (di sesi apapun, kapanpun) HARUS baca dulu sebelum bertindak, dan tulis
balik setelah selesai.

## `project.json`
Metadata proyek & default settings.

```json
{
  "projectName": "string",
  "defaultBuildMethod": "standalone | superpowers",
  "stack": {
    "framework": "string | null",
    "styling": "string | null",
    "notes": "string | null"
  },
  "createdAt": "ISO 8601",
  "updatedAt": "ISO 8601"
}
```
`stack` boleh null di awal — diisi belakangan saat skill `/build` pertama kali dikonfigurasi.

## `references.json`
Kandidat referensi hasil `/inspo`, dipilih/ditolak lewat `/select`.

```json
{
  "references": [
    {
      "id": "R-001",
      "url": "string",
      "source": "mobbin | dribbble | land-book | saas-landing-page | lapa-ninja | really-good-ui | one-page-love | screenlane | behance | awwwards | godly | lainnya",
      "category": "real | concept",
      "searchMode": "link_spesifik | situs_spesifik | bebas",
      "query": "string — brief pencarian yang menghasilkan ini",
      "reason": "string — kenapa relevan, 1 kalimat",
      "screenshotPath": "string | null",
      "status": "candidate | selected | rejected",
      "selectedAt": "ISO 8601 | null"
    }
  ]
}
```
`category`: `"real"` = produk yang sudah live/diimplementasi di produksi
(Mobbin, Land-book, SaaS Landing Page, Lapa Ninja, dll) — token yang
diekstrak dari sini di `/spec` bisa lebih yakin (`stated`/`discussed`).
`"concept"` = eksplorasi visual/mockup (Dribbble, Behance, dll) — belum
tentu bisa diimplementasi persis, token dari sini cenderung butuh lebih
banyak `inferred`/`assumed` di `/spec`.

`searchMode`: mode pencarian yang dipakai `/inspo` buat referensi ini —
`"link_spesifik"` (user kasih URL langsung, di-fetch tanpa search),
`"situs_spesifik"` (user sebut nama situs, search di-scope ke situs itu
saja), atau `"bebas"` (search lintas sumber tanpa arahan situs tertentu).

## `specs.json`
Design spec hasil ekstraksi `/spec` dari referensi terpilih.

```json
{
  "specs": [
    {
      "id": "S-001",
      "featureName": "string",
      "refIds": ["R-001", "R-004"],
      "sections": [
        { "name": "hero", "confidence": "stated|discussed|inferred|assumed" },
        { "name": "features", "confidence": "..." }
      ],
      "sectionsConfirmed": false,
      "tokens": {
        "colors": { "role_name": { "value": "string", "confidence": "stated|discussed|inferred|assumed" } },
        "typography": { "role_name": { "value": "string", "confidence": "..." } },
        "spacing": { "role_name": { "value": "string", "confidence": "..." } },
        "radius": { "role_name": { "value": "string", "confidence": "..." } },
        "shadow": { "role_name": { "value": "string", "confidence": "..." } },
        "motion": { "role_name": { "value": "string", "confidence": "..." } }
      },
      "confidenceSummary": {
        "average": 0.0,
        "assumedRatio": 0.0,
        "blocked": false
      },
      "buildMethod": "standalone | superpowers | null",
      "measuredTokens": {
        "source": "extract-styles | vision",
        "referenceJsonPath": "string | null",
        "sections": [
          { "name": "hero", "screenshotPath": "string", "bbox": { "y": 0, "height": 800 } }
        ]
      },
      "status": "draft | validated | blocked | built",
      "createdAt": "ISO 8601",
      "updatedAt": "ISO 8601"
    }
  ]
}
```

`sections` adalah daftar section halaman (hero, fitur, testimoni, pricing,
footer, dll) yang sudah dikonfirmasi/ditentukan bersama user di `/spec`.
`sectionsConfirmed` HARUS `true` sebelum spec boleh berstatus `"validated"`
atau dipakai `/build` — lihat aturan blocking tambahan di bawah.

### Confidence weight (untuk hitung `confidenceSummary`)
| Marker | Weight |
|---|---|
| `stated` | 1.0 |
| `discussed` | 0.8 |
| `inferred` | 0.5 |
| `assumed` | 0.2 |

Blokir (`blocked: true`) jika `average < 0.4` ATAU `assumedRatio > 0.3`
ATAU `sectionsConfirmed: false`. Struktur halaman yang belum dikonfirmasi
user itu setara dengan spec yang belum siap dipakai, terlepas dari
confidence numerik token visualnya.

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

## `journal.jsonl`
Append-only audit trail. Satu baris = satu event. Jangan pernah di-edit,
cuma di-append.

```json
{"ts":"ISO 8601","event":"reference_selected","refId":"R-001"}
{"ts":"ISO 8601","event":"spec_extracted","specId":"S-001","confidence":0.82}
{"ts":"ISO 8601","event":"spec_blocked","specId":"S-002","reason":"assumedRatio 0.45 > 0.3"}
{"ts":"ISO 8601","event":"build_started","specId":"S-001","method":"standalone"}
{"ts":"ISO 8601","event":"visual_diff","specId":"S-001","diffScore":0.91}
{"ts":"ISO 8601","event":"styles_extracted","specId":"S-001","source":"live-url","refId":"R-001"}
{"ts":"ISO 8601","event":"token_compare","specId":"S-001","iteration":1,"mismatches":3}
{"ts":"ISO 8601","event":"token_compare_converged","specId":"S-001","iteration":2}
```

Event types yang dipakai skill lain: `reference_selected`, `reference_rejected`,
`spec_extracted`, `spec_blocked`, `spec_reanalyzed`, `build_started`,
`build_method_overridden`, `visual_diff`, `build_completed`,
`styles_extracted`, `token_compare`, `token_compare_converged`.
