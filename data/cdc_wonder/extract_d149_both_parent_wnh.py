#!/usr/bin/env python3
"""
Extract both-parent WNH birth counts from D149 (Expanded Natality 2016-2024).

Input: raw-data/cdc_wonder_D149_wnh_mother_by_father_race.txt
  (Year × State × Father's Race 6 × Father's Hispanic, filtered to WNH mothers)

Output: extracted_d149_both_parent_wnh.csv
  Columns: year, state, total_wnh_mother, both_parent_wnh, father_unknown,
           father_non_wnh, pct_both_parent_of_total, pct_father_unknown

Also compares to our existing mother-only WNH data to show the gap.
"""

import os
import re
import csv
from collections import defaultdict

BASE = os.path.dirname(os.path.abspath(__file__))

STATE_NAME_MAP = {
    "Alabama": "Alabama", "Alaska": "Alaska", "Arizona": "Arizona",
    "Arkansas": "Arkansas", "California": "California", "Colorado": "Colorado",
    "Connecticut": "Connecticut", "Delaware": "Delaware",
    "District of Columbia": "District of Columbia", "Florida": "Florida",
    "Georgia": "Georgia", "Hawaii": "Hawaii", "Idaho": "Idaho",
    "Illinois": "Illinois", "Indiana": "Indiana", "Iowa": "Iowa",
    "Kansas": "Kansas", "Kentucky": "Kentucky", "Louisiana": "Louisiana",
    "Maine": "Maine", "Maryland": "Maryland", "Massachusetts": "Massachusetts",
    "Michigan": "Michigan", "Minnesota": "Minnesota", "Mississippi": "Mississippi",
    "Missouri": "Missouri", "Montana": "Montana", "Nebraska": "Nebraska",
    "Nevada": "Nevada", "New Hampshire": "New Hampshire",
    "New Jersey": "New Jersey", "New Mexico": "New Mexico",
    "New York": "New York", "North Carolina": "North Carolina",
    "North Dakota": "North Dakota", "Ohio": "Ohio", "Oklahoma": "Oklahoma",
    "Oregon": "Oregon", "Pennsylvania": "Pennsylvania",
    "Rhode Island": "Rhode Island", "South Carolina": "South Carolina",
    "South Dakota": "South Dakota", "Tennessee": "Tennessee",
    "Texas": "Texas", "Utah": "Utah", "Vermont": "Vermont",
    "Virginia": "Virginia", "Washington": "Washington",
    "West Virginia": "West Virginia", "Wisconsin": "Wisconsin",
    "Wyoming": "Wyoming",
}


def normalize_state(raw):
    """Extract state name from CDC WONDER format like 'Alabama (01)'."""
    m = re.match(r'^(.+?)\s*\(\d+\)$', raw.strip())
    name = m.group(1).strip() if m else raw.strip()
    return STATE_NAME_MAP.get(name)


def parse_births(val):
    """Parse birth count, handling Suppressed/Not Applicable."""
    val = val.strip()
    if val in ('Suppressed', 'Not Applicable', 'Not Available', ''):
        return None
    val = val.replace(',', '')
    try:
        return int(val)
    except ValueError:
        return None


