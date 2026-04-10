# Data Quirks & Gotchas

> Specific oddities in data sources that cost significant debugging time. Read this when encountering unexpected data or working with a source for the first time.

## NBER Historical 1940–1945: NOT Race Data

The columns `births_h_p`, `births_nh_p`, `births_m`, `births_o` in 1940-1945 files look like they could be racial categories but are actually **attendant type at birth** (hospital-physician, non-hospital-physician, midwife, other). There is no race column for 1940-1945. Use NHGIS ds224/ds229 for race data in those years.

## NBER Historical: Column Name Inconsistencies

Column names vary across years and require normalization:
- `page_of_pdf` (1940–1947) vs `page_of_pdf_` (1948–1968)
- `births_h_p` vs `births_h` (varies by year)
- `births_nh_p` vs `births_nh_ns` (varies by year)
- `births_o` present in some years, absent in others
- `sub_county` present in most years, absent in 1951–1952

State totals identified by `county == 'total'`, not a separate indicator.

## NHGIS ds231: Total Births Only

The most tempting dataset (1970-2007, modern era) has **only one data column** (`AGWE001` = total births) — no race breakdown at all. This creates the 1973-1994 gap where no NHGIS dataset provides state-level race data.

## NHGIS ds231: Non-Contiguous Years

Years are: 1970, 1975, 1980, 1985, then 1990-2007 annually. Gaps: 1971-74, 1976-79, 1981-84, 1986-89.

## NHGIS Column Names Are Opaque

Columns like `AF1V001`, `AGVB001`, `AGV2003` require codebook files to decode. Each extract includes `*_codebook.txt` files.

## NHGIS: Occurrence vs Residence

ds229 and ds230 have two table sets. Use **residence** tables:
- ds229: `NT005`/`NT006` (not `NT001`/`NT002`)
- ds230: `NT009`/`NT010` (not `NT001`/`NT002`)

Residence data only from 1942+. Pre-1942 is occurrence only.

## NHGIS ds224: County Race ~48% Incomplete

In 1940, 1,486 of 3,109 county rows have empty race fields. State-level is complete.

## CDC WONDER D66: Duplicate Sections

The scraped D66 file had duplicate sections (possibly two query results concatenated). Deduplication on `(year, state, race, hispanic)` is required.

## CDC WONDER: Suppressed Cells

Rows with <10 births suppressed. Small-state race/ethnicity combinations have `Suppressed` values parsed as NaN.

## NBER Microdata: 2005+ Has No Geography

Starting in 2005, `stateres` and `cntyres` are removed from public-use files. National-level aggregation is the only option for recent microdata.

## NBER Microdata: 1968-1971 Are 50% Samples

Each record represents 2 births (`recwt=2`). Not relevant for our 1973-1994 range but important if expanding.

## ✅ 1988→1989 Metric Switch Discontinuity (RESOLVED)

**Was the single biggest data quality issue. Resolved by `build_smooth_wnh.py`.**

The `births-data.json` file switches from `pct_white` (White including Hispanic) in 1988 to `pct_white_nh` (White Non-Hispanic) in 1989. These are fundamentally different metrics, and the switch creates a massive visual cliff on the map:

| State | 1988 (pct_white) | 1989 (pct_white_nh) | Jump |
|-------|-----------------|--------------------|----|
| New Mexico | 82.71% | 39.06% | **-43.65** |
| California | 80.51% | 44.29% | **-36.22** |
| Texas | 83.94% | 49.00% | **-34.94** |
| Arizona | 85.09% | 58.59% | **-26.50** |
| National avg | — | — | **-8.28** |

**Root cause:** In 1988, only 16 states reported Hispanic origin via `origm`. In 1989, 48/51 states started reporting via `ormoth`. The conversion script classified 1989+ as `white_nh` years because enough states had WNH data.

**Compounding issue — unknown Hispanic origin:** Even for states that reported in BOTH years, there's a quality gap. New York in 1988 had 43,565 white births (21%) with unknown Hispanic origin, excluded from WNH. In 1989, unknowns dropped to 7,040 (3.3%), making WNH jump from 43.88% to 55.86%. Distributing 1988 unknowns proportionally (75.4% → NH) produces 55.59%, matching 1989's 55.86% almost exactly.

**1994→1995 discontinuity (NBER→CDC WONDER):** New York also jumps -7.13 points at this boundary (51.85% → 44.72%), suggesting NBER Microdata WNH overestimates compared to CDC WONDER's authoritative values.

**Resolution:** Built `data/build_smooth_wnh.py` which produces `smooth_wnh.csv` with a smooth `pct_white_nh_smooth` column. Now uses D149 actual both-parent WNH for 2016+, phased-in correction for 1980-2015, and Hispanic estimation for pre-1978. The 1988→1989 boundary is now smooth (avg jump <0.2pt). See `wiki/data/overview.md` for details.

## No Pre-Aggregated State-Level WNH Birth Data Before 1989

Exhaustive search (NCHS NVSR, VSUS volumes, NCHS Series 24, CDC data.gov, KIDS COUNT, Census) confirmed: **no official, machine-readable, state-level WNH birth count data exists before 1989.** The NCHS published "Births of Hispanic Parentage" reports for 23 states in 1983-1985 (NCHS Series 24, No. 2), but these are PDF tables requiring OCR. The VSUS annual volumes have similar tables. The NBER Microdata is the only machine-readable source with Hispanic origin data for the 1978-1988 period, but it requires streaming aggregation and has quality limitations (varying unknown rates by state and year).

## ✅ Post-1980 WNH Data Was Mother-Only (RESOLVED)

**Identified & resolved 2026-04-10.** Post-1980 WNH birth data measured the *mother's* race/ethnicity, not the *baby's*. This overstated the WNH birth % by ~10 percentage points nationally (49.1% mother-only vs 39.1% both-parent in 2024).

**Resolution:** Downloaded CDC WONDER D149 (2016-2024 expanded) with father's race/ethnicity. Computed per-state both-parent correction factors (national avg 0.794). Updated `build_smooth_wnh.py` with historical phase-in:
- **Pre-1980:** No correction (child's race already derived from both parents)
- **1980-2015:** Factor linearly interpolated from 1.0 (1980) to D149 factor (2016)
- **2016+:** Actual D149 both-parent data

**Remaining caveat:** ~10% of births have father's race "Unknown/Not Stated" — these are excluded from the both-parent count, which may slightly undercount WNH births.

## NBER Microdata: 3 States Fail Quality Validation

New York, District of Columbia, and Rhode Island have NBER→CDC WNH ratio discrepancies >3 percentage points at the 1994→1995 boundary. New York is the worst: NBER 1994 shows WNH ratio of 0.707, but CDC 1995 shows 0.610. This is likely caused by incomplete reporting of Hispanic origin in the pre-1989 `origm` field and residual unknown-rate effects in the 1989-1994 `ormoth` field for these states. Use estimation rather than NBER actual WNH data for these 3 states.

---

*Update when new quirks are discovered. Each entry should save at least 30 minutes of debugging.*
