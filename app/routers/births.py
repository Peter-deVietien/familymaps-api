import csv
from pathlib import Path

from fastapi import APIRouter
from fastapi.responses import JSONResponse

router = APIRouter(prefix="/api/births", tags=["births"])

DATA_DIR = Path(__file__).resolve().parent.parent.parent / "data" / "extracted_data"

STATE_NAME_TO_FIPS = {
    "Alabama": "01", "Alaska": "02", "Arizona": "04", "Arkansas": "05",
    "California": "06", "Colorado": "08", "Connecticut": "09", "Delaware": "10",
    "District of Columbia": "11", "Florida": "12", "Georgia": "13", "Hawaii": "15",
    "Idaho": "16", "Illinois": "17", "Indiana": "18", "Iowa": "19",
    "Kansas": "20", "Kentucky": "21", "Louisiana": "22", "Maine": "23",
    "Maryland": "24", "Massachusetts": "25", "Michigan": "26", "Minnesota": "27",
    "Mississippi": "28", "Missouri": "29", "Montana": "30", "Nebraska": "31",
    "Nevada": "32", "New Hampshire": "33", "New Jersey": "34", "New Mexico": "35",
    "New York": "36", "North Carolina": "37", "North Dakota": "38", "Ohio": "39",
    "Oklahoma": "40", "Oregon": "41", "Pennsylvania": "42", "Rhode Island": "44",
    "South Carolina": "45", "South Dakota": "46", "Tennessee": "47", "Texas": "48",
    "Utah": "49", "Vermont": "50", "Virginia": "51", "Washington": "53",
    "West Virginia": "54", "Wisconsin": "55", "Wyoming": "56",
}

_cached_response: dict | None = None


WNH_COVERAGE_THRESHOLD = 46  # out of 51 states+DC — use WNH when >= this many report it


def _build_births_data() -> dict:
    """Read best_estimate.csv and convert to the BirthsData JSON shape:

    {
      years: ["1940", "1941", ...],
      yearTypes: { "1940": "white", ..., "1995": "white_nh", ... },
      states: {
        "01": { name: "Alabama", "1940": 61.8, "1941": 62.0, ... },
        ...
      }
    }

    Year type is determined by WNH coverage: if >= WNH_COVERAGE_THRESHOLD states
    report pct_white_nh for a year, that year uses "white_nh" for all states;
    otherwise it uses "white". This avoids mixing metrics within a single year.
    """
    csv_path = DATA_DIR / "best_estimate.csv"

    # First pass: collect raw data and count WNH coverage per year
    raw_rows: list[dict] = []
    year_nh_count: dict[str, int] = {}
    all_years: set[str] = set()

    with open(csv_path, newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            if not STATE_NAME_TO_FIPS.get(row["state"]):
                continue
            raw_rows.append(row)
            year = row["year"]
            all_years.add(year)
            pct_wnh = row["pct_white_nh"].strip() if row["pct_white_nh"] else ""
            if pct_wnh:
                year_nh_count[year] = year_nh_count.get(year, 0) + 1

    years = sorted(all_years)

    # Determine year types based on coverage threshold
    year_types: dict[str, str] = {}
    for y in years:
        year_types[y] = "white_nh" if year_nh_count.get(y, 0) >= WNH_COVERAGE_THRESHOLD else "white"

    # Second pass: build state data using the correct metric per year
    states: dict[str, dict] = {}
    for row in raw_rows:
        fips = STATE_NAME_TO_FIPS[row["state"]]
        year = row["year"]

        if year_types[year] == "white_nh":
            raw = row["pct_white_nh"].strip() if row["pct_white_nh"] else ""
            if not raw:
                raw = row["pct_white"].strip() if row["pct_white"] else ""
        else:
            raw = row["pct_white"].strip() if row["pct_white"] else ""

        if not raw:
            continue

        if fips not in states:
            states[fips] = {"name": row["state"]}
        states[fips][year] = round(float(raw), 2)

    return {"years": years, "yearTypes": year_types, "states": states}


@router.get("")
async def get_births_data():
    """State-level birth data by race/ethnicity, 1940-2024.

    Returns years, year metric types (white vs white_nh), and
    per-state percentages keyed by FIPS code.
    """
    global _cached_response
    if _cached_response is None:
        _cached_response = _build_births_data()
    return JSONResponse(content=_cached_response)
