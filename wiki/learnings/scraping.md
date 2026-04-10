# Scraping & Download Patterns

> Cross-source lessons learned from building scrapers and downloading data. Read this before building or debugging any scraper.

## General Principles

1. **Table scraping > export buttons** in headless browsers. Export buttons are unreliable; scraping the rendered HTML table is more robust.
2. **Always validate across years/pages.** A scraper that returns plausible-looking data for one query may silently return the same data for all queries (KFF bug).
3. **Retry with backoff.** Government data servers (CDC, Census) regularly return 500/429 errors. Build retry logic with 30-120s backoff.
4. **Use `innerText` not `textContent`** for table cells — `textContent` concatenates all descendants without whitespace.

## CDC WONDER — Playwright

- **API is national-only** for natality. State/county requires browser automation.
- Use `wait_until="domcontentloaded"` — `networkidle` hangs due to analytics scripts.
- Form submission causes full page navigation — set click timeout to 600s+.
- Each database has different variable codes for Group By dropdowns. Match by `value=`, not label.
- D66 defaults to only the most recent year — must explicitly select `*All*` in year filter.
- Wait **120 seconds** between database queries to avoid 429 errors.
- Check "Show zero rows" and "Show suppressed rows" in Quick Options for complete data.
- Find data table by selecting `<table>` with most `<tr>` rows (>50).
- **D66 "Single Race" has no data for 2007-2015.** Use "Bridged Race" (D66.V2) instead of "Single Race" (D66.V42).

## KFF — Selenium

- KFF uses **AngularJS + ag-Grid**. No public API, no standard HTML tables.
- Data cells in `<span title="...">` attributes. Location column in pinned left container, data in body viewport. Link by `row` attribute.
- **URL params don't work** for switching timeframes. Must set `<select>` value via JS and dispatch `change` event to trigger AngularJS digest cycle.
- After dispatch, **poll for data change** — don't use fixed delays.
- Timeframe dropdown values are `string:0`, `string:1`, etc. — not year numbers.

## NHGIS/IPUMS — API

- Extract-based workflow: submit request → poll → download zip of CSVs.
- API well-documented at `developer.ipums.org/docs/v2/apiprogram/apis/nhgis/`.
- API key in `.env` as `IPUMS_API_KEY`.

## NBER Microdata — Streaming HTTP

- Files are 474 MB to 2+ GB each. Stream-download and aggregate in memory; don't store raw files.
- CSV URLs: `https://data.nber.org/nvss/natality/csv/{year}/natality{year}us.csv`
- Column count jumps from ~129 to ~205 at 1989 (slower parsing).

## data.cdc.gov (Socrata/SODA)

- **Not a substitute for CDC WONDER.** No dataset combines state-level geography with race breakdown.
- `89yk-m38d` has race but national-only; `hmz2-vwda` has states but no race.

---

*Update when new scraping patterns are discovered or existing scrapers are modified.*
