#!/usr/bin/env python3
"""
Download NBER Microdata for 1973-1994 and aggregate by state × race.

Streams each year's CSV file (474 MB - 2 GB) through memory,
aggregating birth counts by state FIPS × race category.
Raw files are never stored on disk.

Usage:
    python3 download_nber_microdata.py              # all years 1973-1994
    python3 download_nber_microdata.py 1975          # single year
    python3 download_nber_microdata.py 1975 1980 1990  # specific years

Output: data/nber_microdata/extracted_data.csv
"""

import csv
import io
import os
import sys
import time
import urllib.request
from collections import defaultdict

BASE = os.path.dirname(os.path.abspath(__file__))

FIPS_TO_STATE = {
    '01': 'Alabama', '02': 'Alaska', '04': 'Arizona', '05': 'Arkansas',
    '06': 'California', '08': 'Colorado', '09': 'Connecticut', '10': 'Delaware',
    '11': 'District of Columbia', '12': 'Florida', '13': 'Georgia', '15': 'Hawaii',
    '16': 'Idaho', '17': 'Illinois', '18': 'Indiana', '19': 'Iowa',
    '20': 'Kansas', '21': 'Kentucky', '22': 'Louisiana', '23': 'Maine',
    '24': 'Maryland', '25': 'Massachusetts', '26': 'Michigan', '27': 'Minnesota',
    '28': 'Mississippi', '29': 'Missouri', '30': 'Montana', '31': 'Nebraska',
    '32': 'Nevada', '33': 'New Hampshire', '34': 'New Jersey', '35': 'New Mexico',
    '36': 'New York', '37': 'North Carolina', '38': 'North Dakota', '39': 'Ohio',
    '40': 'Oklahoma', '41': 'Oregon', '42': 'Pennsylvania', '44': 'Rhode Island',
    '45': 'South Carolina', '46': 'South Dakota', '47': 'Tennessee', '48': 'Texas',
    '49': 'Utah', '50': 'Vermont', '51': 'Virginia', '53': 'Washington',
    '54': 'West Virginia', '55': 'Wisconsin', '56': 'Wyoming',
}

# NCHS alphabetical state codes (used in stateres for pre-1989 data).
# States are numbered 1-51 in alphabetical order (including DC between
# Delaware and Florida). Codes 52+ are territories.
_STATES_ALPHA = [
    'Alabama', 'Alaska', 'Arizona', 'Arkansas', 'California',
    'Colorado', 'Connecticut', 'Delaware', 'District of Columbia', 'Florida',
    'Georgia', 'Hawaii', 'Idaho', 'Illinois', 'Indiana',
    'Iowa', 'Kansas', 'Kentucky', 'Louisiana', 'Maine',
    'Maryland', 'Massachusetts', 'Michigan', 'Minnesota', 'Mississippi',
    'Missouri', 'Montana', 'Nebraska', 'Nevada', 'New Hampshire',
    'New Jersey', 'New Mexico', 'New York', 'North Carolina', 'North Dakota',
    'Ohio', 'Oklahoma', 'Oregon', 'Pennsylvania', 'Rhode Island',
    'South Carolina', 'South Dakota', 'Tennessee', 'Texas', 'Utah',
    'Vermont', 'Virginia', 'Washington', 'West Virginia', 'Wisconsin',
    'Wyoming',
]
NCHS_TO_STATE = {f'{i+1:02d}': st for i, st in enumerate(_STATES_ALPHA)}
# Also map single-digit versions
NCHS_TO_STATE.update({str(i+1): st for i, st in enumerate(_STATES_ALPHA)})


def clean_val(val):
    """Strip quotes and whitespace from a CSV value."""
    if val is None:
        return ''
    return val.strip().strip('"').strip()


def safe_int(val, default=None):
    """Parse an integer, returning default on failure."""
    val = clean_val(str(val)) if val is not None else ''
    if not val:
        return default
    try:
        return int(val)
    except (ValueError, TypeError):
        return default