def main():
    infile = os.path.join(BASE, "raw-data",
                          "cdc_wonder_D149_wnh_mother_by_father_race.txt")

    # Parse the raw data file (with deduplication — CDC scrapes often have
    # duplicate sections from two query results concatenated)
    seen = set()
    data_rows = []
    with open(infile, 'r') as f:
        for line in f:
            parts = line.rstrip('\n\r').split('\t')
            if len(parts) < 5:
                continue
            year_str = parts[0].strip()
            if not re.match(r'^\d{4}$', year_str):
                continue

            year = int(year_str)
            state = normalize_state(parts[1])
            father_race = parts[2].strip()
            father_hisp = parts[3].strip()
            births = parse_births(parts[4])

            if not state:
                continue

            dedup_key = (year, state, father_race, father_hisp)
            if dedup_key in seen:
                continue
            seen.add(dedup_key)

            data_rows.append({
                'year': year,
                'state': state,
                'father_race': father_race,
                'father_hisp': father_hisp,
                'births': births,
            })

    print(f"Parsed {len(data_rows)} data rows from D149 (after deduplication)")

    # Aggregate by state × year
    # For each state×year, compute:
    #   total_wnh_mother = sum of all rows (births to WNH mothers)
    #   both_parent_wnh = father_race=White AND father_hisp=Not Hispanic
    #   father_unknown = father_race=Unknown/Not Stated/Not Reported OR father_hisp=Unknown
    #   father_non_wnh = everything else
    agg = defaultdict(lambda: {
        'total_wnh_mother': 0,
        'both_parent_wnh': 0,
        'father_unknown': 0,
        'father_non_wnh': 0,
        'suppressed_count': 0,
    })

    for row in data_rows:
        key = (row['year'], row['state'])
        births = row['births']
        fr = row['father_race']
        fh = row['father_hisp']

        if births is None:
            agg[key]['suppressed_count'] += 1
            continue

        agg[key]['total_wnh_mother'] += births

        is_father_white = (fr == 'White')
        is_father_not_hisp = (fh == 'Not Hispanic or Latino')
        is_father_unknown_race = fr in ('Unknown or Not Stated', 'Not Reported')
        is_father_unknown_hisp = fh in ('Unknown or Not Stated', 'Not Reported')

        if is_father_white and is_father_not_hisp:
            agg[key]['both_parent_wnh'] += births
        elif is_father_unknown_race or is_father_unknown_hisp:
            agg[key]['father_unknown'] += births
        else:
            agg[key]['father_non_wnh'] += births

    # Load total births from existing data for comparison
    total_births_by_key = {}
    smooth_path = os.path.join(BASE, '..', 'extracted_data', 'smooth_wnh.csv')
    if os.path.exists(smooth_path):
        with open(smooth_path, 'r') as f:
            reader = csv.DictReader(f)
            for row in reader:
                yr = int(row['year'])
                st = row['state']
                total = row.get('total_births', '')
                if total and yr >= 2016:
                    try:
                        total_births_by_key[(yr, st)] = int(float(total))
                    except ValueError:
                        pass

    # Build output
    output_rows = []
    for (year, state), v in sorted(agg.items()):
        total_births = total_births_by_key.get((year, state), 0)

        pct_both_parent = (v['both_parent_wnh'] / total_births * 100
                          if total_births > 0 else None)
        pct_mother_only = (v['total_wnh_mother'] / total_births * 100
                          if total_births > 0 else None)
        pct_father_unknown = (v['father_unknown'] / v['total_wnh_mother'] * 100
                             if v['total_wnh_mother'] > 0 else None)

        output_rows.append({
            'year': year,
            'state': state,
            'total_births': total_births,
            'wnh_mother_births': v['total_wnh_mother'],
            'both_parent_wnh_births': v['both_parent_wnh'],
            'father_unknown_births': v['father_unknown'],
            'father_non_wnh_births': v['father_non_wnh'],
            'suppressed_cells': v['suppressed_count'],
            'pct_wnh_mother': round(pct_mother_only, 2) if pct_mother_only else '',
            'pct_both_parent_wnh': round(pct_both_parent, 2) if pct_both_parent else '',
            'pct_father_unknown': round(pct_father_unknown, 2) if pct_father_unknown else '',
        })

    # Write CSV
    outpath = os.path.join(BASE, 'extracted_d149_both_parent_wnh.csv')
    fieldnames = ['year', 'state', 'total_births', 'wnh_mother_births',
                  'both_parent_wnh_births', 'father_unknown_births',
                  'father_non_wnh_births', 'suppressed_cells',
                  'pct_wnh_mother', 'pct_both_parent_wnh', 'pct_father_unknown']
    with open(outpath, 'w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(output_rows)

    print(f"\nOutput: {len(output_rows)} rows -> {outpath}")

    # Summary statistics
    print(f"\n{'='*70}")
    print("ANALYSIS: Mother-Only WNH vs Both-Parent WNH (2016-2024)")
    print('='*70)

    for year in sorted(set(k[0] for k in agg.keys())):
        year_rows = [r for r in output_rows if r['year'] == year and r['total_births'] > 0]
        if not year_rows:
            continue

        tot_births = sum(r['total_births'] for r in year_rows)
        tot_mom_wnh = sum(r['wnh_mother_births'] for r in year_rows)
        tot_both_wnh = sum(r['both_parent_wnh_births'] for r in year_rows)
        tot_unknown = sum(r['father_unknown_births'] for r in year_rows)
        tot_non_wnh = sum(r['father_non_wnh_births'] for r in year_rows)

        pct_mom = tot_mom_wnh / tot_births * 100 if tot_births else 0
        pct_both = tot_both_wnh / tot_births * 100 if tot_births else 0
        pct_unk = tot_unknown / tot_mom_wnh * 100 if tot_mom_wnh else 0
        gap = pct_mom - pct_both

        print(f"\n  {year}:")
        print(f"    Total births:        {tot_births:>10,}")
        print(f"    WNH mother births:   {tot_mom_wnh:>10,}  ({pct_mom:.1f}%)")
        print(f"    Both parent WNH:     {tot_both_wnh:>10,}  ({pct_both:.1f}%)")
        print(f"    Father unknown:      {tot_unknown:>10,}  ({pct_unk:.1f}% of WNH mothers)")
        print(f"    Father non-WNH:      {tot_non_wnh:>10,}")
        print(f"    Gap (mom - both):    {gap:+.1f} percentage points")

    # Per-state analysis for latest year
    latest_year = max(k[0] for k in agg.keys())
    print(f"\n{'='*70}")
    print(f"STATE DETAIL — {latest_year}")
    print(f"{'State':25s} {'Mom WNH%':>10s} {'Both WNH%':>10s} {'Gap':>8s} {'Father Unk%':>12s}")
    print('-' * 70)

    latest = [r for r in output_rows if r['year'] == latest_year and r['total_births'] > 0]
    latest.sort(key=lambda r: float(r['pct_both_parent_wnh'] or 0))

    for r in latest:
        mom = float(r['pct_wnh_mother']) if r['pct_wnh_mother'] else 0
        both = float(r['pct_both_parent_wnh']) if r['pct_both_parent_wnh'] else 0
        unk = float(r['pct_father_unknown']) if r['pct_father_unknown'] else 0
        gap = mom - both
        print(f"  {r['state']:23s} {mom:>9.1f}% {both:>9.1f}% {gap:>+7.1f} {unk:>10.1f}%")


if __name__ == '__main__':
    main()
