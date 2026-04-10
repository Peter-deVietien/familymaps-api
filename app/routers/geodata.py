from pathlib import Path

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse

router = APIRouter(prefix="/api/geo", tags=["geography"])

DATA_DIR = Path(__file__).resolve().parent.parent / "data"

GEO_FILES = {
    "us_states": "US_states_geo.topojson",
    "us_counties": "US_county_geo.topojson",
    "fl_counties": "FL_county_geo.topojson",
    "fl_tracts": "FL_tract_geo.topojson",
    "fl_block_groups": "FL_block_group_geo.topojson",
}


@router.get("/{level}")
async def get_geo(level: str):
    """Serve TopoJSON geography files by level name.

    Levels: us_counties, fl_counties, fl_tracts, fl_block_groups
    """
    filename = GEO_FILES.get(level)
    if not filename:
        raise HTTPException(
            status_code=404,
            detail=f"Unknown geo level '{level}'. Available: {list(GEO_FILES.keys())}",
        )
    filepath = DATA_DIR / filename
    if not filepath.exists():
        raise HTTPException(status_code=404, detail=f"Data file not found: {filename}")
    return FileResponse(filepath, media_type="application/json")
