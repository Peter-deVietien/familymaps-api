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
| `GET /api/demographics/us_counties_obesity` | US county adult obesity (CDC PLACES) |
| `GET /api/demographics/us_counties_economy` | US county 10-year job growth (BLS QCEW) and business applications (Census BFS) per resident |
| `GET /api/demographics/us_counties_fertility` | US county White NH total fertility rate, estimated from Census population pyramids |
| `GET /api/demographics/us_counties_singles` | US county single (not married) White NH women per single White NH man, ages 20-34, from ACS 2020-2024 head counts and PUMS single shares |
| `GET /api/demographics/fl_counties` | Florida county demographics |
| `GET /api/demographics/fl_tracts` | Florida tract demographics |
| `GET /api/demographics/fl_block_groups` | Florida block group demographics |

### Utility

| Endpoint | Description |
|----------|-------------|
| `GET /health` | Health check |

## Data Scripts

Jupyter notebooks in `scripts/` download and prepare data from the Census API.

County economy data (no API key needed):

```bash
python3 scripts/download_economy_data.py
python3 scripts/build_economy_dataset.py [--dry-run]
```

County fertility data (no API key needed; downloads the Census file on first run):

```bash
python3 scripts/build_fertility_dataset.py [--dry-run]
```

County singles data (needs a Census API key in `census_api_key` or `CENSUS_API_KEY`; caches API responses on first run):

```bash
python3 scripts/build_singles_dataset.py [--dry-run]
```
