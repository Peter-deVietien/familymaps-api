"""
Download vital statistics data from NHGIS (IPUMS).

NHGIS provides aggregate vital statistics tables at state and county levels,
compiled from historical sources spanning 1915-2007.

Requires a free IPUMS account and API key:
  1. Register at https://www.nhgis.org/ (free)
  2. Get API key from https://account.ipums.org/api_keys
  3. Set IPUMS_API_KEY environment variable or pass --api-key

Source: https://www.nhgis.org/
API docs: https://developer.ipums.org/docs/v2/apiprogram/apis/nhgis/

Key datasets:
  - 1915-1941 Vital Statistics (Birth Registration Area)
  - 1939-1959 Vital Statistics
  - 1959-1972 Vital Statistics
  - 1970-2007 Vital Statistics (USA Counties database)
"""

import argparse
import json
import os
import sys
import time

import requests
from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(__file__), "..", "..", ".env"))

RAW_DIR = os.path.join(os.path.dirname(__file__), "raw-data")
API_BASE = "https://api.ipums.org"
METADATA_URL = f"{API_BASE}/metadata"
EXTRACTS_URL = f"{API_BASE}/extracts"

BIRTH_TABLES = {
    "1915_1941_cVS": {
        "dataTables": ["NT001", "NT002"],
        "geogLevels": ["state", "county"],
        "years": ["*"],
        "desc": "1915-1941: Total births + births by race (place of occurrence)",
    },
    "1939_1959_cVS": {
        "dataTables": ["NT001", "NT002", "NT005", "NT006"],
        "geogLevels": ["state", "county"],
        "years": ["*"],
        "desc": "1939-1959: Total births + births by race (occurrence + residence)",
    },
    "1959_1972_cVS": {
        "dataTables": ["NT001", "NT002", "NT009", "NT010"],
        "geogLevels": ["state", "county"],
        "years": ["*"],
        "desc": "1959-1972: Total births + births by race (occurrence + residence)",
    },
    "1970_2007_cVS": {
        "dataTables": ["NT002"],
        "geogLevels": ["state", "county"],
        "years": ["*"],
        "desc": "1970-2007: Total births (no race breakdown available)",
    },
}


def get_api_key(args_key=None):
    key = args_key or os.environ.get("IPUMS_API_KEY")
    if not key:
        print("ERROR: IPUMS API key required.")
        print("  1. Register at https://www.nhgis.org/")
        print("  2. Get API key from https://account.ipums.org/api_keys")
        print("  3. Set IPUMS_API_KEY env var or use --api-key")
        sys.exit(1)
    return key


def api_get(url, api_key, params=None):
    headers = {"Authorization": api_key}
    resp = requests.get(url, headers=headers, params=params, timeout=120)
    resp.raise_for_status()
    return resp.json()


def api_post(url, api_key, data):
    headers = {"Authorization": api_key, "Content-Type": "application/json"}
    resp = requests.post(url, headers=headers, json=data, timeout=120)
    resp.raise_for_status()
    return resp.json()


def list_datasets(api_key):
    """List all NHGIS datasets related to vital statistics."""
    print("Fetching NHGIS dataset metadata...")
    url = f"{METADATA_URL}/datasets"
    params = {"collection": "nhgis", "version": "2"}
    data = api_get(url, api_key, params)

    vs_datasets = []
    for ds in data.get("data", data) if isinstance(data, dict) else data:
        name = ds.get("name", "")
        desc = ds.get("description", "")
        if any(term in desc.lower() or term in name.lower()
               for term in ["vital", "natality", "birth", "mortality"]):
            vs_datasets.append(ds)

    return vs_datasets


def list_tables_for_dataset(api_key, dataset_name):
    """List data tables in a specific dataset by fetching dataset detail."""
    url = f"{METADATA_URL}/datasets/{dataset_name}"
    params = {"collection": "nhgis", "version": "2"}
    dataset = api_get(url, api_key, params)
    return dataset.get("dataTables", [])


def submit_extract(api_key, datasets_config, description="Vital statistics extract"):
    """Submit an NHGIS extract request for one or more datasets."""
    datasets = {}
    for ds_name, config in datasets_config.items():
        ds_def = {
            "dataTables": config["dataTables"],
            "geogLevels": config["geogLevels"],
        }
        if "years" in config:
            ds_def["years"] = config["years"]
        datasets[ds_name] = ds_def

    extract_def = {
        "datasets": datasets,
        "dataFormat": "csv_no_header",
        "description": description,
    }

    url = f"{EXTRACTS_URL}/?collection=nhgis&version=2"
    print(f"Submitting extract request...")
    print(f"  Payload: {json.dumps(extract_def, indent=2)}")
    return api_post(url, api_key, extract_def)


def check_extract_status(api_key, extract_number):
    """Check status of a submitted extract."""
    url = f"{EXTRACTS_URL}/{extract_number}?collection=nhgis&version=2"
    return api_get(url, api_key)


def wait_for_extract(api_key, extract_number, poll_interval=30, max_wait=1800):
    """Poll until extract is completed or failed."""
    elapsed = 0
    while elapsed < max_wait:
        status = check_extract_status(api_key, extract_number)
        state = status.get("status", "unknown")
        print(f"  Extract #{extract_number}: {state} ({elapsed}s elapsed)")

        if state == "completed":
            return status
        elif state in ("failed", "canceled"):
            print(f"  Extract failed/canceled: {status.get('errors', {})}")
            return status

        time.sleep(poll_interval)
        elapsed += poll_interval

    print(f"  Timed out after {max_wait}s")
    return None


