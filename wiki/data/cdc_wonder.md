# CDC WONDER Natality

**Source URL:** https://wonder.cdc.gov/natality.html

**Script:** `download_cdc_wonder.py` (API, national-level only)

---

## Status: ✅ DOWNLOADED (3 databases + D66 Bridged Race)

| Field | Value |
|-------|-------|
| Claimed years | 1995–2024 |
| Actual years obtained | **1995–2024** (30 years across 3 databases + bridged race) |
| Geographic level | State (downloaded via Playwright browser automation) |
| Race/ethnicity | Yes (1995+) — White NH clearly available |
| Total data rows | **33,302** (D66: 15,290 + D27: 3,842 + D10: 14,170) |
| Method | Playwright browser automation (headless) — submits form, scrapes results table from HTML |
| Columns | Year, State, Race, Hispanic Origin, Births (tab-separated) |
| Suppression | Cells <10 births suppressed; some rows with zero or suppressed births hidden by default |

## Databases

| ID | Name | Years | URL |
|----|------|-------|-----|
| D10 | Natality 1995-2002 | 1995–2002 | https://wonder.cdc.gov/natality-v2002.html |
| D27 | Natality 2003-2006 | 2003–2006 | https://wonder.cdc.gov/natality-v2006.html |
| D66 | Natality 2007-2024 | 2007–2024 | https://wonder.cdc.gov/natality-current.html |
| D149 | Natality 2016-2024 (Expanded) | 2016–2024 | https://wonder.cdc.gov/natality-expanded-current.html |

## API Limitations (Critical)

The CDC WONDER API **does not support sub-national queries** for vital statistics data:
> "Queries for mortality and births statistics from the National Vital Statistics System
> cannot limit or group results by any location field, such as Region, Division, State
> or County, or Urbanization."

This means:
- API gives **national totals only** (same data available from NBER microdata)
- State/county data requires the **web interface** (manual or Selenium)
- The API script (`download_cdc_wonder.py`) attempts national queries but needs correct variable codes per database

## API Request Format

- POST to `https://wonder.cdc.gov/controller/datarequest/{database_id}`
- Body: `request_xml=<XML document>` + `accept_datause_restrictions=true`
- XML uses `<parameter><name>...</name><value>...</value></parameter>` structure
- Rate limit: 1 query per 2 minutes recommended
- Request XML templates saved in `raw-data/request_D66.xml` etc.

## Manual Web UI Download (Recommended for State/County Data)

1. Visit https://wonder.cdc.gov/natality-current.html
2. Agree to data use restrictions
3. Under "Group Results By":
   - Section 1: Year
   - Section 2: State
   - Section 3: Mother's Single Race 6 (or Bridged Race)
   - Section 4: Mother's Hispanic Origin
4. Under "Select Year": Choose all available years
5. Click "Send" to get results
6. Click "Export" to download tab-delimited text
7. Save to `data/cdc_wonder/raw-data/`

Repeat for county-level (expect heavy suppression for small counties).

## Role in Our Pipeline

CDC WONDER is the **only source for state/county-level births by race/ethnicity for 2005–2024** (NBER/NCHS microdata lost geographic identifiers starting 2005). It also overlaps with NHGIS for 1995–2007, providing a validation/gap-filling option.

Our goal is narrow: **aggregate birth counts by year × state × race (White NH), 1940–present**. CDC WONDER returns exactly this — pre-aggregated counts grouped by year, state, and race/ethnicity. No bulk microdata download needed.

**Coverage plan:**
- **1995–2024** at state level (primary source for 2008–2024; overlap with NHGIS for 1995–2007)
- **County level** also available but heavily suppressed for small counties

## Playwright Browser Automation Script

A Playwright-based download script is available at `download_cdc_wonder_browser.py`:

```bash
pip install playwright
playwright install chromium
python3 download_cdc_wonder_browser.py
```

This script:
1. Navigates to each CDC WONDER natality database (D66, D27, D10)
2. Accepts data use restrictions
3. Configures query: Group by Year × State × Race × Hispanic Origin
4. Selects all years, enables TSV export
5. Submits query and downloads the results file
6. Has retry logic for server errors (500/429)

### Query Configuration Per Database

