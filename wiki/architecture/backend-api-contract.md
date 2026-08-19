# API Contract

> Endpoint shapes and data formats. Read when changing how frontend and backend communicate.

## Base URL

`https://api.wdwwa.com`

## Geography Endpoints

All geo endpoints return **TopoJSON** objects.

```
GET /api/geo/us_counties     → US county boundaries
GET /api/geo/fl_counties     → FL county boundaries
GET /api/geo/fl_tracts       → FL census tract boundaries
GET /api/geo/fl_block_groups → FL block group boundaries
```

## Demographics Endpoints

All demographics endpoints return **JSON** arrays/objects.

```
GET /api/demographics/us_counties            → county-level demographics
GET /api/demographics/us_counties_under5     → county under-5 demographics
GET /api/demographics/us_counties_percentages → WDWWA factor percentages + climate
GET /api/demographics/us_counties_obesity    → county adult obesity prevalence
GET /api/demographics/fl_counties            → FL county demographics
GET /api/demographics/fl_tracts              → FL tract demographics
GET /api/demographics/fl_block_groups        → FL block group demographics
```

### Race composition shape

`us_counties`, `fl_counties`, `fl_tracts` and `fl_block_groups` share one schema, all from ACS 5-year 2023 table **B03002**:

```
GEOID, name, total_pop, white_non_hisp, black_non_hisp,
native_am_non_hisp, asian_non_hisp, nhpi_non_hisp, hisp_any_race, white_hisp
```

`nhpi_non_hisp` (`B03002_007E`, Native Hawaiian / Other Pacific Islander alone non-Hispanic) was added 2026-08-15 to back the frontend's White + Asian toggle.

### WDWWA percentages shape

```
GEOID, name, total_pop, female_pct, median_age, white_pct, trump_pct, pleasant_days
```

`pleasant_days` (added 2026-08-19) is the average number of days per year with a high of 60–85°F, a low of 40–68°F and no measurable rain, from 30 years of NOAA nClimGrid-Daily county averages. **CONUS only** — `null` for Alaska, Hawaii and Puerto Rico (113 of 3,222 records). The frontend's rank algorithm already drops any county with a null field, so nulls need no special handling. See [../data/nclimgrid.md](../data/nclimgrid.md).

Regenerate with `python3 scripts/add_pleasant_days_field.py`.

### Obesity shape

```
GEOID, name, total_pop, obesity_pct, obesity_pct_age_adj, ci_low, ci_high, brfss_year
```

Added 2026-08-19 from CDC PLACES. `obesity_pct` is the crude share of adults 18+ with BMI ≥ 30; `obesity_pct_age_adj` is the same figure reweighted to a standard age distribution. **Neither is age-specific** — both cover all adults, and age-adjustment only neutralises the county's age composition. `ci_low`/`ci_high` are the 95% interval on the crude rate, which is wide for small counties because the values are modelled rather than measured.

`brfss_year` is per-county (2023 or 2022) because the 2025 PLACES release omits Kentucky and Pennsylvania entirely and those 187 counties fall back to the 2024 release. **Null for all 78 Puerto Rico municipios** (3,144 of 3,222 populated) — PLACES covers 50 states + DC only.

Kept as a standalone file rather than a `us_counties_percentages` field. The frontend joins crude `obesity_pct` onto the rank input itself (same pattern as `black_pct`) and also paints it as its own layer. See [../data/cdc_places.md](../data/cdc_places.md).

Regenerate with `python3 scripts/download_cdc_places_obesity.py && python3 scripts/build_obesity_dataset.py`.

### Under-5 shape

```
GEOID, name, total_pop, total_male_under5, total_female_under5,
white_nh_total, white_nh_male_under5, white_nh_female_under5,
total_under5, white_nh_under5, white_nh_under5_perc,
asian_male_under5, asian_female_under5, asian_under5,
nhpi_male_under5, nhpi_female_under5, nhpi_under5,
white_asian_under5, white_asian_under5_perc
```

