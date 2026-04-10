# Current Status

> Living document. Read this to understand what's done, what's in progress, and what's next.

*Last updated: 2026-04-10*

## Overall State

**All birth data downloads are complete. All data is extracted. The pipeline is fully functional.**

The birth data pipeline covers 1940–2024 at the state level with the best available race breakdown for each era. The frontend displays this data on the births choropleth layer.

## What's Done

- ✅ All 6 data sources downloaded (NHGIS, NBER Historical, NBER Microdata, CDC WONDER, KFF, NCHS docs)
- ✅ Extraction pipeline (`data/extract_all_data.py`) produces `all_data.csv` (8,355 rows) and `best_estimate.csv` (4,317 rows)
- ✅ **Births API endpoint** (`GET /api/births`) — reads `best_estimate.csv`, converts to JSON, serves to frontend
- ✅ Frontend births layer fetches from API (no longer uses static `births-data.json`)
- ✅ 1973–1994 gap filled via NBER Microdata streaming aggregation
- ✅ 1989–1994 WNH fix (`origm` → `ormoth`) applied and re-run
- ✅ 2007–2015 CDC WONDER race gap resolved (bridged race query)
- ✅ KFF cross-validated against CDC WONDER (exact match confirms White = White NH)

## What's In Progress

- 🔴 **1988→1989 metric discontinuity** — `births-data.json` switches from `pct_white` to `pct_white_nh` at 1989, causing a visual cliff (avg -8.3 pts, worst -43.7 pts). See `learnings/data-quirks.md` for root cause analysis and `vision/births-choropleth.md` for proposed solutions. **Needs decision on which fix to apply.**

## What's Next

<!-- Update this section as priorities become clear -->
- [ ] **Fix 1988→1989 discontinuity** — pick a solution from `vision/births-choropleth.md` Options A–D
- [ ] Decide on county-level births data (currently state-only)
- [ ] Fill in product vision open questions (`vision/product.md`)
- [ ] Fill in feature-level open questions (all `vision/*.md` files)
- [ ] Consider animation/playback for births year navigation
- [ ] Decide whether to expand Florida detail layers to other states

## Where Key Files Live

| File | What It Is |
|------|------------|
| `data/extract_all_data.py` | Pipeline that combines all sources |
| `data/extracted_data/all_data.csv` | All sources combined (8,355 rows) |
| `data/extracted_data/best_estimate.csv` | Best source per year×state (4,317 rows) |
| `data/nber_microdata/download_nber_microdata.py` | Streaming download+aggregation script |
| `data/nber_microdata/extracted_data.csv` | 1,122 rows (51 states × 22 years) |

## Quick Decision Guide

- **Working on birth data?** → Read `data/overview.md` first, then the specific source wiki
- **Adding a new data source?** → Create `data/{source}/` dir + `wiki/data/{source}.md` + update `data/overview.md` source index
- **Re-running extraction?** → `cd data && python3 extract_all_data.py`
- **Working on a feature?** → Read the relevant `vision/*.md` file
- **Hit a weird data issue?** → Check `learnings/data-quirks.md`

---

*Update this file at the end of each work session.*
