"""
Download NCHS Vital Statistics Online birth data files.

Downloads public-use birth data files (.zip) and user guides (.pdf) from
the CDC/NCHS FTP server.

Source: https://www.cdc.gov/nchs/data_access/vitalstatsonline.htm
FTP: https://ftp.cdc.gov/pub/Health_Statistics/NCHS/Datasets/DVS/natality/
Docs: https://ftp.cdc.gov/pub/Health_Statistics/NCHS/Dataset_Documentation/DVS/natality/

These are the same underlying data as NBER microdata, but in raw flat-file format.
Prefer NBER CSV files for easier processing (see ../nber_microdata/).
This script is useful for:
  - Getting user guides / documentation
  - Getting 2023-2024 data (which may not yet be on NBER)
  - Verifying data against NBER's repackaged versions
"""

import argparse
import os

import requests

RAW_DIR = os.path.join(os.path.dirname(__file__), "raw-data")

DATA_BASE = "https://ftp.cdc.gov/pub/Health_Statistics/NCHS/Datasets/DVS/natality"
DOCS_BASE = "https://ftp.cdc.gov/pub/Health_Statistics/NCHS/Dataset_Documentation/DVS/natality"


def build_file_list(years, docs_only=False):
    """Build list of (url, filename) tuples to download."""
    files = []

    for year in years:
        # User guides
        guide_patterns = [
            f"UserGuide{year}.pdf",
            f"UserGuide{year}_addendum.pdf",
        ]
        for pattern in guide_patterns:
            url = f"{DOCS_BASE}/{pattern}"
            files.append((url, f"docs/{pattern}"))

        if docs_only:
            continue

        # Data files
        if year < 1994:
            files.append((f"{DATA_BASE}/Nat{year}.zip", f"Nat{year}.zip"))
            # Try alternate capitalization
            files.append((f"{DATA_BASE}/Nat{year}.ZIP", f"Nat{year}.ZIP"))
        else:
            files.append((f"{DATA_BASE}/Nat{year}us.zip", f"Nat{year}us.zip"))
            files.append((f"{DATA_BASE}/Nat{year}ps.zip", f"Nat{year}ps.zip"))
            # Try alternate capitalizations
            files.append((f"{DATA_BASE}/nat{year}us.zip", f"nat{year}us.zip"))
            files.append((f"{DATA_BASE}/Nat{year}US.zip", f"Nat{year}US.zip"))
            files.append((f"{DATA_BASE}/Nat{year}PS.zip", f"Nat{year}PS.zip"))

    return files


def download_file(url, dest_path, chunk_size=65536):
    """Download a file, return True if successful."""
    resp = requests.get(url, stream=True, timeout=300, allow_redirects=True)
    if resp.status_code == 404:
        return False
    resp.raise_for_status()

    total = int(resp.headers.get("content-length", 0))
    downloaded = 0

    os.makedirs(os.path.dirname(dest_path), exist_ok=True)

    with open(dest_path, "wb") as f:
        for chunk in resp.iter_content(chunk_size=chunk_size):
            f.write(chunk)
            downloaded += len(chunk)
            if total:
                pct = downloaded / total * 100
                mb = downloaded / 1024 / 1024
                total_mb = total / 1024 / 1024
                print(f"\r    {mb:.1f} / {total_mb:.1f} MB ({pct:.0f}%)", end="", flush=True)

    size_mb = downloaded / 1024 / 1024
    print(f"\n    Saved: {dest_path} ({size_mb:.1f} MB)")
    return True


def main():
    parser = argparse.ArgumentParser(description="Download NCHS birth data files")
    parser.add_argument("--years", nargs="+", type=int,
                        help="Specific years (default: 2023-2024 for data not on NBER)")
    parser.add_argument("--docs-only", action="store_true",
                        help="Download only user guide PDFs (no data files)")
    parser.add_argument("--all-docs", action="store_true",
                        help="Download user guides for all years 1968-2024")
    args = parser.parse_args()

    os.makedirs(RAW_DIR, exist_ok=True)

    if args.all_docs:
        years = list(range(1968, 2025))
        args.docs_only = True
    elif args.years:
        years = args.years
    else:
        # Default: only download years not available from NBER
        years = [2023, 2024]

    print(f"NCHS Vital Statistics Birth Data Downloader")
    print(f"Years: {years}")
    print(f"Download directory: {RAW_DIR}")
    if args.docs_only:
        print("Mode: Documentation only\n")
    else:
        print(f"NOTE: For 1968-2022, prefer NBER CSV files (../nber_microdata/).\n")

    file_list = build_file_list(years, docs_only=args.docs_only)
    downloaded_names = set()

    for url, filename in file_list:
        base_name = os.path.basename(filename).lower()
        if base_name in downloaded_names:
            continue

        dest = os.path.join(RAW_DIR, filename)
        if os.path.exists(dest):
            print(f"  Skipping {filename} (exists)")
            downloaded_names.add(base_name)
            continue

        print(f"  Trying {filename}...")
        try:
            if download_file(url, dest):
                downloaded_names.add(base_name)
            else:
                print(f"    Not found (404)")
        except Exception as e:
            print(f"    Error: {e}")
            if os.path.exists(dest):
                os.remove(dest)

    print("\nDone.")


if __name__ == "__main__":
    main()
