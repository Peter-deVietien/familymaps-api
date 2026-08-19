#!/usr/bin/env python3
"""Merge the pleasant-days climate metric into the served percentages JSON.

Joins county_pleasant_days.csv onto app/data/US_county_percentages.json by
GEOID, adding a single `pleasant_days` field. Existing fields are never
removed, so this is safe to re-run.

nClimGrid-Daily covers the 3,107 CONUS counties only. Alaska, Hawaii and the
territories get `null`, which the frontend's rank algorithm already treats as
"exclude from ranking" the same way it does for null trump_pct.

Usage:
    python3 scripts/add_pleasant_days_field.py [--dry-run]
"""

from __future__ import annotations

import argparse
import csv
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
TARGET = REPO_ROOT / "app" / "data" / "US_county_percentages.json"
SOURCE = REPO_ROOT / "data" / "extracted_data" / "county_pleasant_days.csv"

# Census GEOIDs that nClimGrid does not report, mapped to the county whose
# climate stands in for them.
GEOID_CROSSWALK = {
    # Lexington city is an independent city forming an enclave entirely inside
    # Rockbridge County, and is too small for nClimGrid to resolve separately.
    "51678": "51163",
    # Connecticut retired its eight counties for nine planning regions in 2022.
    # The ACS 2023 percentages use the new GEOIDs while nClimGrid still reports
    # the legacy counties, so each region borrows the county covering most of
    # it. Values span 74.8-89.6 days statewide, too wide for a single average.
    "09110": "09003",  # Capitol <- Hartford
    "09120": "09001",  # Greater Bridgeport <- Fairfield
    "09130": "09007",  # Lower Connecticut River Valley <- Middlesex
    "09140": "09009",  # Naugatuck Valley <- New Haven
    "09150": "09015",  # Northeastern Connecticut <- Windham
    "09160": "09005",  # Northwest Hills <- Litchfield
    "09170": "09009",  # South Central Connecticut <- New Haven
    "09180": "09011",  # Southeastern Connecticut <- New London
    "09190": "09001",  # Western Connecticut <- Fairfield
}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    if not SOURCE.exists():
        print(f"error: {SOURCE} not found - run compute_pleasant_days.py first")
        return 1

    with SOURCE.open(newline="") as fh:
        climate = {
            row["GEOID"]: float(row["pleasant_days"]) for row in csv.DictReader(fh)
        }

    counties = json.loads(TARGET.read_text())

    matched = 0
    crosswalked = 0
    for county in counties:
        geoid = county["GEOID"]
        value = climate.get(geoid)
        if value is None and geoid in GEOID_CROSSWALK:
            value = climate.get(GEOID_CROSSWALK[geoid])
            if value is not None:
                crosswalked += 1
        county["pleasant_days"] = value
        if value is not None:
            matched += 1

    unmatched = len(counties) - matched
    print(f"climate rows:     {len(climate)}")
    print(f"counties in JSON: {len(counties)}")
    print(f"matched:          {matched} ({crosswalked} via crosswalk)")
    print(f"null:             {unmatched}")

    # Anything in the climate file that has no home in the percentages file
    # means the two datasets disagree about county identity, which would
    # silently drop data rather than just leaving it unranked.
    # Legacy Connecticut counties are a superseded geography, so ones that no
    # planning region borrows from (Tolland, which splits across two rather
    # than dominating either) are expected leftovers rather than lost data.
    resolved = {c["GEOID"] for c in counties} | {
        g for g in climate if g.startswith("09")
    }
    orphans = set(climate) - resolved
    if orphans:
        print(f"warning: {len(orphans)} climate GEOIDs absent from JSON: "
              f"{sorted(orphans)[:10]}")

    if args.dry_run:
        print("\ndry run - nothing written")
        return 0

    TARGET.write_text(json.dumps(counties))
    print(f"\nwrote {TARGET}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
