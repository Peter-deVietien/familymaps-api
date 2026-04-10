# NHGIS (IPUMS) — Vital Statistics

**Source URL:** https://www.nhgis.org/

**Script:** `download_nhgis.py`

---

## Status: ✅ DOWNLOADED

| Field | Value |
|-------|-------|
| Claimed years | 1915–2007 |
| Actual years obtained | 1915–2007 (168 CSV files across 4 datasets) |
| Geographic level | State, County |
| Content | Aggregate birth counts (not microdata) |
| Race breakdowns | White/Nonwhite (1915-1959), White/Negro/Other (1959-1972), **Total only** (1970-2007) |
| Access | Free IPUMS account — registered, API key in `.env` |
| API | Yes — https://developer.ipums.org/docs/v2/apiprogram/apis/nhgis/ |
| Extract # | 1 (submitted and downloaded 2026-04-09) |

## Downloaded Data

| Dataset | ID | Years | Files | Tables | Race |
|---------|------|-------|-------|--------|------|
| 1915-1941 VS | `ds224` | 1915–1941 (27 years) | 54 CSVs (27 state + 27 county) | NT001 (total), NT002 (by race) | White/Nonwhite (2 vars) |
| 1939-1959 VS | `ds229` | 1939–1959 (21 years) | 42 CSVs (21 state + 21 county) | NT001/NT002 (occurrence), NT005/NT006 (residence) | White/Nonwhite (2 vars) |
| 1959-1972 VS | `ds230` | 1959–1972 (14 years) | 28 CSVs (14 state + 14 county) | NT001/NT002 (occurrence), NT009/NT010 (residence) | White/Negro/Other (3 vars) |
| 1970-2007 VS | `ds231` | 1970, 1975, 1980, 1985, 1990–2007 (22 years) | 44 CSVs (22 state + 22 county) | NT002 (total only) | **None** — total births only |

### File Location

```
data/nhgis/raw-data/
├── nhgis_extract_1_tableData.zip          # 6 MB zip
├── nhgis_extract_1_codebookPreview.zip    # 298 KB codebooks
├── nhgis_extract_1/nhgis0001_csv/         # 168 CSV files + codebooks
│   ├── nhgis0001_ds224_YYYY_state.csv     # 1915-1941 state-level
│   ├── nhgis0001_ds224_YYYY_county.csv    # 1915-1941 county-level
│   ├── nhgis0001_ds229_YYYY_state.csv     # 1939-1959 state-level
│   ├── nhgis0001_ds229_YYYY_county.csv    # 1939-1959 county-level
│   ├── nhgis0001_ds230_YYYY_state.csv     # 1959-1972 state-level
│   ├── nhgis0001_ds230_YYYY_county.csv    # 1959-1972 county-level
│   ├── nhgis0001_ds231_YYYY_state.csv     # 1970-2007 state-level
│   └── nhgis0001_ds231_YYYY_county.csv    # 1970-2007 county-level
└── nhgis_datasets.json                    # Dataset metadata
```

### Key Column Names (from codebooks)

- **ds224 (1915-1941):** `AF1U001` = total births, `AF1V001` = White births, `AF1V002` = Nonwhite births
- **ds229 (1939-1959):** `AGVA001`/`AGVE001` = total (occurrence/residence), `AGVB001-002`/`AGVF001-002` = by race
- **ds230 (1959-1972):** `AGVT001`/`AGV1001` = total, `AGVU001-003`/`AGV2001-003` = White/Negro/Other
- **ds231 (1970-2007):** `AGWE001` = total births only (single data column)

### Geographic Columns

All files include: `GISJOIN`, `YEAR`, `STATE`, `STATEA`, `COUNTYA`, `AREANAME`
- ds231 also has: `STATEFP`, `COUNTYFP`, `DATAFLAG`, `NOTECODE`

### Row Counts (verified)

| Dataset | State rows/year | County rows/year | Notes |
|---------|----------------|-----------------|-------|
| ds224 (1940) | 51 | 3,109 | Birth Registration Area states only pre-1933 |
| ds229 (1950) | — | 3,112 | |
| ds230 (1965) | 51 | — | |
| ds231 (2000) | 51 | 3,143 | |

### Data Completeness — Race Fields

**ds224 county-level race data is incomplete.** In the 1940 county file, approximately **48% of rows (1,486 of 3,109) have empty race fields** (AF1V001/AF1V002). These are counties where the White/Nonwhite breakdown was not published in the original vital statistics volumes. State-level files appear complete.

This means county-level race breakdowns from NHGIS ds224 are available for roughly half of US counties in any given year. The NBER Historical dataset (which also has county-level data for 1946–1968) may fill some of these gaps.

## Script Usage

```bash
# Download all birth tables (submits API extract, waits, downloads)
python3 download_nhgis.py --download-all

# List datasets
python3 download_nhgis.py --list-datasets

# List tables in a dataset
python3 download_nhgis.py --list-tables 1970_2007_cVS

# Check/download existing extract
python3 download_nhgis.py --check 1
python3 download_nhgis.py --download 1
```

## Key Advantages

