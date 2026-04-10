#!/usr/bin/env python3
"""
Download CDC WONDER D149 (Expanded Natality 2016-2024) data with father's race.

Query: Group by Year × State × Father's Race 6 × Father's Hispanic Origin
Filter: Mother's Race = White, Mother's Hispanic Origin = Not Hispanic

This gives us the breakdown of father's race/ethnicity for births to WNH mothers,
from which we can compute the both-parent WNH birth count.

Usage:
    pip install playwright
    playwright install chromium
    python3 download_d149_father_race.py
"""

import os
import time
from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeout


def log(msg):
    print(msg, flush=True)


RAW_DIR = os.path.join(os.path.dirname(__file__), "raw-data")

D149_URL = "https://wonder.cdc.gov/natality-expanded-current.html"

# Variable codes discovered from form inspection
YEAR_VAR = "D149.V20"
STATE_VAR = "D149.V21-level1"
FATHER_RACE_VAR = "D149.V54"       # Father's Single Race 6
FATHER_HISP_VAR = "D149.V53"       # Father's Hispanic Origin

# Filter values
MOTHER_RACE_WHITE = "2106-3"       # White
MOTHER_HISP_NOT_HISP = "2186-5"    # Not Hispanic or Latino


def query_d149(page, max_retries=3):
    """Query D149 with father's race breakdown for WNH mothers."""
    log(f"\n{'='*60}")
    log("Querying D149 Expanded Natality 2016-2024...")
    log("  Group by: Year × State × Father's Race 6 × Father's Hispanic Origin")
    log("  Filter: Mother = White + Not Hispanic")

    for attempt in range(max_retries):
        try:
            log(f"\n  Attempt {attempt + 1}/{max_retries}...")

            page.goto(D149_URL, wait_until="domcontentloaded", timeout=30000)
            time.sleep(3)

            agree_btn = page.query_selector("input[value='I Agree']")
            if agree_btn:
                agree_btn.click()
                log("  Accepted data use restrictions")
                time.sleep(3)

            page.wait_for_selector("select[name='B_1']", timeout=30000)
            log("  Form loaded, configuring query...")

            # Group By: Year × State × Father's Race 6 × Father's Hispanic
            page.select_option("select[name='B_1']", value=YEAR_VAR)
            time.sleep(0.3)
            page.select_option("select[name='B_2']", value=STATE_VAR)
            time.sleep(0.3)
            page.select_option("select[name='B_3']", value=FATHER_RACE_VAR)
            time.sleep(0.3)
            page.select_option("select[name='B_4']", value=FATHER_HISP_VAR)
            time.sleep(0.3)
            log("  Group-by: Year × State × Father Race 6 × Father Hispanic Origin")

            # Select all years (D149 defaults to most recent year only)
            page.evaluate(f"""() => {{
                const sel = document.querySelector("select[name='V_{YEAR_VAR}']");
                if (sel) {{
                    for (const opt of sel.options) {{
                        if (opt.value === '*All*') {{
                            opt.selected = true;
                        }} else {{
                            opt.selected = false;
                        }}
                    }}
                    sel.dispatchEvent(new Event('change', {{bubbles: true}}));
                }}
            }}""")
            time.sleep(0.5)
            log("  Selected all years")

            # Filter: Mother's Race = White
            page.evaluate(f"""() => {{
                const sel = document.querySelector("select[name='V_D149.V42']");
                if (sel) {{
                    for (const opt of sel.options) {{
                        opt.selected = (opt.value === '{MOTHER_RACE_WHITE}');
                    }}
                    sel.dispatchEvent(new Event('change', {{bubbles: true}}));
                }}
            }}""")
            time.sleep(0.3)
            log("  Filtered Mother's Race = White")

            # Filter: Mother's Hispanic Origin = Not Hispanic or Latino
            page.evaluate(f"""() => {{
                const sel = document.querySelector("select[name='V_D149.V43']");
                if (sel) {{
                    for (const opt of sel.options) {{
                        opt.selected = (opt.value === '{MOTHER_HISP_NOT_HISP}');
                    }}
                    sel.dispatchEvent(new Event('change', {{bubbles: true}}));
                }}
            }}""")
            time.sleep(0.3)
            log("  Filtered Mother's Hispanic = Not Hispanic or Latino")

            # Check "Show Zero Values" and "Show Suppressed Values" in quick options
            zero_cb = page.query_selector("input[name='O_show_zeros']")
            if zero_cb:
                zero_cb.check()
                log("  Checked Show Zero Values")

            supp_cb = page.query_selector("input[name='O_show_suppressed']")
            if supp_cb:
                supp_cb.check()
                log("  Checked Show Suppressed Values")

            log("  Clicking Send (waiting for navigation, may take minutes)...")
            with page.expect_navigation(timeout=600000, wait_until="domcontentloaded"):
                page.click("input#submit-button1")
            log("  Navigation complete, waiting for results...")
            time.sleep(10)

            page.screenshot(path=os.path.join(RAW_DIR, "results_D149_father.png"))

            # Try Export first
            export_btn = page.query_selector("input[value='Export']")
            if export_btn:
                log("  Clicking Export button...")
                with page.expect_download(timeout=120000) as dl:
                    export_btn.click()
                download = dl.value
                dest = os.path.join(RAW_DIR, "cdc_wonder_D149_wnh_mother_by_father_race.txt")
                download.save_as(dest)
                size_kb = os.path.getsize(dest) / 1024
                log(f"  SUCCESS (exported): {dest} ({size_kb:.0f} KB)")
                return True

            log("  Export button not found, trying table scrape...")
            return scrape_table(page)

        except PlaywrightTimeout as e:
            log(f"  Timeout on attempt {attempt + 1}: {str(e)[:150]}")
            page.screenshot(path=os.path.join(RAW_DIR, f"timeout_D149_father_{attempt}.png"))
            if attempt < max_retries - 1:
                log("  Waiting 30s before retry...")
                time.sleep(30)

        except Exception as e:
            log(f"  Error on attempt {attempt + 1}: {str(e)[:150]}")
            page.screenshot(path=os.path.join(RAW_DIR, f"error_D149_father_{attempt}.png"))
            if attempt < max_retries - 1:
                time.sleep(30)

    log(f"  FAILED after {max_retries} attempts")
    return False


