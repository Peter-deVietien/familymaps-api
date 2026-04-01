from pathlib import Path

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse

router = APIRouter(prefix="/api/demographics", tags=["demographics"])

DATA_DIR = Path(__file__).resolve().parent.parent / "data"

DEMO_FILES = {
    "us_counties": "US_county_demographics.json",
    "us_counties_under5": "US_county_under5_demographics.json",
    "us_counties_percentages": "US_county_percentages.json",
    "fl_counties": "FL_county_demographics.json",
    "fl_tracts": "FL_tract_demographics.json",
    "fl_block_groups": "FL_block_group_demographics.json",
}


@router.get("/{dataset}")
async def get_demographics(dataset: str):
    """Serve demographics JSON files by dataset name.

    Datasets: us_counties, us_counties_under5, us_counties_percentages,
              fl_counties, fl_tracts, fl_block_groups
    """
    filename = DEMO_FILES.get(dataset)
    if not filename:
        raise HTTPException(
            status_code=404,
            detail=f"Unknown dataset '{dataset}'. Available: {list(DEMO_FILES.keys())}",
        )
    filepath = DATA_DIR / filename
    if not filepath.exists():
        raise HTTPException(status_code=404, detail=f"Data file not found: {filename}")
    return FileResponse(filepath, media_type="application/json")
