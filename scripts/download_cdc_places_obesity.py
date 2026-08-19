#!/usr/bin/env python3
"""Download county adult-obesity prevalence from the CDC PLACES Socrata API.

PLACES models BRFSS responses down to the county level, giving a single
`OBESITY` measure: the share of adults 18+ reporting a BMI of 30 or more.
Height and weight are self-reported, so the level runs several points below
what a measured survey like NHANES finds. Only the geographic spread is
trustworthy, not the absolute value.

Two releases are pulled and coalesced. The 2025 release (BRFSS 2023) is the
most recent, but BRFSS produced no usable 2023 data for Kentucky or
Pennsylvania, so those 187 counties are absent from it entirely. The 2024
release (BRFSS 2022) covers all 50 states, so it backfills whatever 2025 is
missing. Every row records which release it came from.

Both releases key on 5-digit county FIPS and already use Connecticut's nine
planning regions, matching the GEOIDs in US_county_percentages.json.

Usage:
    python3 scripts/download_cdc_places_obesity.py
"""

from __future__ import annotations

import csv
import json
import sys
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
OUTPUT = REPO_ROOT / "data" / "extracted_data" / "county_obesity.csv"

# Socrata dataset ids for the PLACES county files, newest first. The BRFSS year
# is what the estimate actually describes; the release year is just when CDC
# published it.
RELEASES = [
    {"dataset": "swc5-untb", "release": 2025, "brfss_year": 2023},
    {"dataset": "fu4u-a9bh", "release": 2024, "brfss_year": 2022},
]

# Socrata caps a single page at 50k rows. One measure across ~3,000 counties in
# two value types is ~6k, so this fetches each release in one request.
PAGE_LIMIT = 50000

# PLACES reports a bare `locationname` ("Orleans", "Capitol"), which cannot be
# turned into a display name without knowing whether the county is a parish,
# borough, independent city or planning region. The build step takes the
# canonical name from the existing county roster instead; these columns are kept
# only so the CSV is readable on its own.
FIELDS = [
    "GEOID",
    "places_name",
    "state",
    "obesity_pct",
    "obesity_pct_age_adj",
    "ci_low",
    "ci_high",
    "brfss_year",
]


def fetch_release(dataset: str) -> list[dict]:
    query = urllib.parse.urlencode(
        {
            "measureid": "OBESITY",
            "$select": ",".join(
                [
                    "locationid",
                    "locationname",
                    "stateabbr",
                    "statedesc",
                    "datavaluetypeid",
                    "data_value",
                    "low_confidence_limit",
                    "high_confidence_limit",
                ]
            ),
            "$limit": PAGE_LIMIT,
        }
    )
    url = f"https://data.cdc.gov/resource/{dataset}.json?{query}"
    with urllib.request.urlopen(url, timeout=120) as response:
        return json.loads(response.read())


def collapse(rows: list[dict], brfss_year: int) -> dict[str, dict]:
    """Fold the crude and age-adjusted rows for each county into one record.

    PLACES emits one row per county per value type. The crude rate is what
    people actually weigh in that county; the age-adjusted rate reweights it to
    a standard age distribution so counties with different age structures can be
    compared. Neither is broken out by age -- both cover all adults 18+.
    """
    counties: dict[str, dict] = {}
    for row in rows:
        geoid = row.get("locationid")
        value = row.get("data_value")
        if not geoid or value is None:
            continue
        # The county file also carries a national aggregate under a 2-digit id
        # (32.8% for BRFSS 2023, matching CDC's published national rate). Useful
        # as a sanity check, but it is not a county.
        if len(geoid) != 5:
            continue

        county = counties.setdefault(
            geoid,
            {
                "GEOID": geoid,
                "places_name": row.get("locationname", ""),
                "state": row.get("statedesc", ""),
                "obesity_pct": None,
                "obesity_pct_age_adj": None,
                "ci_low": None,
                "ci_high": None,
                "brfss_year": brfss_year,
            },
        )

        if row.get("datavaluetypeid") == "CrdPrv":
            county["obesity_pct"] = float(value)
            # Confidence limits are only carried for the crude rate, since that
            # is what the map colours by.
            county["ci_low"] = _optional_float(row.get("low_confidence_limit"))
            county["ci_high"] = _optional_float(row.get("high_confidence_limit"))
        elif row.get("datavaluetypeid") == "AgeAdjPrv":
            county["obesity_pct_age_adj"] = float(value)

    # A county with no crude rate has nothing to colour, so drop it rather than
    # ship a row that reads as present but renders as missing data.
    return {g: c for g, c in counties.items() if c["obesity_pct"] is not None}


def _optional_float(value: str | None) -> float | None:
    return float(value) if value not in (None, "") else None


def main() -> int:
    merged: dict[str, dict] = {}

    for spec in RELEASES:
        try:
            rows = fetch_release(spec["dataset"])
        except urllib.error.URLError as err:
            print(f"error: {spec['release']} release ({spec['dataset']}): {err}")
            return 1

        counties = collapse(rows, spec["brfss_year"])
        added = [g for g in counties if g not in merged]
        for geoid in added:
            merged[geoid] = counties[geoid]

        print(
            f"{spec['release']} release (BRFSS {spec['brfss_year']}): "
            f"{len(counties)} counties, {len(added)} new"
        )

    if not merged:
        print("error: no counties returned")
        return 1

    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    with OUTPUT.open("w", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=FIELDS)
        writer.writeheader()
        for geoid in sorted(merged):
            writer.writerow(merged[geoid])

    by_year: dict[int, int] = {}
    for county in merged.values():
        by_year[county["brfss_year"]] = by_year.get(county["brfss_year"], 0) + 1

    print(f"\ntotal counties: {len(merged)}")
    for year in sorted(by_year, reverse=True):
        print(f"  BRFSS {year}: {by_year[year]}")
    print(f"wrote {OUTPUT}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
