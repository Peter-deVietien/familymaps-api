"""
Download natality data from CDC WONDER API.

The API only supports national-level queries. For state/county data,
you must use the web interface manually.

Databases:
  D10  = Natality 1995-2002
  D27  = Natality 2003-2006
  D66  = Natality 2007-2024
  D149 = Natality 2016-2024 (Expanded)

Source: https://wonder.cdc.gov/natality.html
API docs: https://wonder.cdc.gov/wonder/help/wonder-api.html
"""

import csv
import os
import time
import xml.etree.ElementTree as ET

import requests

RAW_DIR = os.path.join(os.path.dirname(__file__), "raw-data")
API_URL = "https://wonder.cdc.gov/controller/datarequest/{db_id}"

DATABASES = {
    "D66": {"name": "Natality 2007-2024", "years": list(range(2007, 2025))},
    "D27": {"name": "Natality 2003-2006", "years": list(range(2003, 2007))},
    "D10": {"name": "Natality 1995-2002", "years": list(range(1995, 2003))},
}


def build_natality_xml(db_id, years):
    """
    Build a CDC WONDER API request for natality data.
    Groups by Year and Mother's Race, requesting birth counts.
    """
    year_strs = [str(y) for y in years]

    # Variable mapping per database (natality-specific)
    # D66 (2007-2024): V1=Year, V42=Single Race 6, V43=Hispanic Origin
    # D27 (2003-2006): V1=Year, V8=Bridged Race 4, V43=Hispanic Origin
    # D10 (1995-2002): V1=Year, V8=Race 8, V16=Hispanic Origin
    if db_id == "D66":
        race_var = "V42"
        hisp_var = "V43"
    elif db_id == "D27":
        race_var = "V8"
        hisp_var = "V43"
    else:  # D10
        race_var = "V8"
        hisp_var = "V16"

    params = [
        # Group by Year, Race, Hispanic Origin
        ("B_1", f"{db_id}.V1-level1"),
        ("B_2", f"{db_id}.{race_var}"),
        ("B_3", f"{db_id}.{hisp_var}"),
        ("B_4", "*None*"),
        ("B_5", "*None*"),

        # Measures: M1 = Birth Count
        ("M_1", f"{db_id}.M1"),

        # Finder modes
        ("O_V1_fmode", "freg"),

        # Display options
        ("O_show_suppressed", "true"),
        ("O_show_totals", "true"),
        ("O_show_zeros", "true"),
        ("O_timeout", "600"),
        ("O_precision", "0"),

        # Required metadata
        ("action-Send", "Send"),
        ("dataset_code", db_id),
        ("stage", "request"),

        # Accept data use restrictions
        ("accept_datause_restrictions", "true"),
    ]

    # Add year finder values
    root = ET.Element("request-parameters")

    for name, value in params:
        param = ET.SubElement(root, "parameter")
        n = ET.SubElement(param, "name")
        n.text = name
        v = ET.SubElement(param, "value")
        v.text = value

    # Year selections (F_ = finder values)
    year_param = ET.SubElement(root, "parameter")
    n = ET.SubElement(year_param, "name")
    n.text = f"F_{db_id}.V1"
    for y in year_strs:
        v = ET.SubElement(year_param, "value")
        v.text = y

    # Year labels (I_ = currently selected info)
    year_info = ET.SubElement(root, "parameter")
    n = ET.SubElement(year_info, "name")
    n.text = f"I_{db_id}.V1"
    v = ET.SubElement(year_info, "value")
    v.text = "\n".join(f"{y} ({y})" for y in year_strs) + "\n"

    return ET.tostring(root, encoding="unicode", xml_declaration=True)


def query_wonder(db_id, request_xml):
    """Send a query to CDC WONDER API."""
    url = API_URL.format(db_id=db_id)
    resp = requests.post(
        url,
        data={"request_xml": request_xml, "accept_datause_restrictions": "true"},
        timeout=120,
    )
    resp.raise_for_status()
    return resp.text


def parse_response(response_xml):
    """Parse CDC WONDER XML response into rows of dicts."""
    root = ET.fromstring(response_xml)
    rows = []

    data_table = root.find(".//data-table")
    if data_table is None:
        return rows

    for r in data_table.findall("r"):
        row = {}
        for c in r.findall("c"):
            label = c.get("l", "")
            value = c.get("v", c.text or "")
            if label:
                row[label] = value
        if row:
            rows.append(row)

    return rows


def main():
    os.makedirs(RAW_DIR, exist_ok=True)

    all_rows = []
    for db_id, info in DATABASES.items():
        print(f"\n{'='*60}")
        print(f"Querying {info['name']} ({db_id})...")
        print(f"  Years: {info['years'][0]}-{info['years'][-1]}")

        xml = build_natality_xml(db_id, info["years"])

        # Save request for debugging
        req_path = os.path.join(RAW_DIR, f"request_{db_id}.xml")
        with open(req_path, "w") as f:
            f.write(xml)

        try:
            response = query_wonder(db_id, xml)

            # Save raw response
            resp_path = os.path.join(RAW_DIR, f"response_{db_id}.xml")
            with open(resp_path, "w") as f:
                f.write(response)

            rows = parse_response(response)
            if rows:
                for row in rows:
                    row["database"] = db_id
                    row["database_name"] = info["name"]
                all_rows.extend(rows)
                print(f"  Got {len(rows)} rows")
                print(f"  Sample: {rows[0]}")
            else:
                print(f"  No data rows parsed. Check {resp_path}")
                # Print any error message
                root = ET.fromstring(response)
                for msg in root.iter("message"):
                    print(f"  Message: {msg.text}")

        except requests.exceptions.HTTPError as e:
            print(f"  HTTP Error: {e}")
            print(f"  Request saved to {req_path}")
        except Exception as e:
            print(f"  Error: {e}")

        print("  Waiting 5s before next query (rate limit)...")
        time.sleep(5)

    if all_rows:
        fieldnames = list(dict.fromkeys(k for row in all_rows for k in row))
        out_path = os.path.join(RAW_DIR, "cdc_wonder_national_births.csv")
        with open(out_path, "w", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
            writer.writeheader()
            writer.writerows(all_rows)
        print(f"\nSaved {len(all_rows)} rows to {out_path}")
    else:
        print("\nNo data retrieved.")

    print("\n" + "="*60)
    print("NOTE: CDC WONDER API is NATIONAL-LEVEL ONLY.")
    print("For state/county data, manually query the web interface:")
    print("  https://wonder.cdc.gov/natality-current.html")
    print("  Group by: Year, State, Mother's Race, Hispanic Origin")
    print("  Export tab-delimited results to data/cdc_wonder/raw-data/")


if __name__ == "__main__":
    main()
