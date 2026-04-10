# Birth Data Sources — Overview & Coverage

> **Goal:** Compile aggregate birth counts — total births and births by race (targeting White non-Hispanic where available) — by year, state, and county, from 1940 to present.
>
> **Scope:** Pre-aggregated counts preferred. Microdata used only where no pre-aggregated source exists (1973–1994 gap).

---

## Source Index

| Source | Years | Race Data? | Status | Wiki | Data Dir |
|--------|-------|-----------|--------|------|----------|
| NHGIS (IPUMS) | 1915–2007 | 1915–1972 ✅; 1970–2007 totals only | ✅ Downloaded | [nhgis.md](nhgis.md) | `data/nhgis/` |
| NBER Historical | 1940–1968 | 1946–1968 ✅; 1940–1945 totals only | ✅ Downloaded | [nber_historical.md](nber_historical.md) | `data/nber_historical/` |
| NBER Microdata | 1973–1994 | ✅ White/Nonwhite + partial Hispanic | ✅ Downloaded (WNH fix complete) | [nber_microdata.md](nber_microdata.md) | `data/nber_microdata/` |
| CDC WONDER | 1995–2024 | ✅ White NH (all years via bridged race) | ✅ Downloaded | [cdc_wonder.md](cdc_wonder.md) | `data/cdc_wonder/` |
| KFF | 2016–2023 | ✅ White NH (validation) | ✅ Downloaded | [kff.md](kff.md) | `data/kff/` |
| NCHS Public-Use | 1968–2024 | Yes (microdata) | ⏸️ Deprioritized | [nchs.md](nchs.md) | `data/nchs/` |
| **Combined Output** | 1940–2024 | Best available per year×state | ✅ Generated | [pipeline.md](pipeline.md) | `data/extracted_data/` |

---

## Coverage by Era

| Era | Primary Source | White (incl Hisp) | White NH | Status |
|-----|---------------|-------------------|---------|--------|
| 1940–1945 | NHGIS ds224/ds229 | ✅ W/NW | ❌ Impossible | ✅ Done |
| 1946–1968 | NBER Historical + NHGIS | ✅ W/NW | ❌ Impossible | ✅ Done |
| 1968–1972 | NHGIS ds230 | ✅ W/Negro/Other | ❌ Impossible | ✅ Done |
| 1973–1977 | NBER Microdata | ✅ W/NW | ❌ No Hispanic field | ✅ Done |
| 1978–1988 | NBER Microdata | ✅ W/NW | 🟡 Partial (4-16 states) | ✅ Done |
| 1989–1994 | NBER Microdata | ✅ W/NW | ✅ WNH: 48-51/51 states | ✅ Done |
| 1995–2006 | CDC WONDER D10/D27 | ✅ | ✅ White NH | ✅ Done |
| 2007–2024 | CDC WONDER D66 Bridged | ✅ | ✅ White NH (bridged race) | ✅ Done |

---

## Key Issues / Action Items

1. **✅ KFF scraper bug:** Fixed. All 8 years validated.
2. **✅ CDC WONDER download:** All 3 databases (33,302 rows, 1995–2024).
3. **✅ KFF White = White NH:** Cross-validated exact match with CDC WONDER.
4. **✅ 1973–1994 gap:** NBER Microdata streaming download complete (22 years, 1,122 rows).
5. **✅ 2007–2015 D66 race gap:** RESOLVED — re-queried with "Mother's Bridged Race" (D66.V2).
6. **✅ 1989-1994 WNH fix:** `origm` → `ormoth` for 1989+ files. Re-run complete.
7. **🟡 NHGIS ds224 county completeness:** ~48% of county rows lack race data.
8. **🟢 NBER 1940–1945:** NHGIS provides race data for these years instead.

---

## 1973–1994 Gap Investigation (2026-04-09)

Exhaustive search for pre-aggregated state-level race data. **No pre-aggregated source exists.** All alternatives ruled out:

| Source | Result |
|--------|--------|
| NHGIS (all 4 datasets) | ds231 has **total births only** — no race |
| Mendeley/Galofré-Vilà (DOI: 10.17632/52xszfstsd.1) | TFR rates only, no raw counts |
| CDC data.cdc.gov (89yk-m38d) | National-level only — no state column |
| CDC data.cdc.gov (hmz2-vwda) | State-level but **no race** |
| CDC WONDER | Starts at 1995 |
| NCHS VSUS volumes (PDFs) | Tables exist but require OCR — impractical |
| HHS DataHub (qv2g-dfhp) | Not tabular |
| **NBER Microdata** | **Only viable option.** Streaming aggregation script built. |

---

## Extraction Pipeline

**Script:** `data/extract_all_data.py` — see [pipeline.md](pipeline.md) for details.

| Output File | Rows | Description |
|-------------|------|-------------|
| `data/extracted_data/all_data.csv` | 8,355 | All sources combined |
| `data/extracted_data/best_estimate.csv` | 4,317 | Best source per year×state |

---

## Other Investigated Sources (Low Priority)

- Statistical Abstract of the US (PDF, 1878–2012) — spot-checking only
- Historical Statistics of the US (national-level, 1909–1970)
- NCHS NVSR reports (PDF, annual) — CDC WONDER is easier
- ICPSR — alternative access to same microdata
- State vital statistics offices — potential for county-level gap-fill (2005+)

---

*Last updated: 2026-04-10*
