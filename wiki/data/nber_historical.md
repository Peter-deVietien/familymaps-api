# NBER Vital Statistics of the US — Births 1940–1968

**Source URL:** https://www.nber.org/research/data/vital-statistics-us-births-1940-1968

**Script:** `download_nber_historical.py`

---

## Status: ✅ DOWNLOADED

| Field | Value |
|-------|-------|
| Claimed years | 1940–1968 |
| Actual years obtained | **1940–1968** (29 cleaned Stata files confirmed) |
| File format | Stata .dta (cleaned), also Excel and PDF versions |
| Download size | 507 MB (zip), ~737 MB extracted |
| Geographic level | State + County (varies by year — see documentation) |
| Race categories | **1940–1945: NO race breakdown** (attendant type only); **1946–1968: White / Nonwhite** |
| States covered | 49 in 1940 (no AK/HI); 50 from 1959 (AK added); 51 from 1960 (HI added) |

## Downloaded Files

```
raw-data/
├── births_data.zip                     (507 MB)
├── births_data/
│   ├── 1_births_data-original_pdf/     (scanned PDFs of original volumes)
│   ├── 2_births_data-original_excel/   (raw Excel from data entry)
│   ├── 3_births_data-formatted_excel/  (standardized Excel)
│   ├── 4_births_data-uncleaned_stata/  (uncleaned + do-file)
│   ├── 5_births_data-cleaned_stata/    (29 cleaned .dta files — USE THESE)
│   ├── natality_documentation_all.xls  (year-by-year field documentation, 143 KB)
│   └── births_data_cleaning.doc        (0 bytes — empty/corrupted in the archive)
```

## Cleaned Stata Files — Detailed Column Analysis

The schema varies significantly across years. There are two distinct eras:

### Era 1: 1940–1945 (NO race breakdown)

| Year | Rows | Columns |
|------|------|---------|
| 1940–1945 | ~4,885 each | `page_of_pdf`, `state`, `county`, `sub_county`, `births`, `births_h_p`, `births_nh_p`, `births_m`, `births_o`, `year` |

These files have **no `race` column**. The breakdown columns represent **attendant type at birth**, not race:
- `births` = total births
- `births_h_p` = hospital, physician-attended
- `births_nh_p` = non-hospital, physician-attended
- `births_m` = midwife-attended
- `births_o` = other attendant

The attendant columns sum to total births (verified: e.g., Alabama 1940: 12,971 + 29,465 + 20,038 + 464 = 62,938 = births).

**For 1940–1945, this source provides total births only — race data must come from NHGIS (ds224 or ds229).**

### Era 2: 1946–1968 (White / Nonwhite breakdown)

| Year Range | Rows | Columns |
|------------|------|---------|
| 1946–1947 | ~7,500–7,600 | `page_of_pdf`, `state`, `county`, `sub_county`, `race`, `births`, `births_h_p`, `births_nh_p`, `births_m`, `year` |
| 1948–1959 | ~5,100–8,400 | `page_of_pdf_`, `state`, `county`, `sub_county`, `race`, `births`, `births_h_p`, `births_nh_p`, `births_m`, `year` (some have `births_o`) |
| 1960–1964 | ~9,200–9,300 | `page_of_pdf_`, `state`, `county`, `sub_county`, `race`, `births`, `births_h_p`, `births_nh_ns`, `year` |
| 1965–1968 | ~9,300 | `page_of_pdf_`, `state`, `county`, `sub_county`, `race`, `births`, `births_h`/`births_h_p`, `births_nh_ns`, `year` |

Race column values: `total`, `white`, `nonwhite` (3 rows per geographic unit).

Column name inconsistencies across years:
- `page_of_pdf` (1940–1947) vs `page_of_pdf_` (1948–1968)
- `births_h_p` vs `births_h` (varies by year)
- `births_nh_p` vs `births_nh_ns` (varies by year)
- `births_o` present in some years but not others
- `sub_county` present in most years, absent in 1951–1952

## Geographic Detail

- 49 states in 1940 (Birth Registration Area complete since 1933, but no AK/HI)
- Alaska added 1959, Hawaii added 1960
- County-level data in all years, with sub-county in most
- State totals identified by `county == 'total'`

## Race Categories

- **1940–1945:** No race breakdown available from this source
- **1946–1968:** White / Nonwhite (total/white/nonwhite per geographic unit)
- Some years may have more detail in the uncleaned files, but cleaned files use total/white/nonwhite
- **No Hispanic origin** — did not exist on birth certificates until 1978
- "White" here includes Hispanic whites

