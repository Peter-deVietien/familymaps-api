"""
Download births by race/ethnicity from KFF State Health Facts.

KFF renders data via an AngularJS app using ag-Grid. No public API exists.
This script uses Selenium to load each year's page and extracts data from
the ag-Grid DOM (cell values are in <span title="..."> attributes).

Source: https://www.kff.org/other/state-indicator/births-by-raceethnicity/
Coverage: 2016-2023, state-level only
"""

import csv
import json
import os
import time

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

RAW_DIR = os.path.join(os.path.dirname(__file__), "raw-data")
BASE_URL = "https://www.kff.org/other/state-indicator/births-by-raceethnicity/"

JS_EXTRACT_AG_GRID = """
var rows = document.querySelectorAll('div.ag-body div.ag-row');
var results = [];

// Get column IDs from header
var headerCells = document.querySelectorAll('div.ag-header-cell');
var colIds = [];
headerCells.forEach(function(h) {
    var cid = h.getAttribute('colid');
    if (cid) colIds.push(cid);
});

// Also get pinned location cells
var pinnedRows = document.querySelectorAll('div.ag-pinned-left-cols-container div.ag-row');
var bodyRows = document.querySelectorAll('div.ag-body-viewport div.ag-row');

// Map row index to location
var locationMap = {};
pinnedRows.forEach(function(row) {
    var rowIdx = row.getAttribute('row');
    var cell = row.querySelector('div[colid="Location"] span');
    if (cell) {
        locationMap[rowIdx] = cell.getAttribute('title') || cell.textContent.trim();
    }
});

// Extract data from body rows
bodyRows.forEach(function(row) {
    var rowIdx = row.getAttribute('row');
    var location = locationMap[rowIdx] || '';
    var rowData = {Location: location};

    var cells = row.querySelectorAll('div.ag-cell');
    cells.forEach(function(cell) {
        var colId = cell.getAttribute('colid');
        var span = cell.querySelector('span');
        var value = '';
        if (span) {
            value = span.getAttribute('title') || span.textContent.trim();
        }
        if (colId && colId !== 'Location') {
            rowData[colId] = value;
        }
    });

    if (location) results.push(rowData);
});

return JSON.stringify(results);
"""

JS_GET_TIMEFRAMES = """
var select = document.querySelector('select');
if (!select) return '[]';
var opts = [];
var options = select.querySelectorAll('option');
for (var i = 0; i < options.length; i++) {
    opts.push({value: options[i].value, label: options[i].textContent.trim()});
}
return JSON.stringify(opts);
"""

JS_DISMISS_POPUPS = """
document.querySelectorAll('iframe[class*="go8128"]').forEach(function(el) { el.remove(); });
document.querySelectorAll('.hs-overlay, .leadinModal').forEach(function(el) { el.style.display = 'none'; });
document.querySelectorAll('[class*="cookie-banner"]').forEach(function(el) { el.style.display = 'none'; });
"""

RACE_COLUMNS = [
    "White", "Black", "Hispanic", "Asian",
    "American Indian or Alaska Native",
    "Native Hawaiian or Pacific Islander",
    "More than one race", "Total"
]


def get_driver():
    options = Options()
    options.add_argument("--headless=new")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--window-size=1920,1080")
    driver = webdriver.Chrome(options=options)
    return driver


JS_SELECT_TIMEFRAME = """
var select = document.querySelector('select');
if (!select) return false;
select.value = arguments[0];
var event = new Event('change', { bubbles: true });
select.dispatchEvent(event);
return true;
"""

JS_GET_FIRST_DATA_VALUE = """
var cell = document.querySelector('div.ag-body-viewport div.ag-cell span');
return cell ? (cell.getAttribute('title') || cell.textContent.trim()) : '';
"""


def scrape_kff():
    os.makedirs(RAW_DIR, exist_ok=True)
    driver = get_driver()

    try:
        print("Loading KFF births by race/ethnicity page...")
        driver.get(BASE_URL)
        time.sleep(8)
        driver.execute_script(JS_DISMISS_POPUPS)

        timeframes = json.loads(driver.execute_script(JS_GET_TIMEFRAMES))
        if not timeframes:
            print("ERROR: Could not find timeframe dropdown.")
            return

        print(f"Found {len(timeframes)} timeframes: {[t['label'] for t in timeframes]}")

        all_rows = []
        for tf in timeframes:
            year_label = tf["label"]
            tf_value = tf["value"]
            print(f"  Scraping {year_label} (value={tf_value})...")

            driver.execute_script(JS_DISMISS_POPUPS)

            prev_val = driver.execute_script(JS_GET_FIRST_DATA_VALUE)

            changed = driver.execute_script(JS_SELECT_TIMEFRAME, tf_value)
            if not changed:
                print(f"    WARNING: Could not set timeframe for {year_label}")
                continue

            for wait_iter in range(20):
                time.sleep(1)
                new_val = driver.execute_script(JS_GET_FIRST_DATA_VALUE)
                if new_val and new_val != prev_val:
                    break
                if wait_iter == 0:
                    driver.execute_script(JS_DISMISS_POPUPS)
            else:
                if tf == timeframes[0]:
                    pass
                else:
                    print(f"    WARNING: Data may not have refreshed for {year_label}")

            time.sleep(2)

            try:
                WebDriverWait(driver, 15).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, "div.ag-row"))
                )
            except Exception:
                print(f"    WARNING: ag-Grid not found for {year_label}")
                continue

            table_json = driver.execute_script(JS_EXTRACT_AG_GRID)
            rows = json.loads(table_json)

            for row in rows:
                row["Year"] = year_label

            if rows:
                sample_loc = rows[0].get("Location", "?")
                sample_val = rows[0].get("White", "?")
                print(f"    Got {len(rows)} rows (sample: {sample_loc} White={sample_val})")

            all_rows.extend(rows)

        if all_rows:
            fieldnames = ["Year", "Location"] + RACE_COLUMNS
            for row in all_rows:
                for k in row:
                    if k not in fieldnames:
                        fieldnames.append(k)

            out_path = os.path.join(RAW_DIR, "kff_births_by_race_ethnicity.csv")
            with open(out_path, "w", newline="") as f:
                writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
                writer.writeheader()
                writer.writerows(all_rows)
            print(f"\nSaved {len(all_rows)} total rows to {out_path}")

            validate_kff_data(all_rows)
        else:
            print("\nNo data extracted.")

    finally:
        driver.quit()


def validate_kff_data(rows):
    """Check that different years have different data (catch the duplication bug)."""
    by_year = {}
    for row in rows:
        yr = row.get("Year", "")
        if row.get("Location") == "United States":
            by_year[yr] = row.get("White", "")

    unique_vals = set(by_year.values())
    if len(unique_vals) <= 1 and len(by_year) > 1:
        print("\n⚠️  WARNING: All years have identical US White values — scraper bug likely persists!")
        for yr, val in sorted(by_year.items()):
            print(f"    {yr}: US White = {val}")
    else:
        print(f"\n✅ Validation passed: {len(unique_vals)} distinct US White values across {len(by_year)} years")
        for yr, val in sorted(by_year.items()):
            print(f"    {yr}: US White = {val}")


if __name__ == "__main__":
    scrape_kff()