def scrape_table(page):
    """Scrape the data table from the results page."""
    log("  Extracting table data from page...")

    data = page.evaluate("""() => {
        const tables = document.querySelectorAll('table');
        let best = null;
        let bestRows = 0;
        for (const table of tables) {
            const rows = table.querySelectorAll('tr');
            if (rows.length > bestRows) {
                bestRows = rows.length;
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
                rowData.push(cell.innerText.trim());
            }
            if (rowData.length > 0 && rowData.some(c => c !== '')) {
                result.push(rowData);
            }
        }
        return result;
    }""")

    if not data or len(data) < 2:
        log("  ERROR: Could not find data table on results page")
        page.screenshot(path=os.path.join(RAW_DIR, "error_D149_no_table.png"))
        return False

    dest = os.path.join(RAW_DIR, "cdc_wonder_D149_wnh_mother_by_father_race.txt")
    with open(dest, "w") as f:
        for row in data:
            f.write("\t".join(row) + "\n")

    log(f"  SUCCESS (scraped): {dest} ({len(data)-1} data rows)")
    return True


def main():
    os.makedirs(RAW_DIR, exist_ok=True)

    log("CDC WONDER D149 — Father's Race for WNH Mothers")
    log("=" * 60)
    log("Downloading births by Year × State × Father Race × Father Hispanic")
    log("Filtered to births where Mother = White Non-Hispanic")
    log("")

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            accept_downloads=True,
            viewport={"width": 1280, "height": 900},
        )
        page = context.new_page()

        success = query_d149(page)

        browser.close()

    if success:
        log("\nSUCCESS — Data downloaded. Run extract script next.")
    else:
        log("\nFAILED — Check screenshots in raw-data/")

    return 0 if success else 1


if __name__ == "__main__":
    exit(main())
