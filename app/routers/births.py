import json
from pathlib import Path

from fastapi import APIRouter, Request
from fastapi.responses import Response

from ..caching import etag_for, json_response

router = APIRouter(prefix="/api/births", tags=["births"])

DATA_DIR = Path(__file__).resolve().parent.parent / "data"

_cached_response: dict | None = None
_cached_etag: str | None = None


@router.get("")
async def get_births_data(request: Request) -> Response:
    """State-level both-parent WNH birth data, 1940-2024.

    Returns years, year metric types, and per-state percentages
    of births where both parents are White Non-Hispanic, keyed by FIPS.
    """
    global _cached_response, _cached_etag
    if _cached_response is None:
        raw = (DATA_DIR / "births.json").read_bytes()
        _cached_response = json.loads(raw)
        _cached_etag = etag_for(raw)
    return json_response(request, _cached_response, _cached_etag)
