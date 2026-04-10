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

---

*Append new entries here. Don't modify old entries.*
