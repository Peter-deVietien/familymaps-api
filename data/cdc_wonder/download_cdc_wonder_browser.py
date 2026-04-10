"""
Download state-level natality data from CDC WONDER using Playwright browser automation.

The CDC WONDER API only supports national-level queries. This script uses browser
automation to submit queries through the web UI and export the results.

Usage:
    pip install playwright
    playwright install chromium
    python3 download_cdc_wonder_browser.py

Databases queried:
    D66: Natality 2007-2024 (Mother's Single Race + Hispanic Origin)
    D27: Natality 2003-2006 (Bridged Race + Hispanic Origin)
    D10: Natality 1995-2002 (Race + Hispanic Origin)
"""

import os
import time

from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeout


def log(msg):
    print(msg, flush=True)

RAW_DIR = os.path.join(os.path.dirname(__file__), "raw-data")

DATABASES = {
    "D66": {
        "url": "https://wonder.cdc.gov/natality-current.html",
        "name": "Natality 2007-2024",
        "year_value": "D66.V20",
        "state_value": "D66.V21-level1",
        "race_value": "D66.V42",
        "hisp_value": "D66.V43",
    },
    "D27": {
        "url": "https://wonder.cdc.gov/natality-v2006.html",
        "name": "Natality 2003-2006",
        "year_value": "D27.V20",
        "state_value": "D27.V21-level1",
        "race_value": "D27.V2",
        "hisp_value": "D27.V43",
    },
    "D10": {
        "url": "https://wonder.cdc.gov/natality-v2002.html",
        "name": "Natality 1995-2002",
        "year_value": "D10.V20",
        "state_value": "D10.V21-level1",
        "race_value": "D10.V2",
        "hisp_value": "D10.V4",
    },
}


def query_database(page, db_id, db_info, output_dir, max_retries=3):
    """Query a single CDC WONDER natality database via browser automation."""
    log(f"\n{'='*60}")
    log(f"Querying {db_info['name']} ({db_id})...")

    for attempt in range(max_retries):
        try:
            log(f"  Attempt {attempt + 1}/{max_retries}...")

            page.goto(db_info["url"], wait_until="domcontentloaded", timeout=30000)
            time.sleep(3)

            agree_btn = page.query_selector("input[value='I Agree']")
            if agree_btn:
                agree_btn.click()
                log("  Accepted data use restrictions")
                time.sleep(2)

            page.wait_for_selector("select[name='B_1']", timeout=30000)
            log("  Form loaded, configuring query...")

            page.select_option("select[name='B_1']", value=db_info["year_value"])
            time.sleep(0.3)
            page.select_option("select[name='B_2']", value=db_info["state_value"])
            time.sleep(0.3)
            page.select_option("select[name='B_3']", value=db_info["race_value"])
            time.sleep(0.3)
            page.select_option("select[name='B_4']", value=db_info["hisp_value"])
            time.sleep(0.3)
            log("  Group-by configured: Year × State × Race × Hispanic Origin")

            log("  Clicking Send (waiting for navigation)...")
            with page.expect_navigation(timeout=600000, wait_until="domcontentloaded"):
                page.click("input#submit-button1")
            log("  Navigation complete, waiting for page to render...")
            time.sleep(10)

            page.screenshot(path=os.path.join(output_dir, f"results_{db_id}.png"))

            export_btn = page.query_selector("input[value='Export']")
            if export_btn:
                log("  Clicking Export button...")
                with page.expect_download(timeout=120000) as dl:
                    export_btn.click()
                download = dl.value
                dest = os.path.join(output_dir, f"cdc_wonder_{db_id}_state_race_hisp.txt")
                download.save_as(dest)
                size_kb = os.path.getsize(dest) / 1024
                log(f"  SUCCESS (exported): {dest} ({size_kb:.0f} KB)")
                return True

            log("  Export button not found, trying table scrape...")
            return scrape_results_table(page, db_id, output_dir)

        except PlaywrightTimeout as e:
            log(f"  Timeout on attempt {attempt + 1}: {str(e)[:150]}")
            page.screenshot(path=os.path.join(output_dir, f"timeout_{db_id}_{attempt}.png"))
            if attempt < max_retries - 1:
                log("  Waiting 30s before retry...")
                time.sleep(30)

        except Exception as e:
            log(f"  Error on attempt {attempt + 1}: {str(e)[:150]}")
            page.screenshot(path=os.path.join(output_dir, f"error_{db_id}_{attempt}.png"))
            if attempt < max_retries - 1:
                time.sleep(30)

    log(f"  FAILED after {max_retries} attempts for {db_id}")
    return False


def scrape_results_table(page, db_id, output_dir):
    """Scrape the data table directly from the results HTML page."""
    log("  Extracting all table data from page...")

    data = page.evaluate("""() => {
        const tables = document.querySelectorAll('table');
        let best = null;
        let bestRows = 0;
        for (const table of tables) {
            const tds = table.querySelectorAll('td');
            if (tds.length > bestRows) {
                bestRows = tds.length;
                best = table;
            }
        }
        if (!best) return null;
        const rows = best.querySelectorAll('tr');
        const result = [];
        for (const row of rows) {
            const cells = row.querySelectorAll('td, th');
            const rowData = [];
            for (const cell of cells) {
                rowData.push(cell.textContent.trim());
            }
            if (rowData.length > 0 && rowData.some(c => c !== '')) {
                result.push(rowData);
            }
        }
        return result;
    }""")

    if not data or len(data) < 2:
        log("  ERROR: Could not find data table on results page")
        return False

    dest = os.path.join(output_dir, f"cdc_wonder_{db_id}_state_race_hisp.txt")
    with open(dest, "w") as f:
        for row in data:
            f.write("\t".join(row) + "\n")

    log(f"  SUCCESS (scraped): {dest} ({len(data)-1} data rows)")
    return True


def main():
    os.makedirs(RAW_DIR, exist_ok=True)

    log("CDC WONDER Natality — State-Level Browser Download")
    log("=" * 60)
    log("Downloading birth counts by Year x State x Race x Hispanic Origin")
    log("")

    results = {}

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            accept_downloads=True,
            viewport={"width": 1280, "height": 900},
        )
        page = context.new_page()

        for db_id, db_info in DATABASES.items():
            success = query_database(page, db_id, db_info, RAW_DIR)
            results[db_id] = success
            if success:
                log(f"  Waiting 120s before next database (rate limit)...")
                time.sleep(120)

        browser.close()

    log(f"\n{'='*60}")
    log("Summary:")
    for db_id, success in results.items():
        status = "OK" if success else "FAILED"
        log(f"  {status} {db_id}: {DATABASES[db_id]['name']}")

    return 0 if all(results.values()) else 1


if __name__ == "__main__":
    exit(main())
