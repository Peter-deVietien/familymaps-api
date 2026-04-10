# NBER Vital Statistics Natality Microdata (1968–2024)

**Source URL:** https://www.nber.org/research/data/vital-statistics-natality-birth-data

**Script:** `download_nber_microdata.py`

---

## Status: ✅ DOWNLOADED — 1,122 rows for 1973-1994 (WNH fix complete)

| Field | Value |
|-------|-------|
| Claimed years | 1968–2024 (CSV directory confirmed) |
| File format | CSV (also Stata .dta, SAS .sas7bdat) |
| File sizes | **Hundreds of MB to 2.4 GB each** |
| Geographic detail (1968–2004) | State + County (FIPS from 1981+) |
| Geographic detail (2005–2024) | **NONE** — national level only |
| Total download size | **~25-30 GB** for 1973-1994 (streamed, not stored) |
| Processed output | 1,122 rows (51 states × 22 years) |

## Role in Pipeline

This is the **only viable source** for state-level birth data by race for 1973-1994. All pre-aggregated alternatives were exhaustively investigated and ruled out (2026-04-09):
- NHGIS ds231 (1970-2007) has total births only — no race
- CDC WONDER starts at 1995
- Mendeley/Galofré-Vilà dataset has TFR only, no raw birth counts
- CDC data.cdc.gov has race data only at national level, not state
- NCHS Vital Stats volumes exist as PDFs only — impractical for 22 years

## Download Approach

Stream-download one year at a time, aggregate by state×race in memory, output counts, don't store the raw file. Each year is 474 MB (1973) to ~2 GB (1990).

**Script:** `data/nber_microdata/download_nber_microdata.py`

```bash
python3 download_nber_microdata.py              # all years 1973-1994
python3 download_nber_microdata.py 1989 1990     # specific years
```

The script has resume logic: existing years in `extracted_data.csv` are preserved when re-running specific years.

## Column Schema by Era

### 1973–1979 (129 columns per file)
- **State:** `stateres` — NCHS alphabetical codes (1=Alabama, 2=Alaska, ..., 51=Wyoming)
- **Race:** `crace` — child's race (1=White, 2=Black/Negro, etc.)
- **Hispanic:** `origm` — Hispanic origin (0=Non-Hispanic, 1=Mexican, 2=Puerto Rican, ..., 5=Other Hispanic, 99=Unknown)
  - 1973-1977: `origm` not available
  - 1978-1979: `origm` available but only ~4-6 states report reliably
- **Weight:** `recwt` — 1 for all years 1973+ (50% samples only for 1968-1971)

### 1980–1988 (129 columns per file)
- **State:** `stateres` — NCHS alphabetical codes
- **Race:** `mrace` — mother's race (replaces `crace`)
- **Hispanic:** `origm` — (0=Non-Hispanic, 1-5=Hispanic, 99=Unknown)
  - Partial states: 8-16 states report reliably (growing over time)

### 1989–1994 (205 columns per file) — CRITICAL SCHEMA CHANGE
- **State:** `stresfip` — FIPS codes (01=Alabama, etc.)
- **Race:** `mrace` — mother's race
- **Hispanic:** **`ormoth`** — NOT `origm`!
  - `ormoth`: 0=Non-Hispanic, 1=Mexican, 2=Puerto Rican, 3=Cuban, 4=Central/South American, 5=Other Hispanic, 9=Unknown
  - `origm`: Changed to a binary flag (0/1) in 1989+ files — **DO NOT USE for Hispanic origin**

### Key Bug Fix (2026-04-10)

The original script used `origm` for all years. In 1989+ files, `origm` was recoded to a binary flag (value=1 for ~99.8% of rows), causing all White Non-Hispanic counts to be 0 for 1989-1994. Fixed by using `ormoth` for 1989+ files:

```python
hisp_field = 'ormoth' if use_fips else 'origm'
origm_val = safe_int(row.get(hisp_field), default=99)
```

