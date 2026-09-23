#!/usr/bin/env python3
"""Download county job counts (BLS QCEW) and business applications (Census BFS).

QCEW -- Quarterly Census of Employment and Wages. Annual-average employment for
every county, all industries and ownerships, counted where people work. It
covers jobs under unemployment insurance, so the self-employed are missing. The
"industry 10" slice returns every area in one file; county totals are
agglvl_code 70, own_code 0. A handful of small counties are suppressed in some
years (disclosure_code "N") and are written blank.

BFS -- Business Formation Statistics. Annual EIN applications by county, 2005
onward, from a single workbook. Counties with too few applications to publish
come through as a blank cell. County level only carries total applications,
not the "high-propensity" subset likely to hire, so registered-agent hubs
(Sheridan WY, Kent DE) read far above their real activity.

Neither source needs an API key.

Usage:
    python3 scripts/download_economy_data.py
"""

from __future__ import annotations

import csv
import io
import sys
import urllib.error
import urllib.request
import xml.etree.ElementTree as ET
import zipfile
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
OUT_DIR = REPO_ROOT / "data" / "extracted_data"
JOBS_OUTPUT = OUT_DIR / "county_jobs.csv"
APPS_OUTPUT = OUT_DIR / "county_business_apps.csv"

# Ten years apart, ending at the newest complete annual average.
JOBS_YEARS = (2015, 2025)
QCEW_URL = "https://data.bls.gov/cew/data/api/{year}/a/industry/10.csv"
BFS_URL = "https://www.census.gov/econ/bfs/xlsx/bfs_county_apps_annual.xlsx"

XLSX_NS = "{http://schemas.openxmlformats.org/spreadsheetml/2006/main}"
TIMEOUT = 120


def fetch(url: str) -> bytes:
    request = urllib.request.Request(url, headers={"User-Agent": "familymaps-api"})
    with urllib.request.urlopen(request, timeout=TIMEOUT) as response:
        return response.read()


def county_jobs(year: int) -> dict[str, int | None]:
    """County annual-average employment; None where BLS suppressed it."""
    text = fetch(QCEW_URL.format(year=year)).decode()
    jobs: dict[str, int | None] = {}
    for row in csv.DictReader(io.StringIO(text)):
        if row["agglvl_code"] != "70" or row["own_code"] != "0":
            continue
        # xx999 is BLS's "unknown or undefined county" bucket within a state.
        if row["area_fips"].endswith("999"):
            continue
        suppressed = bool(row["disclosure_code"])
        jobs[row["area_fips"]] = None if suppressed else int(row["annual_avg_emplvl"])
    return jobs


def xlsx_rows(payload: bytes) -> list[list[str | None]]:
    """Rows of the first sheet, read with the stdlib so no Excel dependency."""
    book = zipfile.ZipFile(io.BytesIO(payload))
    shared = [
        "".join(si.itertext())
        for si in ET.fromstring(book.read("xl/sharedStrings.xml")).findall(f"{XLSX_NS}si")
    ]
    rows = []
    sheet = ET.fromstring(book.read("xl/worksheets/sheet1.xml"))
    for row in sheet.iter(f"{XLSX_NS}row"):
        cells = []
        for cell in row.findall(f"{XLSX_NS}c"):
            value = cell.find(f"{XLSX_NS}v")
            if value is None:
                cells.append(None)
            elif cell.get("t") == "s":
                cells.append(shared[int(value.text)])
            else:
                cells.append(value.text)
        rows.append(cells)
    return rows


def business_apps() -> tuple[list[str], list[dict]]:
    rows = xlsx_rows(fetch(BFS_URL))
    # A title block sits above the real header row.
    header_at = next(i for i, r in enumerate(rows) if r and r[0] == "State")
    header = rows[header_at]
    years = [h for h in header if h and h.startswith("BA")]

    counties = []
    for row in rows[header_at + 1:]:
        record = dict(zip(header, row))
        geoid = (record.get("County Code") or "").strip()
        if len(geoid) != 5:
            continue
        entry = {"GEOID": geoid, "county": record.get("County") or ""}
        for year in years:
            value = (record.get(year) or "").strip()
            entry[year] = value
        counties.append(entry)
    return years, counties


def main() -> int:
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    try:
        start, end = JOBS_YEARS
        by_year = {year: county_jobs(year) for year in JOBS_YEARS}
    except urllib.error.URLError as err:
        print(f"error: QCEW download failed: {err}")
        return 1

    geoids = sorted(set(by_year[start]) | set(by_year[end]))
    with JOBS_OUTPUT.open("w", newline="") as fh:
        writer = csv.writer(fh)
        writer.writerow(["GEOID", f"jobs_{start}", f"jobs_{end}"])
        for geoid in geoids:
            writer.writerow([
                geoid,
                *("" if by_year[y].get(geoid) is None else by_year[y][geoid] for y in JOBS_YEARS),
            ])
    for year in JOBS_YEARS:
        suppressed = sum(1 for v in by_year[year].values() if v is None)
        print(f"QCEW {year}: {len(by_year[year])} counties, {suppressed} suppressed")
    print(f"wrote {JOBS_OUTPUT}")

    try:
        years, counties = business_apps()
    except urllib.error.URLError as err:
        print(f"error: BFS download failed: {err}")
        return 1

    with APPS_OUTPUT.open("w", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=["GEOID", "county", *years])
        writer.writeheader()
        writer.writerows(counties)
    print(f"\nBFS {years[0][2:]}-{years[-1][2:]}: {len(counties)} counties")
    print(f"wrote {APPS_OUTPUT}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
