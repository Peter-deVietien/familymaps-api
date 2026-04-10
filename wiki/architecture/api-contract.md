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
  "yearTypes": { "1940": "white", ..., "1995": "white_nh", ... },
  "states": {
    "01": { "name": "Alabama", "1940": 61.8, ..., "2024": 57.34 },
    ...
  }
}
```

- `yearTypes`: `"white"` = White incl. Hispanic (pre-1989), `"white_nh"` = White Non-Hispanic (1989+)
- State keys are FIPS codes; values are percentage of births that are White (or White NH)

## CORS

The API allows cross-origin requests from the frontend domain.

---

*Update when endpoint signatures change. Document request/response shapes here as they are formalized.*
