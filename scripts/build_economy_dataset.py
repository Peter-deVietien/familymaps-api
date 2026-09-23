#!/usr/bin/env python3
"""Build the served county economy JSON from the downloaded QCEW and BFS CSVs.

Two per-resident metrics, both joined onto the county roster in
US_county_percentages.json so the output carries the same 3,222 counties in
the same order as every other county dataset:

  job_growth_per_100  Jobs added over the QCEW window per 100 residents.
  biz_apps_per_1k     Business applications over the last 10 BFS years per
                      1,000 residents.

Both divide by the roster's current total_pop.

Boundary changes inside the window:
  - Connecticut replaced its 8 counties with 9 planning regions in 2022, and
    the regions do not nest inside the old counties. QCEW has no planning-region
    history, so every region gets the statewide job change per resident
    (jobs_basis "state"). BFS switches geography mid-window too, so each region
    uses only the years it was published under its own code.
  - Alaska's Valdez-Cordova split into Chugach and Copper River in 2019. The
    two halves share the combined area's job change per resident
    (jobs_basis "combined").

Business applications average the years a county was published and scale that
to 10 years, so a county missing some years (suppressed, or created mid-window)
is not penalised for them. Fewer than MIN_APP_YEARS published years is null.

Run scripts/download_economy_data.py first.

Usage:
    python3 scripts/build_economy_dataset.py [--dry-run]
"""

from __future__ import annotations

import argparse
import csv
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
JOBS_SOURCE = REPO_ROOT / "data" / "extracted_data" / "county_jobs.csv"
APPS_SOURCE = REPO_ROOT / "data" / "extracted_data" / "county_business_apps.csv"
ROSTER = REPO_ROOT / "app" / "data" / "US_county_percentages.json"
TARGET = REPO_ROOT / "app" / "data" / "US_county_economy.json"

APP_WINDOW = 10
MIN_APP_YEARS = 4

CT_OLD_COUNTIES = ["09001", "09003", "09005", "09007", "09009", "09011", "09013", "09015"]
CT_PLANNING_REGIONS = ["09110", "09120", "09130", "09140", "09150", "09160", "09170", "09180", "09190"]

# Areas whose start-year geography differs from the roster's: the job change
# is measured across the whole group and spread evenly per resident.
JOB_GROUPS = [
    {"start": CT_OLD_COUNTIES, "end": CT_PLANNING_REGIONS, "basis": "state"},
    {"start": ["02261"], "end": ["02063", "02066"], "basis": "combined"},
]


def optional_int(value: str) -> int | None:
    return int(value) if value.strip() else None


def load_jobs() -> tuple[int, int, dict[str, tuple[int | None, int | None]]]:
    with JOBS_SOURCE.open(newline="") as fh:
        reader = csv.DictReader(fh)
        start_col, end_col = sorted(c for c in reader.fieldnames if c.startswith("jobs_"))
        jobs = {
            row["GEOID"]: (optional_int(row[start_col]), optional_int(row[end_col]))
            for row in reader
        }
    return int(start_col[5:]), int(end_col[5:]), jobs


def load_apps() -> tuple[list[str], dict[str, list[int]]]:
    with APPS_SOURCE.open(newline="") as fh:
        reader = csv.DictReader(fh)
        window = sorted(c for c in reader.fieldnames if c.startswith("BA"))[-APP_WINDOW:]
        apps = {
            row["GEOID"]: [int(row[y]) for y in window if row[y].strip()]
            for row in reader
        }
    return window, apps


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    for source in (JOBS_SOURCE, APPS_SOURCE):
        if not source.exists():
            print(f"error: {source} not found - run download_economy_data.py first")
            return 1

    start_year, end_year, jobs = load_jobs()
    app_window, apps = load_apps()
    roster = json.loads(ROSTER.read_text())
    pop = {c["GEOID"]: c.get("total_pop") or 0 for c in roster}

    grouped: dict[str, tuple[float | None, str]] = {}
    for group in JOB_GROUPS:
        starts = [jobs.get(g, (None, None))[0] for g in group["start"]]
        ends = [jobs.get(g, (None, None))[1] for g in group["end"]]
        group_pop = sum(pop.get(g, 0) for g in group["end"])
        per_100 = None
        if None not in starts and None not in ends and group_pop > 0:
            per_100 = round((sum(ends) - sum(starts)) / group_pop * 100, 2)
        for geoid in group["end"]:
            grouped[geoid] = (per_100, group["basis"])

    counties = []
    for entry in roster:
        geoid = entry["GEOID"]
        residents = pop[geoid]
        start, end = jobs.get(geoid, (None, None))

        if geoid in grouped:
            job_growth, basis = grouped[geoid]
        elif start is not None and end is not None and residents > 0:
            job_growth, basis = round((end - start) / residents * 100, 2), "county"
        else:
            job_growth, basis = None, None

        years = apps.get(geoid, [])
        apps_10yr = sum(years) / len(years) * APP_WINDOW if len(years) >= MIN_APP_YEARS else None

        counties.append(
            {
                "GEOID": geoid,
                "name": entry["name"],
                "total_pop": entry.get("total_pop"),
                f"jobs_{start_year}": start,
                f"jobs_{end_year}": end,
                "job_growth_per_100": job_growth,
                "jobs_basis": basis if job_growth is not None else None,
                "biz_apps_10yr": round(apps_10yr) if apps_10yr is not None else None,
                "biz_apps_years": len(years) if apps_10yr is not None else None,
                "biz_apps_per_1k": (
                    round(apps_10yr / residents * 1000, 1)
                    if apps_10yr is not None and residents > 0
                    else None
                ),
            }
        )

    def summarize(key: str) -> None:
        values = sorted(c[key] for c in counties if c[key] is not None)
        if not values:
            print(f"{key}: no values")
            return
        print(
            f"{key}: {len(values)}/{len(counties)} populated, "
            f"min {values[0]}, median {values[len(values) // 2]}, max {values[-1]}"
        )

    print(f"roster counties:  {len(roster)}")
    print(f"jobs window:      {start_year}-{end_year}")
    print(f"apps window:      {app_window[0][2:]}-{app_window[-1][2:]}")
    summarize("job_growth_per_100")
    summarize("biz_apps_per_1k")

    missing = [
        f"{c['GEOID']} {c['name']}"
        for c in counties
        if (c["job_growth_per_100"] is None or c["biz_apps_per_1k"] is None)
        and not c["GEOID"].startswith("72")
    ]
    print(f"non-PR counties missing a metric: {missing}")

    if args.dry_run:
        print("\ndry run - nothing written")
        return 0

    TARGET.write_text(json.dumps(counties))
    print(f"\nwrote {TARGET}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