- **Best source for pre-1968 county-level birth data by race** (aggregated counts)
- Covers 1915–2007 at state and county level
- **Pre-aggregated** — no need to download and process multi-GB microdata files
- Geographically standardized tables available
- Well-documented with codebooks
- **Only source with race breakdown for 1940–1945** (NBER Historical has attendant type only for those years)

## Role in Our Pipeline

NHGIS is a primary source for **1940–2007** aggregate birth counts by race at state and county level. Together with CDC WONDER (1995–2024), it covers the full 1940–present range with pre-aggregated data.

Critical role: **NHGIS ds224/ds229 are the only available source for race (White/Nonwhite) breakdown during 1940–1945**, since NBER Historical files for those years only contain attendant-type breakdowns, not race.

## Download & Processing Learnings

### API & Access
- Requires a free IPUMS account (register at nhgis.org). API key goes in `.env` as `IPUMS_API_KEY`.
- NHGIS uses an **extract-based workflow**: you submit a request specifying datasets/tables/years/geographies, wait for the server to build it (usually 1-5 minutes), then download the result as a zip of CSVs.
- The IPUMS API (v2) is well-documented at `https://developer.ipums.org/docs/v2/apiprogram/apis/nhgis/`. Python requests work fine for submitting and polling extracts.
- Each extract gets a number (e.g., Extract #1). You can re-download past extracts without re-submitting.

### Dataset Selection Pitfall — ds231 Has No Race
- The most tempting dataset, **ds231 (1970-2007)**, appears to cover the most modern period. However, it contains **only total births** (`AGWE001`) — no race breakdown at all. This is the single biggest "gotcha" in the NHGIS vital statistics data.
- Race breakdowns are only available in the older datasets: ds224 (1915-1941), ds229 (1939-1959), and ds230 (1959-1972).
- This creates a **gap from 1973-1994** where no NHGIS dataset provides state-level race data.

### Column Naming
- NHGIS column names are opaque alphanumeric codes (e.g., `AF1V001`, `AGVB001`, `AGV2003`). You **must** use the codebook files (included in the extract) to decode them.
- Each extract includes `*_codebook.txt` files that map codes to human-readable labels.
- Geographic columns are consistent across datasets: `GISJOIN`, `YEAR`, `STATE`, `STATEA`, `COUNTYA`, `AREANAME`.

### Occurrence vs Residence
- ds229 and ds230 have **two sets of tables**: place of occurrence and place of residence. For our purposes (where do mothers live?), use the **residence** tables:
  - ds229: `NT005`/`NT006` (residence) not `NT001`/`NT002` (occurrence)
  - ds230: `NT009`/`NT010` (residence) not `NT001`/`NT002` (occurrence)
- Place of residence data is only available from 1942 onward. Pre-1942 data is place of occurrence only.

### County Race Completeness
- ds224 county-level race data is only ~52% complete. In 1940, 1,486 out of 3,109 county rows have empty race fields (`AF1V001`/`AF1V002`). These are counties where the original vital statistics volumes did not publish a White/Nonwhite breakdown.
- State-level files are complete for all datasets.

### ds231 Year Gaps
- ds231 years are NOT contiguous: 1970, 1975, 1980, 1985, then 1990-2007 annually. The 5-year gaps (1971-1974, 1976-1979, 1981-1984, 1986-1989) have no data.

## Limitations

- Race categories vary by period: White/Nonwhite only before 1959; White/Negro/Other for 1959-1972
- **1970-2007 dataset has NO race breakdown** — total births only
- **County-level race data ~48% incomplete in ds224** (many counties lack White/Nonwhite split)
- Hispanic origin breakdowns not available from NHGIS vital statistics tables
- Some tables are birth registration area only (not all states before 1933)
- Place of residence data only available from 1942+ (earlier years = place of occurrence)
- ds231 years are not continuous: 1970, 1975, 1980, 1985, then 1990–2007 annually

---

## Extraction (2026-04-09)

Data extracted to `extracted_data.csv` by `data/extract_all_data.py`.

| Dataset | Rows Extracted | Years | Has White Births? |
|---------|---------------|-------|-------------------|
| ds224 | 100 | 1940–1941 | Yes (98/100 — Alaska Territory has no data) |
| ds229 | 1,002 | 1940–1959 | Yes (1,001/1,002) |
| ds230 | 713 | 1959–1972 | Yes (711/713) |
| ds231 | 1,122 | 1970–2007 | No — total births only |
| **Total** | **2,937** | **1940–2007** | |

### Extraction Notes

- **ds229 residence vs occurrence:** For 1940-1941, residence totals exist but residence race fields are empty. Script uses residence totals combined with occurrence-based race data for those years. From 1942 onward, residence-based race data is available.
- **ds230 residence preferred:** Residence-based columns (AGV1001, AGV2001-003) used where available; occurrence (AGVT001, AGVU001-003) as fallback.
- **ds231 5-year gaps:** Years 1970, 1975, 1980, 1985, 1990-2007 only. Missing: 1971-74, 1976-79, 1981-84, 1986-89.
- **State names normalized:** "DIST OF COLUMBIA" → "District of Columbia", territory names mapped to modern state names.
- **No White NH possible:** NHGIS vital statistics tables have no Hispanic origin breakdown. All "White" counts include Hispanic whites.

---

*Last updated: 2026-04-09 (extraction complete; 2,937 rows across 4 datasets)*