def download_extract(api_key, extract_number, dest_dir):
    """Download a completed extract."""
    status = check_extract_status(api_key, extract_number)
    state = status.get("status", "unknown")

    if state != "completed":
        print(f"  Extract #{extract_number} is '{state}', not 'completed'.")
        return False

    download_links = status.get("downloadLinks", {})
    if not download_links:
        print(f"  No download links found.")
        return False

    for link_name, link_info in download_links.items():
        if isinstance(link_info, dict):
            link_url = link_info.get("url", "")
            size_bytes = link_info.get("bytes", 0)
        else:
            link_url = link_info
            size_bytes = 0

        if not link_url:
            continue

        filename = f"nhgis_extract_{extract_number}_{link_name}.zip"
        dest = os.path.join(dest_dir, filename)

        size_str = f" ({size_bytes / 1024:.0f} KB)" if size_bytes else ""
        print(f"  Downloading {link_name}{size_str}...")
        headers = {"Authorization": api_key}
        resp = requests.get(link_url, headers=headers, stream=True, timeout=600)
        resp.raise_for_status()

        with open(dest, "wb") as f:
            for chunk in resp.iter_content(chunk_size=65536):
                f.write(chunk)
        actual_size = os.path.getsize(dest)
        print(f"    Saved: {dest} ({actual_size / 1024:.0f} KB)")

    return True


def download_all(api_key):
    """Submit and download all vital statistics birth tables."""
    os.makedirs(RAW_DIR, exist_ok=True)

    print("=" * 60)
    print("NHGIS Vital Statistics — Download All Birth Tables")
    print("=" * 60)
    print()
    print("Datasets and tables to request:")
    for ds_name, config in BIRTH_TABLES.items():
        print(f"  {ds_name}: {config['desc']}")
        print(f"    Tables: {config['dataTables']}")
        print(f"    Geo levels: {config['geogLevels']}")
    print()

    result = submit_extract(api_key, BIRTH_TABLES,
                            description="Birth counts by race, all VS datasets, state+county")
    extract_num = result.get("number")
    print(f"\n  Extract submitted: #{extract_num}")
    print(f"  Status: {result.get('status')}")

    with open(os.path.join(RAW_DIR, "nhgis_extract_submission.json"), "w") as f:
        json.dump(result, f, indent=2)

    print(f"\nWaiting for extract to complete (polling every 30s)...")
    final = wait_for_extract(api_key, extract_num)

    if final and final.get("status") == "completed":
        print(f"\nExtract #{extract_num} completed! Downloading...")
        download_extract(api_key, extract_num, RAW_DIR)
        print("\nDone!")
        return True
    else:
        print(f"\nExtract not completed. Check status manually:")
        print(f"  python3 download_nhgis.py --check {extract_num}")
        print(f"  python3 download_nhgis.py --download {extract_num}")
        return False


def main():
    parser = argparse.ArgumentParser(description="Download NHGIS vital statistics data")
    parser.add_argument("--api-key", help="IPUMS API key")
    parser.add_argument("--list-datasets", action="store_true",
                        help="List available vital statistics datasets")
    parser.add_argument("--list-tables", metavar="DATASET",
                        help="List tables in a specific dataset")
    parser.add_argument("--download-all", action="store_true",
                        help="Submit and download all birth tables (all 4 VS datasets)")
    parser.add_argument("--check", metavar="EXTRACT_NUM", type=int,
                        help="Check status of an extract")
    parser.add_argument("--download", metavar="EXTRACT_NUM", type=int,
                        help="Download a completed extract")
    args = parser.parse_args()

    api_key = get_api_key(args.api_key)
    os.makedirs(RAW_DIR, exist_ok=True)

    if args.list_datasets:
        datasets = list_datasets(api_key)
        if not datasets:
            print("No vital statistics datasets found.")
            return
        print(f"\nFound {len(datasets)} vital statistics datasets:\n")
        for ds in datasets:
            name = ds.get("name", "unknown")
            desc = ds.get("description", "")
            group = ds.get("group", "")
            print(f"  {name}: {desc} ({group})")
        out_path = os.path.join(RAW_DIR, "nhgis_datasets.json")
        with open(out_path, "w") as f:
            json.dump(datasets, f, indent=2)
        print(f"\nSaved to {out_path}")

    elif args.list_tables:
        tables = list_tables_for_dataset(api_key, args.list_tables)
        print(f"\nTables in {args.list_tables}:\n")
        for t in (tables if isinstance(tables, list) else [tables]):
            print(f"  {t.get('name', '?')}: {t.get('description', '')} "
                  f"(universe={t.get('universe', '?')}, vars={t.get('nVariables', '?')})")

    elif args.download_all:
        download_all(api_key)

    elif args.check:
        status = check_extract_status(api_key, args.check)
        print(f"Extract {args.check}:")
        print(f"  Status: {status.get('status')}")
        dl = status.get("downloadLinks", {})
        if dl:
            for name, info in dl.items():
                if isinstance(info, dict):
                    print(f"  {name}: {info.get('bytes', 0) / 1024:.0f} KB")
        print(f"\nFull response:\n{json.dumps(status, indent=2)}")

    elif args.download:
        download_extract(api_key, args.download, RAW_DIR)

    else:
        print("NHGIS (IPUMS) Vital Statistics Downloader")
        print("=" * 50)
        print()
        print("Usage:")
        print("  python3 download_nhgis.py --list-datasets")
        print("  python3 download_nhgis.py --list-tables DATASET_NAME")
        print("  python3 download_nhgis.py --download-all        # submit + wait + download")
        print("  python3 download_nhgis.py --check EXTRACT_NUM")
        print("  python3 download_nhgis.py --download EXTRACT_NUM")
        print()
        print("Birth tables to be downloaded (--download-all):")
        for ds_name, config in BIRTH_TABLES.items():
            print(f"  {ds_name}: {config['dataTables']} — {config['desc']}")


if __name__ == "__main__":
    main()
