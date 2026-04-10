# NCHS Vital Statistics Online (Public-Use Microdata)

**Source URL:** https://www.cdc.gov/nchs/data_access/vitalstatsonline.htm

**Script:** `download_nchs.py`

---

## Status: ⏸️ DEPRIORITIZED — Docs downloaded, microdata not needed

| Field | Value |
|-------|-------|
| Claimed years | 1968–2024 |
| File format | Flat files (.dat) in .zip archives |
| Geographic detail (1968–2004) | State, County (FIPS), City, MSA |
| Geographic detail (2005–2024) | **NONE** — national level only |
| User guides downloaded | 2023, 2024 |

## Why We're Not Using This

Like NBER microdata, these are **individual birth record files** (one row per birth, 15–230 MB per year). Our goal is narrow:

> **Aggregate birth counts by year × state/county × race, 1940–present**

Pre-aggregated sources (NHGIS, CDC WONDER, KFF) provide the same aggregate totals without downloading and processing multi-GB flat files. This source is also the same underlying data as NBER microdata, just in a less convenient format.

## Role in Our Pipeline

- **Reference only** — user guides downloaded for field documentation
- Fallback if NHGIS/CDC WONDER have gaps for specific years

## Learnings

- These are the same underlying birth records as NBER Microdata, but distributed as **fixed-width `.dat` files** in `.zip` archives — significantly harder to parse than NBER's CSV format.
- The record layout changes between years. The user guide PDFs (2023, 2024) document field positions, lengths, and codes for their respective years.
- **2005+ files have NO geographic identifiers** (state, county, city, MSA all removed). National-level aggregation is the only option for recent years from this source.
- For 1968-2004, state FIPS codes and county codes are available, making sub-national analysis possible.
- Given that NBER provides the same data in CSV format and CDC WONDER provides pre-aggregated counts, there is no practical reason to use NCHS files directly unless both other sources are unavailable.

## Downloaded Files

- `raw-data/docs/UserGuide2023.pdf` (1.7 MB)
- `raw-data/docs/UserGuide2024.pdf` (2.8 MB)

---

*Last updated: 2026-04-09 (learnings about format and limitations added)*
