# Action & Download Log

> Chronological record of all significant actions. Append new entries at the bottom.

| Date | Source | Action | Result |
|------|--------|--------|--------|
| 2026-04-09 | NBER 1940–1968 | Downloaded births_data.zip (507 MB) | ✅ 29 Stata files |
| 2026-04-09 | NHGIS | API extract #1: 4 VS datasets | ✅ 168 CSVs (6 MB) |
| 2026-04-09 | CDC WONDER | Playwright scrape of D10/D27/D66 | ✅ 33,302 rows |
| 2026-04-09 | KFF | Selenium scrape (bug fix + re-download) | ✅ 416 rows |
| 2026-04-09 | NCHS | Downloaded user guides | ✅ 2 PDFs (reference) |
| 2026-04-09 | Mendeley | Downloaded Galofré-Vilà TFR dataset | ⚠️ TFR only, not usable |
| 2026-04-09 | ALL | Exhaustive 1973–1994 gap search | ❌ No pre-aggregated source |
| 2026-04-09 | ALL | Extraction pipeline run | ✅ all_data.csv + best_estimate.csv |
| 2026-04-10 | NBER Microdata | Streaming aggregation 1973–1994 | ✅ Complete (22 years, 1,122 rows, 5 hours) |
| 2026-04-10 | NBER Microdata | Bug fix: origm→ormoth for 1989-1994 | ✅ Complete (6 years, 2.3 hours; 48-51/51 states WNH) |
| 2026-04-10 | CDC WONDER D66 | Bridged Race re-query (D66.V2) | ✅ 27,540 raw rows, 918 extracted |
| 2026-04-10 | ALL | Extraction pipeline re-run with WNH-fixed 1989-1994 | ✅ 8,355 rows combined, 4,317 best estimate, 1,932 with WNH |
| 2026-04-10 | Wiki | Restructured wiki into tiered context system | ✅ constitution/index/vision/data/learnings/status/scratchpad |
| 2026-04-10 | Births viz | Investigated 1988→1989 WNH discontinuity | 🔴 Root cause: metric switch from pct_white→pct_white_nh at 1989. Avg -8.3 pts, worst NM -43.7 pts. 4 solutions proposed in vision/births-choropleth.md |
| 2026-04-10 | API | Created `GET /api/births` endpoint (`app/routers/births.py`) — reads `best_estimate.csv`, converts to JSON with FIPS keys/year types, caches in memory | ✅ 0 mismatches vs prior static JSON |
| 2026-04-10 | Frontend | Updated `single-ratio.component.ts` to fetch births from API instead of static `births-data.json` | ✅ Tested — map loads, year nav works |

| 2026-04-10 | Repo | Undid accidental `git add .`; updated `.gitignore` to exclude `data/*/raw-data/`, `data/**/*.csv`, `data/**/*.zip` | ✅ Only 8 Python scripts trackable in data/ |
| 2026-04-10 | API | Added `/api/geo/us_states` endpoint (moved `states-10m.json` → `US_states_geo.topojson`) | ✅ Pushed |
| 2026-04-10 | Frontend | Deleted `births-data.json` + `states-10m.json` from `public/`; all data now fetched from API | ✅ Pushed |

| 2026-04-10 | Research | Investigated smooth WNH series: searched NCHS NVSR, VSUS volumes, NCHS Series 24 (Hispanic parentage 1983-85), Census Hispanic % by state (1980/1990), CDC data.gov, KIDS COUNT | No pre-aggregated state-level WNH birth data exists before 1989 |
| 2026-04-10 | Pipeline | Built `data/build_smooth_wnh.py` — hybrid estimation: CDC actual (1995+), validated NBER actual (1978-1994 where quality confirmed), Census-calibrated estimation (pre-1978). Output: `smooth_wnh.csv` (4,317 rows) | ✅ Smooth series; 1994→1995 avg jump 0.00pt; 48/51 states validated |
| 2026-04-10 | API+FE | Integrated smooth WNH: `births.py` reads `smooth_wnh.csv`, uses `pct_white_nh_smooth` for all years. Frontend labels pre-1978 as "est.", all years now "White NH Births". Old -8.3pt avg cliff → -0.16pt avg. | ✅ Both repos updated, builds pass |

| 2026-04-10 | Research | Identified mother-only vs both-parent WNH methodology issue: post-1980 data only captures mother's race, not baby's | 🔴 10pt gap nationally between mother-only WNH (49.1%) and both-parent WNH (39.1%) in 2024 |
| 2026-04-10 | CDC WONDER D149 | Downloaded expanded natality 2016-2024 with father's race/ethnicity (Playwright scrape) | ✅ 12,393 rows (Year × State × Father Race × Father Hispanic, filtered to WNH mothers) |
| 2026-04-10 | Pipeline | Built `extract_d149_both_parent_wnh.py` — computes both-parent WNH from D149 data | ✅ 459 state×year rows; per-state correction factors computed |
| 2026-04-10 | Pipeline | Updated `build_smooth_wnh.py` to use both-parent WNH: D149 actual for 2016+, correction factor for earlier years (avg factor 0.794) | ✅ All 4,317 rows updated; smooth series maintained |
| 2026-04-10 | API | Updated `births.py` docstrings to reflect both-parent WNH methodology | ✅ |
| 2026-04-10 | Wiki | Updated constitution, vision/births-choropleth, learnings/race-categories, learnings/data-quirks, data/overview to document both-parent WNH methodology | ✅ |
| 2026-04-10 | Pipeline | Fixed pre-1980 double-correction bug: both-parent factor was applied to all years, but pre-1980 "child's race" data was already both-parent. Now: no correction pre-1980, linear phase-in 1980→2016 | ✅ Maine 1940: 81.5%→99.0%; national 1940: 69.5%→87.0% |
| 2026-04-10 | Frontend | Updated births layer labels: legend="White NH Babies Born (%)", tooltip="WNH Babies: X%" | ✅ Build passes |
| 2026-04-10 | Wiki | Full wiki sweep: updated all files to reflect resolved both-parent methodology, D149 download complete, pre-1980 phase-in fix, frontend label changes | ✅ |

| 2026-04-10 | Deploy | Pre-baked `births.json` (59KB) from `smooth_wnh.csv`; updated births router to serve static JSON instead of parsing CSV at startup. Pushed to main → Render auto-deployed. | ✅ Live at `https://api.wdwwa.com/api/births` — 85 years, 51 states verified |
| 2026-04-28 | API | Added `allow_origin_regex` to CORS middleware in `app/main.py` matching RFC 1918 LAN ranges (10/8, 172.16/12, 192.168/16) on any port. Allows `ng serve --host 0.0.0.0` phone testing without per-IP allowlisting. | ✅ Pushed to main → Render auto-deploy |

---

*Append new entries here. Don't modify old entries.*
