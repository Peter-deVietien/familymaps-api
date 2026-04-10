import json
from pathlib import Path

from fastapi import APIRouter
from fastapi.responses import JSONResponse

router = APIRouter(prefix="/api/births", tags=["births"])

DATA_DIR = Path(__file__).resolve().parent.parent / "data"

_cached_response: dict | None = None


@router.get("")
async def get_births_data():
    """State-level both-parent WNH birth data, 1940-2024.

    Returns years, year metric types, and per-state percentages
    of births where both parents are White Non-Hispanic, keyed by FIPS.
    """
    global _cached_response
    if _cached_response is None:
        with open(DATA_DIR / "births.json") as f:
            _cached_response = json.load(f)
    return JSONResponse(content=_cached_response)
