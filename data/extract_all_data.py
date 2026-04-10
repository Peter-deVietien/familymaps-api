#!/usr/bin/env python3
"""
Extract birth data by race from all downloaded sources, producing:
  - data/nhgis/extracted_data.csv
  - data/nber_historical/extracted_data.csv
  - data/cdc_wonder/extracted_data.csv
  - data/kff/extracted_data.csv
  - data/extracted_data/all_data.csv  (combined)

Goal: percent of White non-Hispanic births by year × state, 1940–present.

Output columns:
  year, state, source, total_births, white_births, white_nh_births,
  nonwhite_births, pct_white, pct_white_nh, race_category_type, notes
"""

import os
import glob
import re
import warnings
import pandas as pd
import numpy as np

warnings.filterwarnings("ignore")

BASE = os.path.dirname(os.path.abspath(__file__))

# Canonical state names for normalization
STATE_NAME_MAP = {
    "ALABAMA": "Alabama", "ALASKA": "Alaska", "ARIZONA": "Arizona",
    "ARKANSAS": "Arkansas", "CALIFORNIA": "California", "COLORADO": "Colorado",
    "CONNECTICUT": "Connecticut", "DELAWARE": "Delaware",
    "DISTRICT OF COLUMBIA": "District of Columbia",
    "DIST OF COLUMBIA": "District of Columbia",
    "DIST. OF COLUMBIA": "District of Columbia",
    "FLORIDA": "Florida", "GEORGIA": "Georgia", "HAWAII": "Hawaii",
    "IDAHO": "Idaho", "ILLINOIS": "Illinois", "INDIANA": "Indiana",
    "IOWA": "Iowa", "KANSAS": "Kansas", "KENTUCKY": "Kentucky",
    "LOUISIANA": "Louisiana", "MAINE": "Maine", "MARYLAND": "Maryland",
    "MASSACHUSETTS": "Massachusetts", "MICHIGAN": "Michigan",
    "MINNESOTA": "Minnesota", "MISSISSIPPI": "Mississippi",
    "MISSOURI": "Missouri", "MONTANA": "Montana", "NEBRASKA": "Nebraska",
    "NEVADA": "Nevada", "NEW HAMPSHIRE": "New Hampshire",
    "NEW JERSEY": "New Jersey", "NEW MEXICO": "New Mexico",
    "NEW YORK": "New York", "NORTH CAROLINA": "North Carolina",
    "NORTH DAKOTA": "North Dakota", "OHIO": "Ohio", "OKLAHOMA": "Oklahoma",
    "OREGON": "Oregon", "PENNSYLVANIA": "Pennsylvania",
    "RHODE ISLAND": "Rhode Island", "SOUTH CAROLINA": "South Carolina",
    "SOUTH DAKOTA": "South Dakota", "TENNESSEE": "Tennessee",
    "TEXAS": "Texas", "UTAH": "Utah", "VERMONT": "Vermont",
    "VIRGINIA": "Virginia", "WASHINGTON": "Washington",
    "WEST VIRGINIA": "West Virginia", "WISCONSIN": "Wisconsin",
    "WYOMING": "Wyoming",
    "ALASKA TERRITORY": "Alaska", "HAWAII TERRITORY": "Hawaii",
}


def normalize_state(name):
    if not isinstance(name, str):
        return None
    name = name.strip()
    upper = name.upper()
    if upper in STATE_NAME_MAP:
        return STATE_NAME_MAP[upper]
    if name.title() in STATE_NAME_MAP.values():
        return name.title()
    # Handle "Alabama (01)" format from CDC WONDER
    m = re.match(r"^(.+?)\s*\(\d+\)$", name)
    if m:
        return normalize_state(m.group(1))
    return None


def parse_number(val):
    """Parse a number that may have commas or be N/A."""
    if pd.isna(val):
        return np.nan
    s = str(val).strip().replace(",", "")
    if s in ("", "N/A", "Not Applicable", "Suppressed", "Not Available"):
        return np.nan
    try:
        return int(s)
    except ValueError:
        try:
            return float(s)
        except ValueError:
            return np.nan