def process_year(year):
    """Stream-download and aggregate one year of NBER microdata.
    Returns list of dicts (one per state) with aggregate birth counts.
    """
    url = f"https://data.nber.org/nvss/natality/csv/{year}/natality{year}us.csv"

    print(f"\n{'='*60}")
    print(f"Processing {year}...")
    print(f"  URL: {url}")

    start_time = time.time()

    use_mrace = (year >= 1980)
    race_col = 'mrace' if use_mrace else 'crace'
    has_origm = (year >= 1978)
    # stresfip (FIPS) available from 1989+; before that, stateres uses NCHS codes
    use_fips = (year >= 1989)

    # Counters: state_name -> {total, white, nonwhite, white_nh, white_hisp, white_hisp_unk}
    counts = defaultdict(lambda: defaultdict(int))

    row_count = 0
    error_count = 0
    bytes_read = 0

    try:
        req = urllib.request.Request(url, headers={
            'User-Agent': 'Mozilla/5.0 (research data download)'
        })
        with urllib.request.urlopen(req, timeout=600) as response:
            content_length = response.headers.get('Content-Length')
            file_size_mb = int(content_length) / 1048576 if content_length else 0
            print(f"  File size: {file_size_mb:.0f} MB")
            print(f"  State column: {'stresfip (FIPS)' if use_fips else 'stateres (NCHS alpha)'}")
            print(f"  Race column: {race_col} ({'mother' if use_mrace else 'child'})")
            hisp_field_name = 'ormoth' if use_fips else 'origm'
            print(f"  Hispanic origin: {hisp_field_name + ' (available)' if has_origm else 'not available'}")

            text_stream = io.TextIOWrapper(
                response, encoding='utf-8', errors='replace',
                newline=''
            )

            reader = csv.DictReader(text_stream)

            # Verify expected columns exist
            if reader.fieldnames:
                fields_lower = [f.strip().strip('"').lower() for f in reader.fieldnames]
                if race_col not in fields_lower and race_col.upper() not in [f.strip().strip('"') for f in reader.fieldnames]:
                    print(f"  Available columns: {reader.fieldnames[:30]}...")
                    print(f"  WARNING: Expected column '{race_col}' not found!")

            for row in reader:
                row_count += 1
                if row_count % 500000 == 0:
                    elapsed = time.time() - start_time
                    rate = row_count / elapsed if elapsed > 0 else 0
                    pct = (row_count / (file_size_mb * 5000)) * 100 if file_size_mb > 0 else 0
                    print(f"  ... {row_count:>10,} rows ({elapsed:>5.0f}s, "
                          f"{rate:,.0f} rows/s)")

                try:
                    if use_fips:
                        state_code = clean_val(row.get('stresfip', ''))
                        if len(state_code) == 1:
                            state_code = '0' + state_code
                        state_name = FIPS_TO_STATE.get(state_code)
                    else:
                        state_code = clean_val(row.get('stateres', ''))
                        state_name = NCHS_TO_STATE.get(state_code)

                    if not state_name:
                        continue

                    race_val = safe_int(row.get(race_col), default=-1)
                    weight = safe_int(row.get('recwt'), default=1)

                    if race_val < 0:
                        error_count += 1
                        continue

                    is_white = (race_val == 1)

                    counts[state_name]['total'] += weight
                    if is_white:
                        counts[state_name]['white'] += weight
                    else:
                        counts[state_name]['nonwhite'] += weight

                    if has_origm and is_white:
                        hisp_field = 'ormoth' if use_fips else 'origm'
                        origm_val = safe_int(row.get(hisp_field), default=99)
                        if origm_val == 0:
                            counts[state_name]['white_nh'] += weight
                        elif 1 <= origm_val <= 5:
                            counts[state_name]['white_hisp'] += weight
                        else:
                            counts[state_name]['white_hisp_unk'] += weight

                except Exception as e:
                    error_count += 1
                    if error_count <= 3:
                        print(f"  WARNING row {row_count}: {e}")

    except Exception as e:
        print(f"  ERROR downloading/processing {year}: {e}")
        import traceback
        traceback.print_exc()
        return []

    elapsed = time.time() - start_time
    rate = row_count / elapsed if elapsed > 0 else 0
    print(f"  Completed: {row_count:,} rows in {elapsed:.0f}s ({rate:,.0f} rows/s)")
    if error_count > 0:
        print(f"  Parse errors: {error_count}")

    # Convert to output rows
    race_basis = "mother's race" if use_mrace else "child's race"
    output_rows = []

    for state_name in sorted(counts.keys()):
        c = counts[state_name]
        total = c['total']
        white = c['white']
        nonwhite = c['nonwhite']

        white_nh = None
        hisp_note = "no Hispanic origin field"

        if has_origm:
            wnh = c.get('white_nh', 0)
            whisp = c.get('white_hisp', 0)
            wunk = c.get('white_hisp_unk', 0)

            # If >30% of white births have unknown Hispanic origin,
            # this state likely doesn't report it reliably
            if white > 0 and wunk > white * 0.3:
                hisp_note = f"Hispanic origin not reported in this state ({wunk}/{white} unknown)"
            elif white > 0:
                white_nh = wnh
                hisp_note = f"White NH from origm; {whisp} White Hispanic, {wunk} unknown"

        notes_parts = [race_basis]
        if white_nh is None:
            notes_parts.append("White includes Hispanic")
        notes_parts.append(hisp_note)

        pct_white = round(white / total * 100, 2) if total > 0 else ''
        pct_white_nh = round(white_nh / total * 100, 2) if white_nh is not None and total > 0 else ''

        race_type = 'White/Nonwhite'
        if has_origm and white_nh is not None:
            race_type += ' + Hispanic'

        output_rows.append({
            'year': year,
            'state': state_name,
            'source': 'NBER Microdata',
            'total_births': total,
            'white_births': white,
            'white_nh_births': white_nh if white_nh is not None else '',
            'nonwhite_births': nonwhite,
            'pct_white': pct_white,
            'pct_white_nh': pct_white_nh,
            'race_category_type': race_type,
            'notes': '; '.join(notes_parts),
        })

    print(f"  Output: {len(output_rows)} state rows for {year}")

    # Print a few sample rows for validation
    for row in output_rows[:3]:
        wnh_str = f", WNH={row['white_nh_births']}" if row['white_nh_births'] != '' else ''
        print(f"    {row['state']}: total={row['total_births']:,}, "
              f"white={row['white_births']:,} ({row['pct_white']}%){wnh_str}")

    return output_rows


