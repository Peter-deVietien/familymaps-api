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
GET /api/demographics/us_counties_percentages → WDWWA factor percentages
GET /api/demographics/fl_counties            → FL county demographics
GET /api/demographics/fl_tracts              → FL tract demographics
GET /api/demographics/fl_block_groups        → FL block group demographics
```

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

## CORS

`app/main.py` configures `CORSMiddleware` with:

- **`allow_origins`** — explicit production hosts: `localhost:4200`, `localhost:3000`, `familymaps.onrender.com`, `wdwwa.com`, `www.wdwwa.com`
- **`allow_origin_regex`** — also permits any HTTP origin from RFC 1918 private LAN ranges (`10.*`, `172.16-31.*`, `192.168.*`) on any port. This lets developers test on phones via `ng serve --host 0.0.0.0` without per-IP allowlisting.

---

*Update when endpoint signatures change. Document request/response shapes here as they are formalized.*