# ---------------------------------------------------------------------------
# 1. NHGIS
# ---------------------------------------------------------------------------
def extract_nhgis():
    print("=" * 60)
    print("Extracting NHGIS data...")
    nhgis_dir = os.path.join(BASE, "nhgis", "raw-data", "nhgis_extract_1", "nhgis0001_csv")
    rows = []

    # ds224: 1915-1941 — AF1U001=total, AF1V001=white, AF1V002=nonwhite
    for f in sorted(glob.glob(os.path.join(nhgis_dir, "*ds224*_state.csv"))):
        df = pd.read_csv(f)
        year = int(df["YEAR"].iloc[0])
        if year < 1940:
            continue
        for _, r in df.iterrows():
            st = normalize_state(str(r.get("AREANAME", "") or r.get("STATE", "")))
            if not st:
                continue
            total = parse_number(r.get("AF1U001"))
            white = parse_number(r.get("AF1V001"))
            nonwhite = parse_number(r.get("AF1V002"))
            if pd.isna(total) and pd.isna(white):
                continue
            rows.append({
                "year": year, "state": st, "source": "NHGIS ds224",
                "total_births": total, "white_births": white,
                "white_nh_births": np.nan, "nonwhite_births": nonwhite,
                "race_category_type": "White/Nonwhite",
                "notes": "occurrence-based; White includes Hispanic"
            })

    # ds229: 1939-1959 — residence: AGVE001=total, AGVF001=white, AGVF002=nonwhite
    #                     occurrence: AGVA001=total, AGVB001=white, AGVB002=nonwhite
    for f in sorted(glob.glob(os.path.join(nhgis_dir, "*ds229*_state.csv"))):
        df = pd.read_csv(f)
        year = int(df["YEAR"].iloc[0])
        if year < 1940:
            continue
        for _, r in df.iterrows():
            st = normalize_state(str(r.get("AREANAME", "") or r.get("STATE", "")))
            if not st:
                continue
            # Prefer residence-based; fall back to occurrence
            # If residence has total but no race, use occurrence for race
            total_res = parse_number(r.get("AGVE001"))
            white_res = parse_number(r.get("AGVF001"))
            nonwhite_res = parse_number(r.get("AGVF002"))
            total_occ = parse_number(r.get("AGVA001"))
            white_occ = parse_number(r.get("AGVB001"))
            nonwhite_occ = parse_number(r.get("AGVB002"))

            if not pd.isna(total_res) and not pd.isna(white_res):
                total, white, nonwhite = total_res, white_res, nonwhite_res
                basis = "residence-based"
            elif not pd.isna(total_occ) and not pd.isna(white_occ):
                total, white, nonwhite = total_occ, white_occ, nonwhite_occ
                basis = "occurrence-based"
            elif not pd.isna(total_res):
                total, white, nonwhite = total_res, white_occ, nonwhite_occ
                basis = "residence total + occurrence race"
            elif not pd.isna(total_occ):
                total, white, nonwhite = total_occ, np.nan, np.nan
                basis = "occurrence-based (total only)"
            else:
                continue

            if pd.isna(total) and pd.isna(white):
                continue
            rows.append({
                "year": year, "state": st, "source": "NHGIS ds229",
                "total_births": total, "white_births": white,
                "white_nh_births": np.nan, "nonwhite_births": nonwhite,
                "race_category_type": "White/Nonwhite",
                "notes": f"{basis}; White includes Hispanic; residence only from 1942"
            })

    # ds230: 1959-1972 — residence: AGV1001=total, AGV2001=white, AGV2002=negro, AGV2003=other
    #                     occurrence: AGVT001=total, AGVU001=white, AGVU002=negro, AGVU003=other
    for f in sorted(glob.glob(os.path.join(nhgis_dir, "*ds230*_state.csv"))):
        df = pd.read_csv(f)
        year = int(df["YEAR"].iloc[0])
        for _, r in df.iterrows():
            st = normalize_state(str(r.get("AREANAME", "") or r.get("STATE", "")))
            if not st:
                continue
            total_res = parse_number(r.get("AGV1001"))
            white_res = parse_number(r.get("AGV2001"))
            negro_res = parse_number(r.get("AGV2002"))
            other_res = parse_number(r.get("AGV2003"))
            total_occ = parse_number(r.get("AGVT001"))
            white_occ = parse_number(r.get("AGVU001"))

            if not pd.isna(total_res):
                total = total_res
                white = white_res
                nonwhite_parts = [negro_res, other_res]
                nonwhite = sum(x for x in nonwhite_parts if not pd.isna(x)) if any(not pd.isna(x) for x in nonwhite_parts) else np.nan
                basis = "residence-based"
            elif not pd.isna(total_occ):
                total = total_occ
                white = white_occ
                negro_occ = parse_number(r.get("AGVU002"))
                other_occ = parse_number(r.get("AGVU003"))
                nonwhite_parts = [negro_occ, other_occ]
                nonwhite = sum(x for x in nonwhite_parts if not pd.isna(x)) if any(not pd.isna(x) for x in nonwhite_parts) else np.nan
                basis = "occurrence-based"
            else:
                continue

            if pd.isna(total) and pd.isna(white):
                continue
            rows.append({
                "year": year, "state": st, "source": "NHGIS ds230",
                "total_births": total, "white_births": white,
                "white_nh_births": np.nan, "nonwhite_births": nonwhite,
                "race_category_type": "White/Negro/Other",
                "notes": f"{basis}; White includes Hispanic"
            })

    # ds231: 1970-2007 — AGWE001=total births only (no race)
    for f in sorted(glob.glob(os.path.join(nhgis_dir, "*ds231*_state.csv"))):
        df = pd.read_csv(f)
        year = int(df["YEAR"].iloc[0])
        for _, r in df.iterrows():
            st = normalize_state(str(r.get("AREANAME", "") or r.get("STATE", "")))
            if not st:
                continue
            total = parse_number(r.get("AGWE001"))
            if pd.isna(total):
                continue
            rows.append({
                "year": year, "state": st, "source": "NHGIS ds231",
                "total_births": total, "white_births": np.nan,
                "white_nh_births": np.nan, "nonwhite_births": np.nan,
                "race_category_type": "Total only",
                "notes": "total births only; no race breakdown available"
            })

    nhgis_df = pd.DataFrame(rows)
    out = os.path.join(BASE, "nhgis", "extracted_data.csv")
    nhgis_df.to_csv(out, index=False)
    print(f"  NHGIS: {len(nhgis_df)} rows -> {out}")
    print(f"    ds224: {len(nhgis_df[nhgis_df.source == 'NHGIS ds224'])} rows ({nhgis_df[nhgis_df.source == 'NHGIS ds224']['year'].min()}-{nhgis_df[nhgis_df.source == 'NHGIS ds224']['year'].max()})")
    print(f"    ds229: {len(nhgis_df[nhgis_df.source == 'NHGIS ds229'])} rows ({nhgis_df[nhgis_df.source == 'NHGIS ds229']['year'].min()}-{nhgis_df[nhgis_df.source == 'NHGIS ds229']['year'].max()})")
    print(f"    ds230: {len(nhgis_df[nhgis_df.source == 'NHGIS ds230'])} rows ({nhgis_df[nhgis_df.source == 'NHGIS ds230']['year'].min()}-{nhgis_df[nhgis_df.source == 'NHGIS ds230']['year'].max()})")
    print(f"    ds231: {len(nhgis_df[nhgis_df.source == 'NHGIS ds231'])} rows ({nhgis_df[nhgis_df.source == 'NHGIS ds231']['year'].min()}-{nhgis_df[nhgis_df.source == 'NHGIS ds231']['year'].max()})")
    return nhgis_df


