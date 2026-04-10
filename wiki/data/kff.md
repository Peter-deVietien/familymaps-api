# KFF State Health Facts — Births by Race/Ethnicity

**Source URL:** https://www.kff.org/other/state-indicator/births-by-raceethnicity/

**Script:** `download_kff.py`

---

## Status: ✅ DOWNLOADED

| Field | Value |
|-------|-------|
| Claimed years | ~2000–2023 |
| Actual years available on site | **2016–2023** (8 years — timeframe dropdown only goes back to 2016) |
| Actual years obtained | **2016–2023** (all 8 years, validated distinct) |
| Geographic level | State only (50 states + DC + US total = 52 rows/year) |
| Total rows in file | 416 (52 locations × 8 years — all valid and distinct) |
| Race categories | White, Black, Hispanic, Asian, AIAN, NHPI, More than one race |
| Has "Total" births column | Column exists but is empty (can be computed as sum of race categories) |
| White NH vs White | Likely **White non-Hispanic** — Hispanic is a separate column (see Race Category Interpretation) |
| Output file | `raw-data/kff_births_by_race_ethnicity.csv` |

## Data Quality — Validated

The scraper bug that previously caused all 8 years to contain identical data has been **fixed and re-run**. All 8 years now have distinct values. US White births by year:

| Year | US White Births |
|------|----------------|
| 2016 | 2,056,332 |
| 2017 | 1,992,461 |
| 2018 | 1,956,413 |
| 2019 | 1,915,912 |
| 2020 | 1,843,432 |
| 2021 | 1,887,656 |
| 2022 | 1,840,739 |
| 2023 | 1,787,051 |

Values decline year-over-year as expected (except a small uptick in 2021), confirming each year is distinct data.

## Technical Notes

- KFF uses an AngularJS app with **ag-Grid** for the data table. No public API.
- The Selenium scraper extracts data from ag-Grid DOM (`<span title="...">` attributes).
- The timeframe dropdown only goes back to 2016 (8 years available, not the ~2000 originally expected).
- Some cells contain "N/A" for small populations (e.g., Wyoming NHPI, several small states).
- KFF sources this data from NCHS/CDC — it's a secondary/aggregated source.

## Race Category Interpretation

KFF's notes state:
> "Data reflect race and Hispanic origin of the infant's mother. Race and Hispanic origin are
> reported separately on birth certificates; persons of Hispanic origin may be of any race."

Since Hispanic is listed as a separate column and the footnote says persons of Hispanic origin may be of any race, the "White" column likely represents **White non-Hispanic** (with Hispanic whites counted in the Hispanic column instead). This should be validated against CDC WONDER data once available.

## CSV File Structure

```
Columns: Year, Location, White, Black, Hispanic, Asian, American Indian or Alaska Native,
         Native Hawaiian or Pacific Islander, More than one race, Total
Rows: 416 (52 locations × 8 years — all years validated distinct)
```

Notable:
- "Total" column is always empty (not populated by KFF)
- "N/A" appears for small populations in some states (e.g., CT/DE/DC/ME/MT/NH/RI/VT/WV/WY for NHPI)
- Values use comma-formatted numbers (e.g., "1,787,051")

## Role in Our Pipeline

KFF serves as a **validation and cross-reference source** for recent years (2016–2023). Since CDC WONDER and NHGIS cover the same period with broader year ranges, KFF is not a primary data source but useful for sanity-checking aggregate state-level totals.

Now validated and usable for cross-referencing CDC WONDER data for 2016–2023.

## Scraping Learnings

Hard-won technical details from building and debugging the KFF scraper:

### Architecture
- KFF uses an **AngularJS single-page app** with **ag-Grid** for rendering data tables. There is no public API, no standard HTML `<table>`, and no static page per year.
- Data cells live inside `<span title="...">` attributes within ag-Grid's custom DOM structure.
- The "Location" column is in a **pinned left container** (`div.ag-pinned-left-cols-container`), separate from the data columns (`div.ag-body-viewport`). You must link them by the `row` attribute on `<div class="ag-row">` elements.

### Timeframe Switching — The Key Pitfall
- The timeframe `<select>` dropdown has values like `string:0`, `string:1`, etc. (not year numbers).
- **URL parameter approach does NOT work:** Navigating to `?currentTimeframe=N` does NOT update the AngularJS app's internal state. The page loads with the default timeframe regardless of URL params. This was the original scraper bug — all 8 years returned identical data.
- **Correct approach:** Stay on the same page, set the `<select>` value via JavaScript, and dispatch a `change` event (`new Event('change', {bubbles: true})`). This triggers AngularJS's digest cycle and refreshes the ag-Grid.
- After dispatching the change event, **wait for the data to actually refresh** by polling for a visible data value to change (compare the first cell's content before and after). Naive fixed-delay waits are unreliable.

### Validation
- Always validate that different years produce different data — check a known value (e.g., US White births) across all years. A declining trend (2,056,332 → 1,787,051 for 2016→2023) confirms distinct data.
- "N/A" values appear for small populations in some states — these are legitimate, not errors.

## Limitations

- Only 8 years of data (2016–2023), not the ~24 years initially expected
- State-level only — no county data
- Secondary source (aggregated from NCHS)
- "Total" births not directly provided (but computable from race breakdown)
- Secondary source — use for validation, not as primary

---

## Extraction (2026-04-09)

Data extracted to `extracted_data.csv` by `data/extract_all_data.py`.

| Field | Value |
|-------|-------|
| Rows extracted | 408 (51 states × 8 years) |
| Years | 2016–2023 |
| White NH confirmed | **Yes** — exact match with CDC WONDER White NH for all checked states |

### Extraction Notes

- "Total" column in raw data is always empty. Total computed as sum of all race columns (White + Black + Hispanic + Asian + AIAN + NHPI + More than one race).
- Numbers with commas parsed to integers. "N/A" values preserved as NaN.
- `white_nh_births` set equal to `white_births` based on cross-validation confirming KFF "White" = White Non-Hispanic.
- "United States" total row excluded (only 50 states + DC kept).

### Cross-Validation Results

KFF "White" births exactly match CDC WONDER D66 "White + Not Hispanic or Latino" for every state checked:
- Alabama 2020: KFF = 32,672, CDC = 32,672 ✓
- California 2020: KFF = 115,543, CDC = 115,543 ✓
- Texas 2020: KFF = 120,329, CDC = 120,329 ✓
- New York 2020: KFF = 104,581, CDC = 104,581 ✓

This confirms KFF "White" = White Non-Hispanic (not White including Hispanic).

---

*Last updated: 2026-04-09 (extraction complete; White NH confirmed via CDC WONDER cross-validation)*