Re-run of 1989-1994 completed (2026-04-10, 2.3 hours). Results: 1989=48/51, 1990=49/51, 1991-92=50/51, 1993-94=51/51 states with WNH.

## White NH Coverage by Year

| Years | States with WNH | Notes |
|-------|----------------|-------|
| 1973-1977 | 0/51 | `origm` not available |
| 1978 | 4/51 | First year with partial Hispanic origin |
| 1979 | 6/51 | |
| 1980-1981 | 8/51 | |
| 1982 | 10/51 | |
| 1983 | 11/51 | |
| 1984-1987 | 10/51 | |
| 1988 | 16/51 | |
| 1989 | 48/51 | `ormoth` fix applied; 3 states excluded (>30% unknown Hispanic) |
| 1990 | 49/51 | |
| 1991-1992 | 50/51 | |
| 1993-1994 | 51/51 | All states report Hispanic origin from 1993 |

States are excluded from WNH if >30% of white births have unknown Hispanic origin.

## File Sizes by Year (verified 2026-04-09)

| Year | CSV Size | Notes |
|------|----------|-------|
| 1973 | 474 MB | `crace` only, no Hispanic origin |
| 1975 | 580 MB | |
| 1978 | 810 MB | `origm` appears (partial states) |
| 1980 | 965 MB | `mrace` replaces `crace` |
| 1985 | 1,243 MB | |
| 1989 | 1,929 MB | `stresfip` + `ormoth` (205 cols, bigger rows) |
| 1990 | 1,996 MB | |
| 1994 | 1,896 MB | `ormoth` in all states by 1993 |

## Learnings

- CSV files are at `https://data.nber.org/nvss/natality/csv/{year}/`. Each year has two files: `natality{YYYY}us.csv` (US records) and `natality{YYYY}ps.csv` (territory records).
- **Column count changes at 1989:** Pre-1989 files have ~129 columns; 1989+ files have ~205 columns (many more clinical/medical fields). This makes 1989+ rows larger and slower to parse.
- **Processing speed:** Pre-1989 files process at ~5,000-6,500 rows/s. 1989+ files are slower (~1,000-3,500 rows/s) due to the larger row size.
- **NCHS alpha codes (pre-1989):** States numbered 1-51 alphabetically (DC between Delaware and Florida). Map: 1=Alabama, 2=Alaska, 3=Arizona, ..., 9=District of Columbia, ..., 51=Wyoming. Codes 52+ are territories (excluded).
- **FIPS codes (1989+):** Standard 2-digit FIPS (01=Alabama, 02=Alaska, ..., 56=Wyoming).
- **Hispanic origin field change at 1989:** `origm` pre-1989 = detailed coding (0=Non-Hisp, 1-5=Hisp, 99=Unknown). `origm` post-1989 = binary flag (useless). Use `ormoth` for post-1989 (same detailed coding as pre-1989 `origm`).
- The `ormoth` column does NOT exist in pre-1989 files.
- **1968-1971 are 50% samples** — each record represents 2 births (`recwt=2`). Not relevant for our 1973-1994 range.
- **2005+ files lack geographic identifiers** — `stateres` and `cntyres` are missing. National-level aggregation only.
- Total download was ~25-30 GB streamed over ~5 hours. No raw files stored on disk — only the 1,122-row aggregate output.

## Reference Info

- CSV URLs: `https://data.nber.org/nvss/natality/csv/{year}/natality{year}us.csv`
- Geographic detail available 1968–2004 only; 2005+ is national-only
- Hispanic origin available 1978+ (partial), 1993+ (all states)
- Pre-1989: `origm` for Hispanic, `stateres` for state (NCHS alpha)
- 1989+: `ormoth` for Hispanic, `stresfip` for state (FIPS)
- County FIPS codes consistent from 1981+; pre-1981 uses NCHS codes

---

*Last updated: 2026-04-10 (all downloads complete; origm→ormoth bug fix for 1989-1994 done; 402/1122 rows have WNH)*