# ---------------------------------------------------------------------------
# 2. NBER Historical (1940-1968 Stata files)
# ---------------------------------------------------------------------------
def extract_nber_historical():
    print("=" * 60)
    print("Extracting NBER Historical data...")
    stata_dir = os.path.join(BASE, "nber_historical", "raw-data", "births_data",
                             "5_births_data-cleaned_stata")
    rows = []

    for year in range(1940, 1969):
        fpath = os.path.join(stata_dir, f"clean_natality{year}.dta")
        if not os.path.exists(fpath):
            print(f"  WARNING: {fpath} not found")
            continue
        df = pd.read_stata(fpath)

        if year <= 1945:
            # No race column — total births only, filter to state-level
            state_rows = df[df["county"].str.strip().str.lower() == "total"]
            for _, r in state_rows.iterrows():
                st = normalize_state(str(r["state"]))
                if not st:
                    continue
                total = parse_number(r.get("births"))
                if pd.isna(total):
                    continue
                rows.append({
                    "year": year, "state": st, "source": "NBER Historical",
                    "total_births": total, "white_births": np.nan,
                    "white_nh_births": np.nan, "nonwhite_births": np.nan,
                    "race_category_type": "Total only",
                    "notes": "1940-1945: no race in source; attendant type only"
                })
        else:
            # 1946-1968: has race column (total/white/nonwhite)
            state_rows = df[df["county"].str.strip().str.lower() == "total"].copy()
            # Pivot: for each state, get total/white/nonwhite births
            for st_name in state_rows["state"].unique():
                st = normalize_state(str(st_name))
                if not st:
                    continue
                st_data = state_rows[state_rows["state"] == st_name]
                total_row = st_data[st_data["race"].str.strip().str.lower() == "total"]
                white_row = st_data[st_data["race"].str.strip().str.lower() == "white"]
                nonwhite_row = st_data[st_data["race"].str.strip().str.lower() == "nonwhite"]

                total = parse_number(total_row["births"].iloc[0]) if len(total_row) > 0 else np.nan
                white = parse_number(white_row["births"].iloc[0]) if len(white_row) > 0 else np.nan
                nonwhite = parse_number(nonwhite_row["births"].iloc[0]) if len(nonwhite_row) > 0 else np.nan

                if pd.isna(total) and pd.isna(white):
                    continue
                rows.append({
                    "year": year, "state": st, "source": "NBER Historical",
                    "total_births": total, "white_births": white,
                    "white_nh_births": np.nan, "nonwhite_births": nonwhite,
                    "race_category_type": "White/Nonwhite",
                    "notes": "White includes Hispanic"
                })

    nber_df = pd.DataFrame(rows)
    out = os.path.join(BASE, "nber_historical", "extracted_data.csv")
    nber_df.to_csv(out, index=False)
    print(f"  NBER Historical: {len(nber_df)} rows -> {out}")
    yr_range = f"{nber_df['year'].min()}-{nber_df['year'].max()}" if len(nber_df) > 0 else "none"
    print(f"    Years: {yr_range}, States: {nber_df['state'].nunique()}")
    return nber_df