| Database | Race Group-By | Hispanic Group-By | Output File |
|----------|--------------|-------------------|-------------|
| D66 (2007-2024) | Mother's Single Race 6 | Mother's Hispanic Origin (D66.V43) | `cdc_wonder_D66_state_race_hisp.txt` |
| D27 (2003-2006) | Mother's Bridged Race | Hispanic Origin | `cdc_wonder_D27_state_race_hisp.txt` |
| D10 (1995-2002) | Race 8 | Hispanic Origin | `cdc_wonder_D10_state_race_hisp.txt` |

### Server Issues (Resolved)

The CDC WONDER servers were returning 500/429 errors earlier on 2026-04-09 but recovered. The Playwright script's retry logic handled the intermittent failures, and all 3 databases were successfully downloaded.

## Scraping Learnings

Comprehensive technical notes from building and debugging the Playwright-based CDC WONDER scraper:

### API vs Web UI
- The CDC WONDER API (`POST /controller/datarequest/{db_id}`) is **strictly national-only** for natality data. Any attempt to group by State or County via the API returns error messages. This is documented but the error messages are misleading — they mention State/County as valid group-by values in other contexts.
- The API endpoint returns XML (not JSON). Errors come back as `<page><message>...</message></page>`.
- The **web UI** does support state/county queries. Browser automation is the only programmatic path to sub-national data.
- `data.cdc.gov` (the Socrata/SODA open data portal) has some natality datasets but **none with both state-level and race breakdown**. Dataset `89yk-m38d` has race but is national-only; `hmz2-vwda` has states but no race.

### Form Field Codes (Critical Reference)
Each database has different variable codes for the Group By dropdowns. These must be set by **value**, not by label:

| Field | D66 (2007-2024) | D27 (2003-2006) | D10 (1995-2002) |
|-------|-----------------|-----------------|-----------------|
| Year | `D66.V20` | `D27.V20` | `D10.V20` |
| State | `D66.V21-level1` | `D27.V21-level1` | `D10.V21-level1` |
| Race | `D66.V42` (Single Race) | `D27.V2` (Bridged Race) | `D10.V2` (Race) |
| Hispanic Origin | `D66.V43` | `D27.V43` | `D10.V4` |

The dropdown labels vary across databases (e.g., "Mother's Single Race" vs "Mother's Bridged Race" vs "Mother's Race"), so matching by label is fragile. Always use `value=`.

### Year Filter Gotcha
- D66 defaults to **only the most recent year** (2024). You must explicitly select `*All*` in the year filter dropdown (`V_D66.V20`). Otherwise you get one year of data out of 18.
- D27 and D10 default to all years already — no action needed.
- To select all years, find `select[name='V_{db}.V20']` and set the `*All*` option via JavaScript, then dispatch a `change` event.

### Playwright-Specific Issues
- **`wait_until="networkidle"` causes hangs.** The CDC website loads analytics/tracking scripts that keep the network active indefinitely. Use `wait_until="domcontentloaded"` instead.
- **Form submission causes a full page navigation** (POST form submit, not AJAX). After clicking `input#submit-button1`, use `page.click(..., timeout=600000)` to wait for the navigation to complete. The default 30s timeout is too short for D10.
- **`expect_navigation()` wrapper can also work** but the default click timeout still applies.
- **Export button unreliable:** The Export button on the results page exists but `input[value='Export']` doesn't reliably find it in headless mode. **Table scraping is more reliable** than trying to trigger a file download.

### Table Scraping
- Use `cell.innerText.trim()` not `cell.textContent.trim()`. `textContent` concatenates all descendant text without whitespace, producing `"2024Alabama (01)White..."`. `innerText` respects rendered layout and returns clean cell values.
- Find the data table by selecting the `<table>` with the most `<tr>` rows (> 50), since the page has multiple small tables for navigation/layout.
- Results include some header/metadata rows — data rows can be identified by starting with a 4-digit year.
- Suppressed and zero-count rows are hidden by default. Check "Show zero rows" and "Show suppressed rows" in Quick Options for complete data.

### Rate Limits
- Wait **120 seconds** between database queries. Shorter waits risk 429 (Too Many Requests) errors.
- The server occasionally returns 500 errors even with proper waits. Retry logic with 30-60s backoff handles these.

## Limitations

- API returns national data only — state/county requires web UI or Playwright automation
- Web UI/Playwright downloads one database at a time
- County-level data heavily suppressed for small populations (<10 births hidden)
- Server may be unreliable (500/429 errors observed 2026-04-09 but recovered)
- Some rows with zero or suppressed births hidden by default in results

---

## Downloaded Files

### Birth Data (Playwright browser automation)

