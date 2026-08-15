#!/usr/bin/env python3
"""Augment the served demographics JSON with Asian and NHPI population counts.

Backfills the fields needed by the frontend's "White + Asian" toggle onto the
already-generated files in app/data/, joining on GEOID. Existing fields are
never removed, so this is safe to re-run.

Census tables used
------------------
B03002_007E  Native Hawaiian / Other Pacific Islander alone, not Hispanic.
             Pairs with B03002_006E (Asian alone, not Hispanic) which the
             demographics files already carry.

B01001D_003E / _018E  Asian alone under 5 (male / female)
B01001E_003E / _018E  NHPI alone under 5 (male / female)
             The B01001 race iterations have no "not Hispanic" variant, so
             these are race-alone counts of any ethnicity. About 2% of Asians
             identify as Hispanic, making this a close but not exact analogue
             to the B03002 figures used by the other layers.

Usage
-----
    python3 scripts/add_asian_nhpi_fields.py [--dry-run]

Requires CENSUS_API_KEY (or census_api_key) in the repo-root .env file.
"""

from __future__ import annotations

import argparse
import json
import sys
import urllib.parse
import urllib.request
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = REPO_ROOT / "app" / "data"
API_URL = "https://api.census.gov/data/2023/acs/acs5"

FLORIDA_FIPS = "12"

# Census sentinel for a suppressed / unavailable estimate.
MISSING = "-666666666"


def load_api_key() -> str:
    env_path = REPO_ROOT / ".env"
    if not env_path.exists():
        sys.exit(f"Missing {env_path}")

    for line in env_path.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        name, _, value = line.partition("=")
        if name.strip().lower() == "census_api_key" and value.strip():
            return value.strip()

    sys.exit("Missing CENSUS_API_KEY in .env — get one at api.census.gov/data/key_signup.html")


def census_get(variables: list[str], for_clause: str, in_clause: str | None, key: str) -> list[list[str]]:
    params = {"get": ",".join(variables), "for": for_clause, "key": key}
    if in_clause:
        params["in"] = in_clause
    url = f"{API_URL}?{urllib.parse.urlencode(params)}"

    with urllib.request.urlopen(url, timeout=180) as response:
        if response.status != 200:
            sys.exit(f"Census API returned {response.status} for {for_clause}")
        return json.loads(response.read().decode())


def to_int(value: str | None) -> int:
    if not value or value == MISSING:
        return 0
    try:
        return int(value)
    except ValueError:
        return 0


def build_geoid(row: list[str], headers: list[str], parts: list[str]) -> str:
    return "".join(row[headers.index(part)] for part in parts)


def fetch_counts(
    variables: dict[str, str],
    for_clause: str,
    in_clause: str | None,
    geoid_parts: list[str],
    key: str,
) -> dict[str, dict[str, int]]:
    """Return {GEOID: {field_name: count}} for the requested Census variables."""
    rows = census_get(list(variables), for_clause, in_clause, key)
    headers = rows[0]

    counts: dict[str, dict[str, int]] = {}
    for row in rows[1:]:
        geoid = build_geoid(row, headers, geoid_parts)
        counts[geoid] = {
            field: to_int(row[headers.index(code)]) for code, field in variables.items()
        }
    return counts


def merge_into_file(filename: str, counts: dict[str, dict[str, int]], derived, dry_run: bool) -> None:
    path = DATA_DIR / filename
    records = json.loads(path.read_text())

    matched = 0
    for record in records:
        values = counts.get(record["GEOID"])
        if values is None:
            # Keep the schema uniform so the frontend never sees undefined.
            values = {field: 0 for field in next(iter(counts.values()))}
        else:
            matched += 1
        record.update(values)
        if derived:
            record.update(derived(record))

    print(f"  {filename}: {matched}/{len(records)} records matched")

    if not dry_run:
        path.write_text(json.dumps(records))


def under5_derived(record: dict) -> dict:
    """Combined white + Asian + NHPI under-5 count and percentage."""
    combined = record["white_nh_under5"] + record["asian_under5"] + record["nhpi_under5"]
    total = record["total_under5"]
    return {
        "white_asian_under5": combined,
        "white_asian_under5_perc": round(combined / total * 100, 2) if total else 0,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dry-run", action="store_true", help="fetch and report without writing")
    args = parser.parse_args()

    key = load_api_key()

    nhpi_var = {"B03002_007E": "nhpi_non_hisp"}

    print("Fetching NHPI non-Hispanic counts (B03002_007E)...")

    print(" US counties")
    us_counties = fetch_counts(nhpi_var, "county:*", None, ["state", "county"], key)
    merge_into_file("US_county_demographics.json", us_counties, None, args.dry_run)

    fl_counties = {g: v for g, v in us_counties.items() if g.startswith(FLORIDA_FIPS)}
    merge_into_file("FL_county_demographics.json", fl_counties, None, args.dry_run)

    print(" FL tracts")
    fl_tracts = fetch_counts(
        nhpi_var, "tract:*", f"state:{FLORIDA_FIPS} county:*", ["state", "county", "tract"], key
    )
    merge_into_file("FL_tract_demographics.json", fl_tracts, None, args.dry_run)

    print(" FL block groups")
    fl_block_groups = fetch_counts(
        nhpi_var,
        "block group:*",
        f"state:{FLORIDA_FIPS} county:*",
        ["state", "county", "tract", "block group"],
        key,
    )
    merge_into_file("FL_block_group_demographics.json", fl_block_groups, None, args.dry_run)

    print("Fetching Asian / NHPI under-5 counts (B01001D, B01001E)...")
    under5 = fetch_counts(
        {
            "B01001D_003E": "asian_male_under5",
            "B01001D_018E": "asian_female_under5",
            "B01001E_003E": "nhpi_male_under5",
            "B01001E_018E": "nhpi_female_under5",
        },
        "county:*",
        None,
        ["state", "county"],
        key,
    )
    for values in under5.values():
        values["asian_under5"] = values["asian_male_under5"] + values["asian_female_under5"]
        values["nhpi_under5"] = values["nhpi_male_under5"] + values["nhpi_female_under5"]

    merge_into_file("US_county_under5_demographics.json", under5, under5_derived, args.dry_run)

    if args.dry_run:
        print("Dry run — no files written.")
    else:
        print("Done. Commit app/data/ and redeploy.")


if __name__ == "__main__":
    main()