# ---------------------------------------------------------------------------
# 3. CDC WONDER (D10, D27, D66)
# ---------------------------------------------------------------------------
def parse_cdc_wonder_file(filepath):
    """Parse a CDC WONDER tab-separated results file into data rows."""
    data_rows = []
    with open(filepath, "r", encoding="utf-8", errors="replace") as fh:
        lines = fh.readlines()

    for line in lines:
        line = line.rstrip("\n\r")
        parts = line.split("\t")
        if len(parts) < 5:
            continue
        # Data rows start with a 4-digit year
        year_str = parts[0].strip()
        if not re.match(r"^\d{4}$", year_str):
            continue
        year = int(year_str)
        state_raw = parts[1].strip()
        race = parts[2].strip()
        hispanic = parts[3].strip()
        births_str = parts[4].strip()
        births = parse_number(births_str)

        state = normalize_state(state_raw)
        if not state:
            continue

        data_rows.append({
            "year": year, "state": state, "race": race,
            "hispanic": hispanic, "births": births
        })
    return pd.DataFrame(data_rows)


def extract_cdc_wonder():
    print("=" * 60)
    print("Extracting CDC WONDER data...")
    wonder_dir = os.path.join(BASE, "cdc_wonder", "raw-data")
    all_rows = []

    # --- D10: 1995-2002 ---
    d10_path = os.path.join(wonder_dir, "cdc_wonder_D10_state_race_hisp.txt")
    if os.path.exists(d10_path):
        d10_raw = parse_cdc_wonder_file(d10_path)
        # Deduplicate (file may have duplicate sections)
        d10_raw = d10_raw.drop_duplicates(subset=["year", "state", "race", "hispanic"])
        print(f"  D10 raw rows (deduplicated): {len(d10_raw)}")

        # D10 Hispanic categories: Mexican, Puerto Rican, Cuban,
        # Central or South American, Other and Unknown Hispanic,
        # Non-Hispanic White, Non-Hispanic Black, Non-Hispanic other races,
        # Origin unknown or not stated
        # White NH = race=="White" & hispanic=="Non-Hispanic White"
        for (year, state), grp in d10_raw.groupby(["year", "state"]):
            total = grp["births"].sum()
            white_rows = grp[grp["race"] == "White"]
            white_all = white_rows["births"].sum()
            white_nh_row = white_rows[white_rows["hispanic"] == "Non-Hispanic White"]
            white_nh = white_nh_row["births"].sum() if len(white_nh_row) > 0 else np.nan
            nonwhite = total - white_all if not pd.isna(total) else np.nan

            all_rows.append({
                "year": year, "state": state, "source": "CDC WONDER D10",
                "total_births": total, "white_births": white_all,
                "white_nh_births": white_nh, "nonwhite_births": nonwhite,
                "race_category_type": "Race×Hispanic (8 races)",
                "notes": "White NH = Race:White + Hispanic:Non-Hispanic White"
            })

    # --- D27: 2003-2006 ---
    d27_path = os.path.join(wonder_dir, "cdc_wonder_D27_state_race_hisp.txt")
    if os.path.exists(d27_path):
        d27_raw = parse_cdc_wonder_file(d27_path)
        d27_raw = d27_raw.drop_duplicates(subset=["year", "state", "race", "hispanic"])
        print(f"  D27 raw rows (deduplicated): {len(d27_raw)}")

        # D27: Bridged Race (White, Black/AA, AIAN, Asian/PI) × Hispanic Origin
        for (year, state), grp in d27_raw.groupby(["year", "state"]):
            total = grp["births"].sum()
            white_rows = grp[grp["race"] == "White"]
            white_all = white_rows["births"].sum()
            white_nh_row = white_rows[white_rows["hispanic"] == "Not Hispanic or Latino"]
            white_nh = white_nh_row["births"].sum() if len(white_nh_row) > 0 else np.nan
            nonwhite = total - white_all if not pd.isna(total) else np.nan

            all_rows.append({
                "year": year, "state": state, "source": "CDC WONDER D27",
                "total_births": total, "white_births": white_all,
                "white_nh_births": white_nh, "nonwhite_births": nonwhite,
                "race_category_type": "Bridged Race×Hispanic",
                "notes": "White NH = Race:White + Hispanic:Not Hispanic or Latino"
            })

    # --- D66: 2007-2024 (Single Race) ---
    d66_path = os.path.join(wonder_dir, "cdc_wonder_D66_state_race_hisp.txt")
    if os.path.exists(d66_path):
        d66_raw = parse_cdc_wonder_file(d66_path)
        d66_raw = d66_raw.drop_duplicates(subset=["year", "state", "race", "hispanic"])
        print(f"  D66 Single Race raw rows (deduplicated): {len(d66_raw)}")

        for (year, state), grp in d66_raw.groupby(["year", "state"]):
            total = grp["births"].sum()
            has_race = not all(grp["race"] == "Not Available")

            if has_race:
                white_rows = grp[grp["race"] == "White"]
                white_all = white_rows["births"].sum()
                white_nh_row = white_rows[white_rows["hispanic"] == "Not Hispanic or Latino"]
                white_nh = white_nh_row["births"].sum() if len(white_nh_row) > 0 else np.nan
                nonwhite = total - white_all if not pd.isna(total) else np.nan
                cat = "Single Race 6×Hispanic"
                note = "White NH = Race:White + Hispanic:Not Hispanic or Latino"
            else:
                not_hisp_rows = grp[grp["hispanic"] == "Not Hispanic or Latino"]
                not_hisp_total = not_hisp_rows["births"].sum() if len(not_hisp_rows) > 0 else np.nan
                hisp_rows = grp[grp["hispanic"] == "Hispanic or Latino"]
                hisp_total = hisp_rows["births"].sum() if len(hisp_rows) > 0 else np.nan
                white_all = np.nan
                white_nh = np.nan
                nonwhite = np.nan
                cat = "Hispanic only (no race)"
                note = f"Race not available; Not Hispanic total={int(not_hisp_total) if not pd.isna(not_hisp_total) else 'N/A'}; Hispanic total={int(hisp_total) if not pd.isna(hisp_total) else 'N/A'}"

            all_rows.append({
                "year": year, "state": state, "source": "CDC WONDER D66",
                "total_births": total, "white_births": white_all,
                "white_nh_births": white_nh, "nonwhite_births": nonwhite,
                "race_category_type": cat,
                "notes": note
            })

    # --- D66 Bridged Race: 2007-2024 (fills 2007-2015 race gap) ---
    d66b_path = os.path.join(wonder_dir, "cdc_wonder_D66_bridged_state_race_hisp.txt")
    if os.path.exists(d66b_path):
        d66b_raw = parse_cdc_wonder_file(d66b_path)
        d66b_raw = d66b_raw.drop_duplicates(subset=["year", "state", "race", "hispanic"])
        print(f"  D66 Bridged Race raw rows (deduplicated): {len(d66b_raw)}")

        for (year, state), grp in d66b_raw.groupby(["year", "state"]):
            total = grp["births"].sum()
            white_rows = grp[grp["race"] == "White"]
            white_all = white_rows["births"].sum()
            white_nh_row = white_rows[white_rows["hispanic"] == "Not Hispanic or Latino"]
            white_nh = white_nh_row["births"].sum() if len(white_nh_row) > 0 else np.nan
            nonwhite = total - white_all if not pd.isna(total) else np.nan

            all_rows.append({
                "year": year, "state": state, "source": "CDC WONDER D66 Bridged",
                "total_births": total, "white_births": white_all,
                "white_nh_births": white_nh, "nonwhite_births": nonwhite,
                "race_category_type": "Bridged Race×Hispanic",
                "notes": "White NH = Bridged Race:White + Hispanic:Not Hispanic or Latino"
            })

    cdc_df = pd.DataFrame(all_rows)
    out = os.path.join(BASE, "cdc_wonder", "extracted_data.csv")
    cdc_df.to_csv(out, index=False)
    print(f"  CDC WONDER: {len(cdc_df)} rows -> {out}")
    for src in cdc_df["source"].unique():
        sub = cdc_df[cdc_df["source"] == src]
        print(f"    {src}: {len(sub)} rows ({sub['year'].min()}-{sub['year'].max()})")
    return cdc_df


