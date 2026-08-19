#!/usr/bin/env python3
"""Download NOAA nClimGrid-Daily county area-average CSVs.

Fetches daily max temp, min temp and precipitation aggregated to county
polygons by NCEI, so no zonal statistics are needed on our side.

Source: https://www.ncei.noaa.gov/data/nclimgrid-daily/access/averages/
Coverage: 3,107 CONUS counties (no Alaska, no Hawaii), 1951-present.

Usage:
    python3 scripts/download_nclimgrid.py [--start 1995] [--end 2024]
"""

import argparse
import sys
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

BASE_URL = "https://www.ncei.noaa.gov/data/nclimgrid-daily/access/averages"
VARIABLES = ("tmax", "tmin", "prcp")
OUT_DIR = Path(__file__).resolve().parent.parent / "data" / "nclimgrid"

# NCEI throttles aggressive clients; 8 workers downloads ~1GB in a few minutes
# without tripping it.
MAX_WORKERS = 8
TIMEOUT = 120


def targets(start_year: int, end_year: int) -> list[tuple[str, Path]]:
    jobs = []
    for year in range(start_year, end_year + 1):
        for month in range(1, 13):
            for var in VARIABLES:
                name = f"{var}-{year}{month:02d}-cty-scaled.csv"
                jobs.append((f"{BASE_URL}/{year}/{name}", OUT_DIR / name))
    return jobs


def fetch(url: str, dest: Path) -> tuple[Path, str]:
    if dest.exists() and dest.stat().st_size > 0:
        return dest, "cached"
    try:
        with urllib.request.urlopen(url, timeout=TIMEOUT) as resp:
            payload = resp.read()
    except urllib.error.HTTPError as exc:
        return dest, f"http {exc.code}"
    except Exception as exc:  # noqa: BLE001 - report and continue
        return dest, f"error {exc}"

    # Write via a temp file so an interrupted run never leaves a partial CSV
    # that a later resume would treat as complete.
    tmp = dest.with_suffix(".part")
    tmp.write_bytes(payload)
    tmp.rename(dest)
    return dest, "ok"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--start", type=int, default=1995)
    parser.add_argument("--end", type=int, default=2024)
    args = parser.parse_args()

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    jobs = targets(args.start, args.end)
    print(f"nClimGrid-Daily county averages {args.start}-{args.end}")
    print(f"{len(jobs)} files -> {OUT_DIR}")

    counts = {"ok": 0, "cached": 0, "failed": 0}
    failures = []

    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as pool:
        futures = {pool.submit(fetch, url, dest): dest for url, dest in jobs}
        for i, future in enumerate(as_completed(futures), 1):
            dest, status = future.result()
            if status in ("ok", "cached"):
                counts[status] += 1
            else:
                counts["failed"] += 1
                failures.append(f"{dest.name}: {status}")
            if i % 100 == 0 or i == len(jobs):
                print(
                    f"  {i}/{len(jobs)}  ok={counts['ok']} "
                    f"cached={counts['cached']} failed={counts['failed']}",
                    flush=True,
                )

    print(f"\ndone: {counts['ok']} downloaded, {counts['cached']} cached, "
          f"{counts['failed']} failed")
    if failures:
        print("failures:")
        for line in failures[:20]:
            print(f"  {line}")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