The Asian/NHPI under-5 fields come from **B01001D** and **B01001E**. Those are race-*alone* counts of any ethnicity — the B01001 race iterations have no "not Hispanic" variant — so they are a close but not exact analogue to the B03002 figures. Roughly 2% of Asians identify as Hispanic.

### Regenerating

```bash
python3 scripts/add_asian_nhpi_fields.py [--dry-run]
```

Stdlib-only, idempotent, joins on GEOID and reports match counts. Requires `CENSUS_API_KEY` in `.env` — **the Census API now rejects unkeyed requests**, 302-ing to `missing_key.html`.

## Births Data

```
GET /api/births → state-level birth race data, 1940-2024
```

**Response shape:**

```json
{
  "years": ["1940", "1941", ..., "2024"],
  "yearTypes": { "1940": "white_nh_est", ..., "1978": "white_nh", ... },
  "states": {
    "01": { "name": "Alabama", "1940": 54.5, ..., "2024": 47.2 },
    ...
  }
}
```

- Values are **both-parent WNH** — % of births where both mother and father are White Non-Hispanic
- `yearTypes`: `"white_nh"` = based on actual data (D149 or CDC adjusted), `"white_nh_est"` = estimated
- 2016+: D149 actual both-parent WNH; 1995-2015: CDC mother-only adjusted by correction factor; pre-1995: estimated
- State keys are FIPS codes

## Caching

All data endpoints (`/api/geo/*`, `/api/demographics/*`, `/api/births`) send:

```
Cache-Control: public, max-age=0, must-revalidate
```

and answer `304 Not Modified` to a matching `If-None-Match`. Helpers live in `app/caching.py`.

Three traps, each of which fails silently:

1. **FastAPI sends no `Cache-Control` by default.** `FileResponse` emits `ETag` and `Last-Modified` only. With no explicit freshness a browser applies the RFC 9111 §4.2.2 heuristic — about 10% of the response's age — and these files go months between changes, so clients served copies over a week old **without ever contacting the origin**. A deployed field looked missing on phones that had visited before while cold desktops rendered it correctly. Added 2026-08-19.

2. **A bare `FileResponse` never checks `If-None-Match`.** That comparison lives in Starlette's `StaticFiles`, not the response class. Adding `must-revalidate` without implementing it would have re-downloaded the 4.4 MB county TopoJSON on *every* page load.

3. **`FileResponse` defers its `stat()` until send time.** `response.headers["etag"]` does not exist at construction unless `stat_result=` is passed, so a comparison written the obvious way reads `None` and never matches — full body every time, with no error.

Also note **Cloudflare weakens ETags** when it compresses: the origin computes `"abc"` but the browser sends back `W/"abc"`. `_normalize()` strips the `W/` prefix before comparing, otherwise nothing ever matches.

Verify with:

```bash
ET=$(curl -s -D - -o /dev/null "$URL" | awk 'tolower($1)=="etag:"{print $2}' | tr -d '\r')
curl -s -o /dev/null -w '%{http_code}/%{size_download}\n' -H "If-None-Match: $ET" "$URL"   # want 304/0
curl -s -o /dev/null -w '%{http_code}/%{size_download}\n' -H 'If-None-Match: "x"' "$URL"    # want 200/<size>
```

## CORS

`app/main.py` configures `CORSMiddleware` with:

- **`allow_origins`** — explicit production hosts: `localhost:4200`, `localhost:3000`, `familymaps.onrender.com`, `wdwwa.com`, `www.wdwwa.com`
- **`allow_origin_regex`** — also permits any HTTP origin from RFC 1918 private LAN ranges (`10.*`, `172.16-31.*`, `192.168.*`) on any port. This lets developers test on phones via `ng serve --host 0.0.0.0` without per-IP allowlisting.

---

*Update when endpoint signatures change. Document request/response shapes here as they are formalized.*