# ---------------------------------------------------------------------------
# 4. KFF
# ---------------------------------------------------------------------------
def extract_kff():
    print("=" * 60)
    print("Extracting KFF data...")
    kff_path = os.path.join(BASE, "kff", "raw-data", "kff_births_by_race_ethnicity.csv")
    df = pd.read_csv(kff_path)
    rows = []
    for _, r in df.iterrows():
        st = normalize_state(str(r["Location"]))
        if not st:
            continue
        year = int(r["Year"])
        white = parse_number(r.get("White"))
        black = parse_number(r.get("Black"))
        hispanic = parse_number(r.get("Hispanic"))
        asian = parse_number(r.get("Asian"))
        aian = parse_number(r.get("American Indian or Alaska Native"))
        nhpi = parse_number(r.get("Native Hawaiian or Pacific Islander"))
        multi = parse_number(r.get("More than one race"))

        # Compute total from race categories (Total column is empty in KFF)
        parts = [white, black, hispanic, asian, aian, nhpi, multi]
        valid_parts = [x for x in parts if not pd.isna(x)]
        total = sum(valid_parts) if valid_parts else np.nan

        rows.append({
            "year": year, "state": st, "source": "KFF",
            "total_births": total,
            "white_births": white,
            "white_nh_births": white,  # KFF "White" is likely White NH (Hispanic separate)
            "nonwhite_births": total - white if not pd.isna(total) and not pd.isna(white) else np.nan,
            "race_category_type": "7 race/ethnicity categories",
            "notes": "White likely=White NH (Hispanic is separate column); Total computed from categories"
        })

    kff_df = pd.DataFrame(rows)
    out = os.path.join(BASE, "kff", "extracted_data.csv")
    kff_df.to_csv(out, index=False)
    print(f"  KFF: {len(kff_df)} rows -> {out}")
    print(f"    Years: {kff_df['year'].min()}-{kff_df['year'].max()}, States: {kff_df['state'].nunique()}")
    return kff_df


