# FamilyMaps API

FastAPI backend serving demographic and geographic data for FamilyMaps.

## Setup

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Run

```bash
uvicorn app.main:app --reload
```

The API will be available at `http://localhost:8000`. Interactive docs at `http://localhost:8000/docs`.

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
| `GET /api/demographics/us_counties_under5` | US county under-5 demographics |
| `GET /api/demographics/us_counties_percentages` | US county percentages (WDWWA factors) |
| `GET /api/demographics/fl_counties` | Florida county demographics |
| `GET /api/demographics/fl_tracts` | Florida tract demographics |
| `GET /api/demographics/fl_block_groups` | Florida block group demographics |

### Utility

| Endpoint | Description |
|----------|-------------|
| `GET /health` | Health check |

## Data Scripts

Jupyter notebooks in `scripts/` download and prepare data from the Census API.
