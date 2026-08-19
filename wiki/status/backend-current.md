# Current Status

> Living document. Read this to understand what's done, what's in progress, and what's next.

*Last updated: 2026-08-19*

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

- ✅ **County obesity dataset (2026-08-19)** — new `GET /api/demographics/us_counties_obesity` serving CDC PLACES adult obesity (BMI ≥ 30, adults 18+), crude and age-adjusted with 95% CIs. 3,144 of 3,222 counties populated; nulls are all Puerto Rico. Coalesces two PLACES releases because the newest one omits Kentucky and Pennsylvania entirely. **Deliberately a standalone dataset, not a WDWWA rank factor** — adding it to the rank is an open decision. Full details in `data/cdc_places.md`.
- ✅ **Cache correctness (2026-08-19)** — data endpoints now send `Cache-Control: public, max-age=0, must-revalidate` and answer 304 to conditional requests via `app/caching.py`. Previously they sent no `Cache-Control` at all, so browsers guessed freshness from file age and served stale JSON for days. See `architecture/backend-api-contract.md` → Caching for the three traps involved.
- ✅ **County climate metric (2026-08-19)** — `pleasant_days` added to `US_county_percentages.json` as the 7th WDWWA rank factor. Average days/yr with a high of 60–85°F, a low of 40–68°F and no measurable rain, from 30 years of NOAA nClimGrid-Daily county area averages. 3,109 of 3,222 counties populated; CONUS-only, so AK/HI/PR are null. Three new scripts, full details in `data/nclimgrid.md`.
- ✅ **Asian/NHPI demographics deployed** — the Aug 15 regenerated files were committed in `34c3f3d` and verified live; `nhpi_non_hisp` is present in the production `us_counties` response.
- ✅ **Production deployment fixed** — births endpoint was broken on Render because `smooth_wnh.csv` was gitignored. Pre-baked display data as `app/data/births.json` (59KB). All API endpoints now serve static files from `app/data/`. Verified live at `https://api.wdwwa.com`.

## What's Next
- [ ] **Decide whether obesity becomes a WDWWA rank factor** — the data is live at `us_counties_obesity` and the frontend now paints it as its own layer (crude `obesity_pct`, 2026-08-19). Adding it to the composite would make 8 factors (dropping each existing one from ~1/7 to ~1/8 of the influence) and would unrank nothing new, since the 78 null counties are Puerto Rico, which is already absent from the rank set. Open question: crude or age-adjusted, and which direction counts as desirable.
- [ ] **Asian births data** — the frontend wants White + Asian on the births page but `/api/births` has no Asian series. Raw CDC WONDER D66 (2007+) and KFF (2016–2023) files *do* carry Asian counts; `extract_all_data.py` parses KFF's `Asian` column but only uses it to compute `total_births`. A both-parent Asian equivalent would need new D149 queries and only exists 2016+. Discussed in the frontend wiki at `~/familymaps/wiki/features/race-toggle.md`.
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
| `scripts/add_asian_nhpi_fields.py` | Backfills Asian/NHPI fields onto served demographics JSON |
| `scripts/download_nclimgrid.py` | Downloads NOAA county climate CSVs (resumable) |
| `scripts/compute_pleasant_days.py` | Counts pleasant days/yr per county |
| `scripts/add_pleasant_days_field.py` | Merges `pleasant_days` into the served percentages JSON |
| `scripts/download_cdc_places_obesity.py` | Pulls county obesity from CDC PLACES (2 releases, coalesced) |
| `scripts/build_obesity_dataset.py` | Builds `app/data/US_county_obesity.json` from the PLACES CSV |

## Quick Decision Guide

- **Working on birth data?** → Read `data/overview.md` first, then the specific source wiki
- **Adding a new data source?** → Create `data/{source}/` dir + `wiki/data/{source}.md` + update `data/overview.md` source index
- **Re-running extraction?** → `cd data && python3 extract_all_data.py`
- **Working on a feature?** → Read the relevant `vision/*.md` file
- **Hit a weird data issue?** → Check `learnings/data-quirks.md`

---

*Update this file at the end of each work session.*