# ---------------------------------------------------------------------------
# 5. NBER Microdata (1973-1994)
# ---------------------------------------------------------------------------
def extract_nber_microdata():
    print("=" * 60)
    print("Extracting NBER Microdata data...")
    micro_path = os.path.join(BASE, "nber_microdata", "extracted_data.csv")
    if not os.path.exists(micro_path):
        print("  WARNING: NBER Microdata extracted_data.csv not found")
        return pd.DataFrame()

    df = pd.read_csv(micro_path)
    print(f"  NBER Microdata: {len(df)} rows -> {micro_path}")
    yr_range = f"{df['year'].min()}-{df['year'].max()}" if len(df) > 0 else "none"
    print(f"    Years: {yr_range}, States: {df['state'].nunique()}")

    has_wnh = df["white_nh_births"].notna() & (df["white_nh_births"] != "") & (df["white_nh_births"] != 0)
    print(f"    Rows with White NH: {has_wnh.sum()}/{len(df)}")
    return df


# ---------------------------------------------------------------------------
# 6. Combine all sources -> all_data.csv
# ---------------------------------------------------------------------------
def combine_all(nhgis_df, nber_df, cdc_df, kff_df, micro_df=None):
    print("=" * 60)
    print("Combining all sources...")

    dfs = [nhgis_df, nber_df, cdc_df, kff_df]
    if micro_df is not None and len(micro_df) > 0:
        dfs.append(micro_df)
    combined = pd.concat(dfs, ignore_index=True)

    # Compute percentages
    combined["pct_white"] = np.where(
        combined["total_births"] > 0,
        (combined["white_births"] / combined["total_births"] * 100).round(2),
        np.nan
    )
    combined["pct_white_nh"] = np.where(
        combined["total_births"] > 0,
        (combined["white_nh_births"] / combined["total_births"] * 100).round(2),
        np.nan
    )

    combined = combined.sort_values(["year", "state", "source"]).reset_index(drop=True)

    # Column order for Excel friendliness
    cols = ["year", "state", "source", "total_births", "white_births",
            "white_nh_births", "nonwhite_births", "pct_white", "pct_white_nh",
            "race_category_type", "notes"]
    combined = combined[cols]

    out = os.path.join(BASE, "extracted_data", "all_data.csv")
    combined.to_csv(out, index=False)
    print(f"  Combined: {len(combined)} rows -> {out}")
    print(f"  Years: {int(combined['year'].min())}-{int(combined['year'].max())}")
    print(f"  States: {combined['state'].nunique()}")
    print(f"  Sources: {combined['source'].nunique()} ({', '.join(combined['source'].unique())})")

    # Summary stats
    print("\n  Coverage by source:")
    for src in sorted(combined["source"].unique()):
        sub = combined[combined["source"] == src]
        has_white = sub["white_births"].notna().sum()
        has_wnh = sub["white_nh_births"].notna().sum()
        print(f"    {src}: {sub['year'].min()}-{sub['year'].max()}, "
              f"{len(sub)} rows, "
              f"white_births: {has_white}/{len(sub)}, "
              f"white_nh: {has_wnh}/{len(sub)}")

    print("\n  Year coverage summary:")
    for decade_start in range(1940, 2030, 10):
        decade_end = min(decade_start + 9, 2024)
        dec = combined[(combined["year"] >= decade_start) & (combined["year"] <= decade_end)]
        if len(dec) == 0:
            continue
        has_wnh = dec["white_nh_births"].notna().sum()
        has_w = dec["white_births"].notna().sum()
        srcs = ", ".join(sorted(dec["source"].unique()))
        print(f"    {decade_start}s: {len(dec)} rows, "
              f"white: {has_w}, white_nh: {has_wnh} [{srcs}]")

    # Also create a "best estimate" version that picks the best source per year×state
    best = create_best_estimate(combined)
    return combined, best


