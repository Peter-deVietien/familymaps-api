#!/usr/bin/env python3
"""Build the served county fertility JSON: White non-Hispanic total fertility
rate (TFR) for every county.

Birth-certificate TFR by county is only public for counties of 100,000+
people (CDC WONDER lumps the rest together per state), so this estimates TFR
from each county's population pyramid with the xTFR estimator of Hauer &
Schmertmann (2020, Demography 57:221-241):

    xTFR = (10.65 - 12.55 * p) * C / W

    C  children aged 0-4
    W  women aged 15-49
    p  share of W aged 25-34

using White-alone, non-Hispanic counts from the Census Bureau's Vintage 2024
county characteristics estimates (July 1, 2024). Children 0-4 on that date
were born mid-2019 to mid-2024, so the result is roughly a 2020-2024 TFR.

Census labels a child's race, not the mother's, and many children of White NH
mothers are recorded as multiracial or Hispanic, so the raw White NH estimate
runs low. Every county is scaled by one national factor so the US total
matches CDC_WNH_TFR; that sets the level without changing the order. Against
CDC WONDER birth-certificate TFRs for the 572 named counties (100k+, excluding
Connecticut), the scaled estimate has a median absolute error of about 0.1
births per woman and a rank correlation of 0.87. It reads low in cities that
young families leave before their kids turn five and in military counties, and
high in some heavily Hispanic ones.

Small counties: Census's race-by-age detail for small counties is several
times noisier than counting noise alone, so each county's pyramid is blended
with PRIOR_WOMEN women's worth of its state's White NH pyramid before the
estimate is taken. A county with PRIOR_WOMEN White NH women aged 15-49 lands
halfway between its own figure and its state's; one with ten times that is
~90% its own. tfr_wnh_raw keeps the unblended figure.

Puerto Rico is not in the county characteristics file, so its municipios are
null.

Usage:
    python3 scripts/build_fertility_dataset.py [--dry-run]
"""

from __future__ import annotations

import argparse
import csv
import json
import sys
import urllib.request
from collections import defaultdict
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
SOURCE_URL = (
    "https://www2.census.gov/programs-surveys/popest/datasets/"
    "2020-2024/counties/asrh/cc-est2024-alldata.csv"
)
SOURCE = REPO_ROOT / "data" / "census_pep" / "raw-data" / "cc-est2024-alldata.csv"
ROSTER = REPO_ROOT / "app" / "data" / "US_county_percentages.json"
TARGET = REPO_ROOT / "app" / "data" / "US_county_fertility.json"

# YEAR code for the July 1, 2024 estimate in the 2020-2024 vintage.
ESTIMATE_YEAR = "6"
PRIOR_WOMEN = 750
# White NH mothers' TFR for US births 2020-2024: CDC WONDER Natality 2007-2024,
# 5 x the sum of age-specific rates for ages 15-44, plus births to 45-49.
CDC_WNH_TFR = 1.546

# AGEGRP codes: 1 = 0-4, 4..10 = 15-19 .. 45-49, 6-7 = 25-34.
CHILD_GROUPS = {"1"}
WOMEN_GROUPS = {str(g) for g in range(4, 11)}
PEAK_GROUPS = {"6", "7"}


def download() -> None:
    SOURCE.parent.mkdir(parents=True, exist_ok=True)
    print(f"downloading {SOURCE_URL}")
    urllib.request.urlretrieve(SOURCE_URL, SOURCE)


def load_pyramids() -> dict[str, dict[str, float]]:
    """White NH children 0-4, women 15-49 and women 25-34 per county."""
    counts: dict[str, dict[str, float]] = defaultdict(lambda: {"kids": 0, "women": 0, "peak": 0})
    with SOURCE.open(newline="", encoding="latin-1") as fh:
        for row in csv.DictReader(fh):
            if row["YEAR"] != ESTIMATE_YEAR:
                continue
            geoid = row["STATE"] + row["COUNTY"]
            age = row["AGEGRP"]
            c = counts[geoid]
            if age in CHILD_GROUPS:
                c["kids"] += int(row["NHWA_MALE"]) + int(row["NHWA_FEMALE"])
            if age in WOMEN_GROUPS:
                c["women"] += int(row["NHWA_FEMALE"])
            if age in PEAK_GROUPS:
                c["peak"] += int(row["NHWA_FEMALE"])
    return dict(counts)


def xtfr(kids: float, women: float, peak: float) -> float | None:
    if women <= 0:
        return None
    return (10.65 - 12.55 * peak / women) * kids / women


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    if not SOURCE.exists():
        download()

    pyramids = load_pyramids()
    states: dict[str, dict[str, float]] = defaultdict(lambda: {"kids": 0, "women": 0, "peak": 0})
    for geoid, c in pyramids.items():
        for key, value in c.items():
            states[geoid[:2]][key] += value

    us = {k: sum(s[k] for s in states.values()) for k in ("kids", "women", "peak")}
    us_xtfr = xtfr(us["kids"], us["women"], us["peak"])
    calibration = CDC_WNH_TFR / us_xtfr

    roster = json.loads(ROSTER.read_text())
    counties = []
    for entry in roster:
        geoid = entry["GEOID"]
        c = pyramids.get(geoid)
        raw = smoothed = None
        if c is not None:
            raw = xtfr(c["kids"], c["women"], c["peak"])
            s = states[geoid[:2]]
            share = PRIOR_WOMEN / s["women"]
            smoothed = xtfr(
                c["kids"] + s["kids"] * share,
                c["women"] + PRIOR_WOMEN,
                c["peak"] + s["peak"] * share,
            )
            raw = raw * calibration if raw is not None else None
            smoothed = smoothed * calibration if smoothed is not None else None
        counties.append(
            {
                "GEOID": geoid,
                "name": entry["name"],
                "total_pop": entry.get("total_pop"),
                "wnh_children_0_4": c["kids"] if c else None,
                "wnh_women_15_49": c["women"] if c else None,
                "tfr_wnh_raw": round(raw, 3) if raw is not None else None,
                "tfr_wnh": round(smoothed, 3) if smoothed is not None else None,
            }
        )

    print(f"roster counties:  {len(roster)}")
    print(f"national WNH xTFR: {us_xtfr:.3f} -> x{calibration:.3f} to match CDC {CDC_WNH_TFR}")
    for key in ("tfr_wnh_raw", "tfr_wnh"):
        values = sorted(c[key] for c in counties if c[key] is not None)
        print(
            f"{key}: {len(values)}/{len(counties)} populated, min {values[0]}, "
            f"median {values[len(values) // 2]}, max {values[-1]}"
        )
    missing = [c["GEOID"] for c in counties if c["tfr_wnh"] is None and not c["GEOID"].startswith("72")]
    print(f"non-PR counties missing tfr_wnh: {missing}")

    if args.dry_run:
        print("\ndry run - nothing written")
        return 0

    TARGET.write_text(json.dumps(counties))
    print(f"\nwrote {TARGET}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
