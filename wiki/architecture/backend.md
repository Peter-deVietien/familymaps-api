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

Birth data is pre-baked as `app/data/births.json` (59KB) — a FIPS-keyed JSON with years,
year types, and both-parent WNH percentages per state. The births router loads and caches
this file on first request. To regenerate after updating the source data pipeline:

```bash
cd ~/familymaps-api
python3 -c "
import json, sys; sys.path.insert(0, '.')
# Temporarily needs the old CSV-based builder or regenerate from smooth_wnh.csv
from data.build_births_json import build; data = build()
with open('app/data/births.json', 'w') as f: json.dump(data, f, separators=(',', ':'))
"
```

All other data files (`*_demographics.json`, `*.topojson`, `US_county_percentages.json`)
are also static files in `app/data/`, committed to git and deployed directly.

See `data/overview.md` for the full data source matrix.

---

*Update when endpoints change or new routers are added.*