def create_best_estimate(combined):
    """Pick the single best source for each year×state combination."""
    print("\n" + "=" * 60)
    print("Creating best-estimate file (one row per year×state)...")

    # Priority order for source selection
    source_priority = {
        "CDC WONDER D66": 1, "CDC WONDER D66 Bridged": 2,
        "CDC WONDER D27": 3, "CDC WONDER D10": 4,
        "KFF": 5, "NBER Microdata": 6,
        "NHGIS ds230": 7, "NHGIS ds229": 8, "NHGIS ds224": 9,
        "NBER Historical": 10, "NHGIS ds231": 11,
    }

    rows = []
    for (year, state), grp in combined.groupby(["year", "state"]):
        # Prefer sources with white_nh_births, then white_births, then total_births
        best_row = None
        best_score = (999, 999)  # (has_data_score, priority)

        for _, row in grp.iterrows():
            has_wnh = 0 if pd.isna(row["white_nh_births"]) else 1
            has_w = 0 if pd.isna(row["white_births"]) else 1
            has_t = 0 if pd.isna(row["total_births"]) else 1
            data_score = -(has_wnh * 100 + has_w * 10 + has_t)
            priority = source_priority.get(row["source"], 50)
            score = (data_score, priority)
            if score < best_score:
                best_score = score
                best_row = row

        if best_row is not None:
            rows.append(best_row.to_dict())

    best_df = pd.DataFrame(rows)
    best_df = best_df.sort_values(["year", "state"]).reset_index(drop=True)

    out = os.path.join(BASE, "extracted_data", "best_estimate.csv")
    best_df.to_csv(out, index=False)
    print(f"  Best estimate: {len(best_df)} rows -> {out}")
    print(f"  Years: {int(best_df['year'].min())}-{int(best_df['year'].max())}")

    # Coverage report
    has_wnh = best_df["white_nh_births"].notna()
    has_w = best_df["white_births"].notna()
    has_t = best_df["total_births"].notna()
    print(f"  Rows with white_nh_births: {has_wnh.sum()}/{len(best_df)} "
          f"({has_wnh.sum()/len(best_df)*100:.1f}%)")
    print(f"  Rows with white_births: {has_w.sum()}/{len(best_df)} "
          f"({has_w.sum()/len(best_df)*100:.1f}%)")
    print(f"  Rows with total_births: {has_t.sum()}/{len(best_df)} "
          f"({has_t.sum()/len(best_df)*100:.1f}%)")

    # Year ranges by data availability
    wnh_years = sorted(best_df[has_wnh]["year"].unique())
    w_years = sorted(best_df[has_w & ~has_wnh]["year"].unique())
    t_only_years = sorted(best_df[has_t & ~has_w & ~has_wnh]["year"].unique())

    if wnh_years:
        print(f"  White NH available: {min(wnh_years)}-{max(wnh_years)}")
    if w_years:
        print(f"  White (incl Hisp) only: {min(w_years)}-{max(w_years)}")
    if t_only_years:
        print(f"  Total only (no race): {min(t_only_years)}-{max(t_only_years)}")

    return best_df


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    print("Birth Data Extraction Pipeline")
    print("Goal: % White non-Hispanic births by year × state, 1940–present")
    print()

    nhgis_df = extract_nhgis()
    nber_df = extract_nber_historical()
    cdc_df = extract_cdc_wonder()
    kff_df = extract_kff()
    micro_df = extract_nber_microdata()
    combined, best = combine_all(nhgis_df, nber_df, cdc_df, kff_df, micro_df)

    print("\n" + "=" * 60)
    print("DONE. Output files:")
    print(f"  data/nhgis/extracted_data.csv ({len(nhgis_df)} rows)")
    print(f"  data/nber_historical/extracted_data.csv ({len(nber_df)} rows)")
    print(f"  data/cdc_wonder/extracted_data.csv ({len(cdc_df)} rows)")
    print(f"  data/kff/extracted_data.csv ({len(kff_df)} rows)")
    print(f"  data/nber_microdata/extracted_data.csv ({len(micro_df)} rows)")
    print(f"  data/extracted_data/all_data.csv ({len(combined)} rows)")
    print(f"  data/extracted_data/best_estimate.csv ({len(best)} rows)")
