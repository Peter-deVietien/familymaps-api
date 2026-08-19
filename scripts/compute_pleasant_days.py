#!/usr/bin/env python3
"""Compute average "pleasant days per year" per county from nClimGrid-Daily.

Reads the county area-average CSVs fetched by download_nclimgrid.py and counts
days that clear every comfort threshold, then normalises to a per-year rate.

Input format (no header, one row per county per month):
    cty,{CODE},{ST: County Name},{YYYY},{MM},{VAR},{day1},{day2},...,{dayN}
Temperatures are degrees Celsius, precipitation is millimetres.

The leading two digits of {CODE} are NOT a FIPS state code. NCEI numbers the
CONUS states 01-48 alphabetically (Alaska and Hawaii omitted), so 04 is
California rather than Arizona, and DC is filed under Maryland's 18. Alabama is
01 in both schemes, which makes a spot check of the first row look correct. The
trailing three digits are a real county FIPS, so GEOIDs are rebuilt from the
state abbreviation in the name field.

Usage:
    python3 scripts/compute_pleasant_days.py [--start 1995] [--end 2024]
"""

import argparse
import csv
import sys
from collections import defaultdict
from pathlib import Path

DATA_DIR = Path(__file__).resolve().parent.parent / "data" / "nclimgrid"
OUT_PATH = (
    Path(__file__).resolve().parent.parent
    / "data"
    / "extracted_data"
    / "county_pleasant_days.csv"
)

# Thresholds in source units (Celsius / millimetres), annotated with the
# Fahrenheit values they came from.
TMAX_MIN_C = 15.56  # 60F - warmer than a jacket day
TMAX_MAX_C = 29.44  # 85F - cooler than uncomfortably hot
TMIN_MIN_C = 4.44   # 40F - no overnight freeze
# 68F. Warm nights track high dewpoint closely, so this upper bound stands in
# for the humidity term nClimGrid does not carry. Without it a muggy Gulf Coast
# night scores the same as a dry Mountain West one.
TMIN_MAX_C = 20.0
PRCP_MAX_MM = 0.254  # 0.01in - below the threshold for measurable rain

MISSING = -999.0
DAYS_PER_YEAR = 365.25

STATE_FIPS = {
    "AL": "01", "AZ": "04", "AR": "05", "CA": "06", "CO": "08", "CT": "09",
    "DE": "10", "DC": "11", "FL": "12", "GA": "13", "ID": "16", "IL": "17",
    "IN": "18", "IA": "19", "KS": "20", "KY": "21", "LA": "22", "ME": "23",
    "MD": "24", "MA": "25", "MI": "26", "MN": "27", "MS": "28", "MO": "29",
    "MT": "30", "NE": "31", "NV": "32", "NH": "33", "NJ": "34", "NM": "35",
    "NY": "36", "NC": "37", "ND": "38", "OH": "39", "OK": "40", "OR": "41",
    "PA": "42", "RI": "44", "SC": "45", "SD": "46", "TN": "47", "TX": "48",
    "UT": "49", "VT": "50", "VA": "51", "WA": "53", "WV": "54", "WI": "55",
    "WY": "56",
}


def to_geoid(code: str, name: str) -> str | None:
    """Rebuild a real 5-digit FIPS GEOID from an NCEI county code and name."""
    abbrev, _, _ = name.partition(":")
    abbrev = abbrev.strip().upper()
    state = STATE_FIPS.get(abbrev)
    if state is None or len(code) < 5:
        return None
    # NCEI files DC as 18511 under Maryland; the Census county code is 001.
    if abbrev == "DC":
        return "11001"
    return state + code[-3:]


def read_month(path: Path) -> dict[str, list[float]]:
    """Return {geoid: [daily values]} for one variable-month file."""
    if not path.exists():
        return {}
    out = {}
    with path.open(newline="") as fh:
        for row in csv.reader(fh):
            if len(row) < 7:
                continue
            geoid = to_geoid(row[1].strip(), row[2])
            if geoid is None:
                continue
            try:
                out[geoid] = [float(v) for v in row[6:]]
            except ValueError:
                continue
    return out


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--start", type=int, default=1995)
    parser.add_argument("--end", type=int, default=2024)
    args = parser.parse_args()

    if not DATA_DIR.exists():
        print(f"error: {DATA_DIR} not found - run download_nclimgrid.py first")
        return 1

    pleasant = defaultdict(int)
    valid = defaultdict(int)
    names = {}
    months_seen = 0
    months_missing = []

    for year in range(args.start, args.end + 1):
        for month in range(1, 13):
            stamp = f"{year}{month:02d}"
            tmax = read_month(DATA_DIR / f"tmax-{stamp}-cty-scaled.csv")
            tmin = read_month(DATA_DIR / f"tmin-{stamp}-cty-scaled.csv")
            prcp = read_month(DATA_DIR / f"prcp-{stamp}-cty-scaled.csv")
            if not (tmax and tmin and prcp):
                months_missing.append(stamp)
                continue
            months_seen += 1

            for geoid, highs in tmax.items():
                lows = tmin.get(geoid)
                rain = prcp.get(geoid)
                if lows is None or rain is None:
                    continue
                for hi, lo, pr in zip(highs, lows, rain):
                    if hi <= MISSING or lo <= MISSING or pr <= MISSING:
                        continue
                    valid[geoid] += 1
                    if (
                        TMAX_MIN_C <= hi <= TMAX_MAX_C
                        and TMIN_MIN_C <= lo <= TMIN_MAX_C
                        and pr < PRCP_MAX_MM
                    ):
                        pleasant[geoid] += 1
        print(f"  processed {year}", flush=True)

    if not valid:
        print("error: no usable data found")
        return 1

    # Read county names from any one month rather than carrying them through
    # the hot loop.
    for year in range(args.start, args.end + 1):
        probe = DATA_DIR / f"tmax-{year}07-cty-scaled.csv"
        if probe.exists():
            with probe.open(newline="") as fh:
                for row in csv.reader(fh):
                    if len(row) > 2:
                        geoid = to_geoid(row[1].strip(), row[2])
                        if geoid:
                            names[geoid] = row[2].strip()
            break

    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    rows = []
    for geoid in sorted(valid):
        days = valid[geoid]
        rate = pleasant[geoid] / days * DAYS_PER_YEAR
        rows.append(
            {
                "GEOID": geoid,
                "name": names.get(geoid, ""),
                "pleasant_days": round(rate, 1),
                "valid_days": days,
            }
        )

    with OUT_PATH.open("w", newline="") as fh:
        writer = csv.DictWriter(
            fh, fieldnames=["GEOID", "name", "pleasant_days", "valid_days"]
        )
        writer.writeheader()
        writer.writerows(rows)

    values = sorted(r["pleasant_days"] for r in rows)
    print(f"\n{len(rows)} counties, {months_seen} months processed")
    if months_missing:
        print(f"missing months ({len(months_missing)}): {months_missing[:12]}")
    print(f"min  {values[0]:.1f}")
    print(f"med  {values[len(values) // 2]:.1f}")
    print(f"max  {values[-1]:.1f}")

    best = sorted(rows, key=lambda r: -r["pleasant_days"])[:10]
    worst = sorted(rows, key=lambda r: r["pleasant_days"])[:10]
    print("\nmost pleasant:")
    for r in best:
        print(f"  {r['pleasant_days']:6.1f}  {r['name']}")
    print("least pleasant:")
    for r in worst:
        print(f"  {r['pleasant_days']:6.1f}  {r['name']}")
    print(f"\nwrote {OUT_PATH}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
