# Current Status

> Living document. Read this to understand what's done, what's in progress, and what's next.

*Last updated: 2026-04-10*

## Overall State

**All birth data downloads are complete. Both-parent WNH pipeline is fully functional. Frontend updated.**

The birth data pipeline covers 1940–2024 at the state level, now measuring **both-parent WNH** (% of babies where both mother and father are White Non-Hispanic). The frontend displays this on the births choropleth layer with label "White NH Babies Born (%)".

## What's Done

- ✅ All 7 data sources downloaded (NHGIS, NBER Historical, NBER Microdata, CDC WONDER D10/D27/D66, CDC WONDER D149, KFF, NCHS docs)
- ✅ Extraction pipeline (`data/extract_all_data.py`) produces `all_data.csv` (8,355 rows) and `best_estimate.csv` (4,317 rows)
- ✅ **Births API endpoint** (`GET /api/births`) — reads `smooth_wnh.csv`, serves both-parent WNH data
- ✅ Frontend births layer fetches from API, labels: "White NH Babies Born (%)" / "WNH Babies: X%"
- ✅ 1973–1994 gap filled via NBER Microdata streaming aggregation
- ✅ 1989–1994 WNH fix (`origm` → `ormoth`) applied and re-run
- ✅ 2007–2015 CDC WONDER race gap resolved (bridged race query)
- ✅ KFF cross-validated against CDC WONDER (exact match confirms White = White NH)
- ✅ **Both-parent WNH pipeline** — `data/build_smooth_wnh.py` produces a both-parent WNH series:
  - **2016-2024:** CDC WONDER D149 actual both-parent WNH (father + mother race/ethnicity)
  - **1980-2015:** Mother-only WNH × correction factor, linearly phased in from 1.0 (1980) to D149 factor (2016)
  - **Pre-1980:** No both-parent correction (child's race already from both parents); Hispanic adjustment still applied
  - **National avg factor:** 0.794 (both-parent is ~80% of mother-only WNH)
  - **National impact (2024):** Mother-only = 49.1% → Both-parent = 39.1% (10pt gap)
- ✅ **Pre-1980 double-correction bug fixed** — the both-parent correction was initially applied to all years including pre-1980, where "child's race" was already derived from both parents. Now no correction is applied pre-1980, and 1980-2015 uses a gradual phase-in.

## What's In Progress

Nothing actively in progress.

## Recently Completed

- ✅ **Production deployment fixed** — births endpoint was broken on Render because `smooth_wnh.csv` was gitignored. Pre-baked display data as `app/data/births.json` (59KB). All API endpoints now serve static files from `app/data/`. Verified live at `https://api.wdwwa.com`.

## What's Next

- [ ] Re-process NBER Microdata (1973-2004) with `frace` for direct both-parent WNH (~5+ hours download)
- [ ] Decide on county-level births data (currently state-only)
- [ ] Fill in product vision open questions (`vision/product.md`)
- [ ] Fill in feature-level open questions (all `vision/*.md` files)
- [ ] Consider animation/playback for births year navigation
- [ ] Decide whether to expand Florida detail layers to other states

## Where Key Files Live

| File | What It Is |
|------|------------|
| `data/extract_all_data.py` | Pipeline that combines all sources |
| `data/build_smooth_wnh.py` | Builds both-parent WNH smooth series |
| `data/extracted_data/all_data.csv` | All sources combined (8,355 rows) |
| `data/extracted_data/best_estimate.csv` | Best source per year×state (4,317 rows) |
| `data/extracted_data/smooth_wnh.csv` | Final both-parent WNH series (4,317 rows) — **what the API serves** |
| `data/cdc_wonder/download_d149_father_race.py` | D149 Playwright scraper (father's race) |
| `data/cdc_wonder/extract_d149_both_parent_wnh.py` | Extracts both-parent WNH from D149 |
| `data/cdc_wonder/extracted_d149_both_parent_wnh.csv` | 459 rows: per-state both-parent counts (2016-2024) |
| `data/nber_microdata/download_nber_microdata.py` | Streaming download+aggregation script |
| `data/nber_microdata/extracted_data.csv` | 1,122 rows (51 states × 22 years) |
| `app/data/births.json` | Pre-baked births display data (59KB, committed to git) |
| `app/routers/births.py` | API endpoint serving births data (loads births.json) |

## Quick Decision Guide

- **Working on birth data?** → Read `data/overview.md` first, then the specific source wiki
- **Adding a new data source?** → Create `data/{source}/` dir + `wiki/data/{source}.md` + update `data/overview.md` source index
- **Re-running extraction?** → `cd data && python3 extract_all_data.py`
- **Working on a feature?** → Read the relevant `vision/*.md` file
- **Hit a weird data issue?** → Check `learnings/data-quirks.md`

---

*Update this file at the end of each work session.*
