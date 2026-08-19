#!/usr/bin/env python3
"""Build the served county obesity JSON from the downloaded PLACES CSV.

Joins county_obesity.csv onto the county roster in US_county_percentages.json by
GEOID so the output carries exactly the same 3,222 counties in the same order as
every other county dataset, with canonical display names. Counties PLACES has no
estimate for get null, which the frontend renders grey.

Run scripts/download_cdc_places_obesity.py first.

Usage:
    python3 scripts/build_obesity_dataset.py [--dry-run]
"""

from __future__ import annotations

import argparse
import csv
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
SOURCE = REPO_ROOT / "data" / "extracted_data" / "county_obesity.csv"
ROSTER = REPO_ROOT / "app" / "data" / "US_county_percentages.json"
TARGET = REPO_ROOT / "app" / "data" / "US_county_obesity.json"


def optional_float(value: str) -> float | None:
    return float(value) if value else None


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    if not SOURCE.exists():
        print(f"error: {SOURCE} not found - run download_cdc_places_obesity.py first")
        return 1

    with SOURCE.open(newline="") as fh:
        obesity = {row["GEOID"]: row for row in csv.DictReader(fh)}

    roster = json.loads(ROSTER.read_text())

    counties = []
    matched = 0
    for entry in roster:
        geoid = entry["GEOID"]
        row = obesity.get(geoid)
        if row:
            matched += 1
        counties.append(
            {
                "GEOID": geoid,
                "name": entry["name"],
                "total_pop": entry.get("total_pop"),
                "obesity_pct": optional_float(row["obesity_pct"]) if row else None,
                "obesity_pct_age_adj": (
                    optional_float(row["obesity_pct_age_adj"]) if row else None
                ),
                "ci_low": optional_float(row["ci_low"]) if row else None,
                "ci_high": optional_float(row["ci_high"]) if row else None,
                "brfss_year": int(row["brfss_year"]) if row else None,
            }
        )

    values = [c["obesity_pct"] for c in counties if c["obesity_pct"] is not None]
    print(f"roster counties:  {len(roster)}")
    print(f"PLACES counties:  {len(obesity)}")
    print(f"matched:          {matched}")
    print(f"null:             {len(counties) - matched}")
    if values:
        print(f"obesity_pct:      {min(values):.1f}% - {max(values):.1f}%")

    # PLACES GEOIDs with no home in the roster mean the two disagree about county
    # identity, which would silently drop counties from the map.
    orphans = set(obesity) - {c["GEOID"] for c in roster}
    if orphans:
        print(
            f"warning: {len(orphans)} PLACES GEOIDs absent from roster: "
            f"{sorted(orphans)[:10]}"
        )

    if args.dry_run:
        print("\ndry run - nothing written")
        return 0

    TARGET.write_text(json.dumps(counties))
    print(f"\nwrote {TARGET}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
