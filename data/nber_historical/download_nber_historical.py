"""
Download NBER Vital Statistics of the US — Births 1940-1968.

Downloads the births_data.zip archive containing digitized tables from
historical Vital Statistics volumes, plus the documentation file.

Source: https://www.nber.org/research/data/vital-statistics-us-births-1940-1968
Data dir: https://data.nber.org/data/births/1940-1968/
"""

import os
import sys
import zipfile

import requests

RAW_DIR = os.path.join(os.path.dirname(__file__), "raw-data")

FILES = {
    "births_data.zip": "https://data.nber.org/data/births/1940-1968/births_data.zip",
    "natality_documentation_all.xls": "https://data.nber.org/data/births/1940-1968/natality_documentation_all.xls",
    "natality_documentation_all.csv": "https://data.nber.org/data/births/1940-1968/natality_documentation_all.csv",
}


def download_file(url, dest_path, chunk_size=8192):
    """Download a file with progress reporting."""
    print(f"  Downloading {os.path.basename(dest_path)}...")
    print(f"    URL: {url}")

    resp = requests.get(url, stream=True, timeout=300)
    resp.raise_for_status()

    total = int(resp.headers.get("content-length", 0))
    downloaded = 0

    with open(dest_path, "wb") as f:
        for chunk in resp.iter_content(chunk_size=chunk_size):
            f.write(chunk)
            downloaded += len(chunk)
            if total:
                pct = downloaded / total * 100
                mb = downloaded / 1024 / 1024
                total_mb = total / 1024 / 1024
                print(f"\r    {mb:.1f} / {total_mb:.1f} MB ({pct:.0f}%)", end="", flush=True)

    print(f"\n    Saved to {dest_path} ({downloaded / 1024 / 1024:.1f} MB)")
    return dest_path


def main():
    os.makedirs(RAW_DIR, exist_ok=True)

    for filename, url in FILES.items():
        dest = os.path.join(RAW_DIR, filename)
        if os.path.exists(dest):
            print(f"  Skipping {filename} (already exists)")
            continue
        try:
            download_file(url, dest)
        except Exception as e:
            print(f"  ERROR downloading {filename}: {e}")
            continue

    # Extract the zip file
    zip_path = os.path.join(RAW_DIR, "births_data.zip")
    extract_dir = os.path.join(RAW_DIR, "births_data")

    if os.path.exists(zip_path) and not os.path.exists(extract_dir):
        print(f"\nExtracting {zip_path}...")
        try:
            with zipfile.ZipFile(zip_path, "r") as zf:
                zf.extractall(RAW_DIR)
            print(f"  Extracted to {extract_dir}")

            # List the cleaned stata files
            cleaned_dir = None
            for root, dirs, files in os.walk(extract_dir):
                if "5_births_data-cleaned_stata" in root:
                    cleaned_dir = root
                    break
                for d in dirs:
                    if "cleaned_stata" in d:
                        cleaned_dir = os.path.join(root, d)

            if cleaned_dir and os.path.exists(cleaned_dir):
                dta_files = sorted([f for f in os.listdir(cleaned_dir) if f.endswith(".dta")])
                print(f"\n  Found {len(dta_files)} cleaned Stata files:")
                for f in dta_files:
                    size = os.path.getsize(os.path.join(cleaned_dir, f))
                    print(f"    {f} ({size / 1024:.0f} KB)")
        except zipfile.BadZipFile:
            print(f"  ERROR: {zip_path} is not a valid zip file")
    elif os.path.exists(extract_dir):
        print(f"\nAlready extracted: {extract_dir}")

    print("\nDone.")


if __name__ == "__main__":
    main()