def save_results(all_rows, out_path):
    """Save accumulated results to CSV."""
    fieldnames = [
        'year', 'state', 'source', 'total_births', 'white_births',
        'white_nh_births', 'nonwhite_births', 'pct_white', 'pct_white_nh',
        'race_category_type', 'notes'
    ]
    with open(out_path, 'w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(all_rows)


def main():
    years = list(range(1973, 1995))

    if len(sys.argv) > 1:
        years = [int(y) for y in sys.argv[1:]]

    print("NBER Microdata Streaming Aggregation")
    print(f"Years to process: {min(years)}-{max(years)} ({len(years)} years)")
    print(f"Streaming from: https://data.nber.org/nvss/natality/csv/")

    out_path = os.path.join(BASE, 'extracted_data.csv')
    all_rows = []

    # Load any existing results (for resuming interrupted runs)
    if os.path.exists(out_path):
        with open(out_path, 'r') as f:
            reader = csv.DictReader(f)
            existing = list(reader)
        existing_years = set(int(r['year']) for r in existing)
        all_rows = [r for r in existing if int(r['year']) not in set(years)]
        if existing_years - set(years):
            print(f"  Keeping {len(all_rows)} existing rows from years "
                  f"{sorted(existing_years - set(years))}")

    overall_start = time.time()

    for i, year in enumerate(years):
        print(f"\n[{i+1}/{len(years)}] Year {year}")
        year_rows = process_year(year)
        all_rows.extend(year_rows)

        # Sort and save after each year (incremental save for safety)
        all_rows.sort(key=lambda r: (int(r['year']), r['state']))
        save_results(all_rows, out_path)
        print(f"  Saved {len(all_rows)} total rows to {out_path}")

    overall_elapsed = time.time() - overall_start
    print(f"\n{'='*60}")
    print(f"DONE. {len(all_rows)} total rows for {len(years)} years "
          f"in {overall_elapsed:.0f}s ({overall_elapsed/60:.1f} min)")
    print(f"Output: {out_path}")


if __name__ == '__main__':
    main()