| File | Database | Years | Data Rows | Race Field |
|------|----------|-------|-----------|------------|
| `cdc_wonder_D66_state_race_hisp.txt` | D66 (Natality 2007–2024) | 2007–2024 (18 years) | 15,290 | Single Race (2016-2024 only) |
| `cdc_wonder_D66_bridged_state_race_hisp.txt` | D66 (Natality 2007–2024) | 2007–2024 (18 years) | 27,540 | **Bridged Race (all years)** |
| `cdc_wonder_D27_state_race_hisp.txt` | D27 (Natality 2003–2006) | 2003–2006 (4 years) | 3,842 | Bridged Race |
| `cdc_wonder_D10_state_race_hisp.txt` | D10 (Natality 1995–2002) | 1995–2002 (8 years) | 14,170 | Race 8 |

All files are tab-separated with columns: Year, State, Race, Hispanic Origin, Births.

### API Request Templates (reference)

- `request_D10.xml` — XML for the 1995–2002 database
- `request_D27.xml` — XML for the 2003–2006 database
- `request_D66.xml` — XML for the 2007–2024 database

---

## Extraction (2026-04-10)

Data extracted to `extracted_data.csv` by `data/extract_all_data.py`.

| Database | Rows | Years | White NH Available? |
|----------|------|-------|---------------------|
| D10 (1995-2002) | 408 | 1995–2002 | **Yes** — Race:White + Hispanic:Non-Hispanic White |
| D27 (2003-2006) | 204 | 2003–2006 | **Yes** — Race:White + Hispanic:Not Hispanic or Latino |
| D66 Single Race (2007-2024) | 918 | 2007–2024 | **Partial:** 2016-2024 yes, 2007-2015 no (race="Not Available") |
| D66 Bridged Race (2007-2024) | 918 | 2007–2024 | **Yes — all years** via Bridged Race |
| **Total** | **2,448** | **1995–2024** | |

### Extraction Notes

- **D10 Hispanic categories are granular:** Mexican, Puerto Rican, Cuban, Central or South American, Other and Unknown Hispanic, Non-Hispanic White, Non-Hispanic Black, Non-Hispanic other races. White NH = `race=="White" AND hispanic=="Non-Hispanic White"`.
- **D27 Hispanic categories are simpler:** Hispanic or Latino, Not Hispanic or Latino, Unknown or Not Stated. White NH = `race=="White" AND hispanic=="Not Hispanic or Latino"`.
- **D66 two-phase data:**
  - 2007-2015: `Mother's Single Race` = "Not Available" for all rows. Only Hispanic/Not Hispanic breakdown exists. No White NH can be computed. Total births available from sum.
  - 2016-2024: Full Race × Hispanic cross-tabulation. White NH = `race=="White" AND hispanic=="Not Hispanic or Latino"`.
- **D66 file had duplicate sections** (possibly two query results concatenated). Deduplication applied on `(year, state, race, hispanic)`.
- **Suppressed cells:** Rows with <10 births suppressed by CDC WONDER. Some small-state race/ethnicity combinations have `Suppressed` values parsed as NaN.
- **Total births computed** as sum of all race × Hispanic combinations per year × state (not directly provided as a column).

### The 2007-2015 Race Gap — RESOLVED (2026-04-10)

The "Not Available" race field for 2007-2015 in D66 was because the "Mother's Single Race" variable was introduced with the 2003 Standard Certificate revision, but not all states adopted it until 2016.

**Fix:** Re-queried D66 with "Mother's Bridged Race" (`D66.V2`) instead of "Mother's Single Race" (`D66.V42`) in the Group By settings. This returned 27,540 raw data rows covering all 18 years (2007-2024) with proper race categories: White, Black or African American, American Indian or Alaska Native, Asian or Pacific Islander, Not Reported.

The bridged-race data file is at `raw-data/cdc_wonder_D66_bridged_state_race_hisp.txt`.

| File | Rows | Years | Race Available? |
|------|------|-------|----------------|
| D66 Single Race | 15,290 | 2007-2024 | 2016-2024 only |
| **D66 Bridged Race** | **27,540** | **2007-2024** | **All years** |

### Cross-Validation with KFF (2016-2023)

CDC WONDER White NH births exactly match KFF "White" births for all checked states in 2016-2023, confirming both sources derive from the same NCHS data and that KFF "White" = White Non-Hispanic.

---

*Last updated: 2026-04-10 (bridged race re-query complete; 2,448 extracted rows; 2007-2015 race gap resolved)*