## Documentation

`natality_documentation_all.xls` describes for each year:
- Whether county-level data is available
- Whether race breakdown is available
- Whether attendant breakdown is available
- Whether urbanicity breakdown is available
- Source file name and page numbers from original volumes

## Role in Our Pipeline

This is a primary source for **1946–1968** aggregate birth counts with race breakdown, and **1940–1945** for total births only. Already pre-aggregated (no microdata processing needed).

For the 1940–1945 race gap, NHGIS (ds224 and ds229 datasets) provides White/Nonwhite breakdown at state and county level for the same period.

## Processing Required

The Stata .dta files can be read with:
- Python: `pandas.read_stata('clean_natality1940.dta')`
- R: `haven::read_dta()`
- Stata: `use clean_natality1940.dta`

Key processing considerations:
- Column names vary across years — normalize before merging
- Filter to `race == 'total'` or `race == 'white'` rows for 1946+
- Filter to state-level with `county == 'total'` if only state data needed
- 1940–1945 files have no `race` column — use NHGIS for race breakdown

## Download & Processing Learnings

### Download
- The entire dataset is a single zip file (`births_data.zip`, 507 MB) from the NBER website. No API or authentication needed.
- The zip contains 5 processing stages (original PDFs → raw Excel → formatted Excel → uncleaned Stata → cleaned Stata). Only folder `5_births_data-cleaned_stata/` is needed for analysis.
- `births_data_cleaning.doc` in the archive is 0 bytes (empty/corrupted) — the documentation file that was supposed to describe the cleaning process is missing.

### Reading the Data
- Stata `.dta` files can be read directly with `pandas.read_stata('clean_natality1940.dta')` — no Stata license needed.
- The files are small enough to load fully into memory (each file is a few hundred KB to a few MB).

### Schema Gotchas
- **1940–1945 do NOT have a `race` column.** The breakdown columns (`births_h_p`, `births_nh_p`, `births_m`, `births_o`) look like they could be racial categories but are actually **attendant type at birth** (hospital-physician, non-hospital-physician, midwife, other). This is easy to mistake without checking the documentation.
- **Column names are inconsistent across years** and require normalization before merging:
  - `page_of_pdf` (1940–1947) vs `page_of_pdf_` (1948–1968) — trailing underscore
  - `births_h_p` vs `births_h` — varies by year
  - `births_nh_p` vs `births_nh_ns` — varies by year
  - `births_o` present in some years, absent in others
  - `sub_county` present in most years, absent in 1951–1952
- State totals are identified by `county == 'total'`, not by a separate state-level indicator.
- The `race` column (1946+) has string values `'total'`, `'white'`, `'nonwhite'` — 3 rows per geographic unit. Total = White + Nonwhite (verified).

## Limitations

- **1940–1945: No race breakdown** (attendant type only) — must use NHGIS for race
- 1946–1968: Race is White/Nonwhite only — no Hispanic breakdown (not possible for this era)
- County coverage varies by year
- Column names inconsistent across years (require normalization)
- Pre-1959 data missing Alaska; pre-1960 missing Hawaii

---

## Extraction (2026-04-09)

Data extracted to `extracted_data.csv` by `data/extract_all_data.py`.

| Period | Rows | White Births? | Notes |
|--------|------|---------------|-------|
| 1940–1945 | 345 | No — total births only | No `race` column in source files |
| 1946–1968 | 1,095 | Yes (White/Nonwhite) | Filtered to `county=='total'` for state-level; pivoted race column |
| **Total** | **1,440** | | 51 states (49 pre-1959, 50 from 1959, 51 from 1960) |

### Extraction Notes

- Read cleaned Stata files (`5_births_data-cleaned_stata/clean_natality{year}.dta`) using `pandas.read_stata()`
- State-level rows identified by `county == 'total'`
- 1946-1968: Pivoted from 3 rows per state (total/white/nonwhite) to 1 row per state with separate columns
- Column name inconsistencies handled (e.g., `page_of_pdf` vs `page_of_pdf_`, `births_h_p` vs `births_h`)
- No White NH data possible (Hispanic origin not recorded until 1978)
- For 1940-1945, NHGIS ds224/ds229 provides the race breakdown that this source lacks

---

*Last updated: 2026-04-09 (extraction complete; 1,440 rows, 1940–1968)*
