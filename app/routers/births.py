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


def _build_births_data() -> dict:
    """Read smooth_wnh.csv and convert to the BirthsData JSON shape.

    Uses pct_white_nh_smooth for all years — a continuous both-parent WNH
    series (% of babies where both parents are White Non-Hispanic):
      - 2016+: D149 actual both-parent WNH
      - 1995-2015: CDC mother-only WNH adjusted by per-state correction factor
      - 1978-1994: NBER/estimated mother-only WNH adjusted by correction factor
      - Pre-1978: Estimated from pct_white, adjusted for Hispanic + both-parent

    yearTypes: "white_nh" (D149 actual or CDC adjusted), "white_nh_est" (estimated).
    """
    csv_path = DATA_DIR / "smooth_wnh.csv"

    raw_rows: list[dict] = []
    all_years: set[str] = set()
    year_methods: dict[str, set[str]] = {}

    with open(csv_path, newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            if not STATE_NAME_TO_FIPS.get(row["state"]):
                continue
            raw_rows.append(row)
            year = row["year"]
            all_years.add(year)
            method = row.get("wnh_method", "")
            if year not in year_methods:
                year_methods[year] = set()
            year_methods[year].add(method)

    years = sorted(all_years)

    # Classify each year by its dominant method
    year_types: dict[str, str] = {}
    for y in years:
        methods = year_methods.get(y, set())
        actual_methods = {"d149_both_parent", "cdc_adjusted_both_parent",
                         "nber_adjusted_both_parent"}
        if methods & actual_methods:
            year_types[y] = "white_nh"
        else:
            year_types[y] = "white_nh_est"

    states: dict[str, dict] = {}
    for row in raw_rows:
        fips = STATE_NAME_TO_FIPS[row["state"]]
        year = row["year"]
        raw = row.get("pct_white_nh_smooth", "").strip()

        if not raw:
            continue

        if fips not in states:
            states[fips] = {"name": row["state"]}
        states[fips][year] = round(float(raw), 2)

    return {"years": years, "yearTypes": year_types, "states": states}


@router.get("")
async def get_births_data():
    """State-level both-parent WNH birth data, 1940-2024.

    Returns years, year metric types, and per-state percentages
    of births where both parents are White Non-Hispanic, keyed by FIPS.
    """
    global _cached_response
    if _cached_response is None:
        _cached_response = _build_births_data()
    return JSONResponse(content=_cached_response)
