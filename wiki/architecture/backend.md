# Backend Architecture

> FastAPI backend at `~/familymaps-api`. Read when modifying API endpoints or data serving logic.

## Stack

- **Framework:** FastAPI (Python)
- **Server:** Uvicorn (`uvicorn app.main:app --reload`)
- **Hosting:** Render
- **URL:** `https://api.wdwwa.com`

## Project Structure

```
app/
├── main.py              ← FastAPI app setup, CORS, router includes
├── database.py          ← Database connection (if any)
├── xai_client.py        ← xAI API client for church events
├── routers/
│   ├── geodata.py       ← /api/geo/* endpoints (TopoJSON)
│   ├── demographics.py  ← /api/demographics/* endpoints (JSON)
│   ├── births.py        ← /api/births endpoint (CSV→JSON at startup)
│   └── churchevents.py  ← /api/churchevents/* endpoints
└── data/                ← Static data files served by endpoints
    ├── *_geo.topojson   ← Geographic boundary files
    ├── *_demographics.json ← Demographic data
    └── US_county_percentages.json ← WDWWA factors
```

## API Endpoints

### Geography (TopoJSON)
| Endpoint | Description |
|----------|-------------|
| `GET /api/geo/us_counties` | US county boundaries |
| `GET /api/geo/fl_counties` | Florida county boundaries |
| `GET /api/geo/fl_tracts` | Florida census tracts |
| `GET /api/geo/fl_block_groups` | Florida block groups |

### Demographics (JSON)
| Endpoint | Description |
|----------|-------------|
| `GET /api/demographics/us_counties` | US county demographics |
| `GET /api/demographics/us_counties_under5` | Under-5 demographics |
| `GET /api/demographics/us_counties_percentages` | WDWWA factors |
| `GET /api/demographics/fl_counties` | FL county demographics |
| `GET /api/demographics/fl_tracts` | FL tract demographics |
| `GET /api/demographics/fl_block_groups` | FL block group demographics |

### Births
| Endpoint | Description |
|----------|-------------|
| `GET /api/births` | State-level birth data by race/ethnicity, 1940-2024 |

### Utility
| Endpoint | Description |
|----------|-------------|
| `GET /health` | Health check |

## Data Pipeline

Birth data is read from `data/extracted_data/best_estimate.csv` by the births router at startup,
converted to JSON (FIPS-keyed, with year types and percentages), cached in memory, and served
via `GET /api/births`. No static JSON file is needed.

See `data/overview.md` for the full data source matrix.

---

*Update when endpoints change or new routers are added.*
