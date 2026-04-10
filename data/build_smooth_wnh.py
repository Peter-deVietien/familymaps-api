#!/usr/bin/env python3
"""
Build a smooth estimated White Non-Hispanic birth percentage series for all
state×year combinations from 1940 to present.

Strategy:
  1. 2016+: Use CDC WONDER D149 both-parent WNH (authoritative, actual data
     where both mother AND father are White Non-Hispanic)
  2. 1995-2015: Use CDC WONDER mother-only WNH, adjusted by per-state
     both-parent correction factor from D149 data
  3. Pre-1995: Estimate WNH from pct_white using a per-state Hispanic
     adjustment factor + both-parent correction factor

The both-parent correction accounts for the fact that mother-only WNH
overstates the true % of babies that are WNH (not all fathers are WNH).
State-specific factors are derived from D149 (2016-2024 expanded) data.

Output: data/extracted_data/smooth_wnh.csv
"""

import os
import math
import pandas as pd
import numpy as np

BASE = os.path.dirname(os.path.abspath(__file__))

# 1990 Census Hispanic % of total population by state
# Source: U.S. Bureau of the Census, 1990 Census STF1
CENSUS_1990_HISPANIC_PCT = {
    "Alabama": 0.6, "Alaska": 3.2, "Arizona": 18.8, "Arkansas": 0.8,
    "California": 25.8, "Colorado": 12.9, "Connecticut": 6.5,
    "Delaware": 2.4, "District of Columbia": 5.4, "Florida": 12.2,
    "Georgia": 1.7, "Hawaii": 7.3, "Idaho": 5.3, "Illinois": 7.9,
    "Indiana": 1.8, "Iowa": 1.2, "Kansas": 3.8, "Kentucky": 0.6,
    "Louisiana": 2.2, "Maine": 0.6, "Maryland": 2.6,
    "Massachusetts": 4.8, "Michigan": 2.2, "Minnesota": 1.2,
    "Mississippi": 0.6, "Missouri": 1.2, "Montana": 1.5,
    "Nebraska": 2.3, "Nevada": 10.4, "New Hampshire": 1.0,
    "New Jersey": 9.6, "New Mexico": 38.2, "New York": 12.3,
    "North Carolina": 1.2, "North Dakota": 0.7, "Ohio": 1.3,
    "Oklahoma": 2.7, "Oregon": 4.0, "Pennsylvania": 2.0,
    "Rhode Island": 4.6, "South Carolina": 0.9,
    "South Dakota": 0.8, "Tennessee": 0.7, "Texas": 25.5,
    "Utah": 4.9, "Vermont": 0.7, "Virginia": 2.6,
    "Washington": 4.4, "West Virginia": 0.5, "Wisconsin": 1.9,
    "Wyoming": 5.7,
}

# Approximate 1980 Census Hispanic % (from Census Working Paper 56)
CENSUS_1980_HISPANIC_PCT = {
    "Alabama": 0.9, "Alaska": 2.4, "Arizona": 16.2, "Arkansas": 0.8,
    "California": 19.2, "Colorado": 11.8, "Connecticut": 4.0,
    "Delaware": 1.6, "District of Columbia": 2.8, "Florida": 8.8,
    "Georgia": 1.1, "Hawaii": 7.4, "Idaho": 3.9, "Illinois": 5.6,
    "Indiana": 1.6, "Iowa": 0.9, "Kansas": 2.7, "Kentucky": 0.7,
    "Louisiana": 2.4, "Maine": 0.4, "Maryland": 1.5,
    "Massachusetts": 2.5, "Michigan": 1.8, "Minnesota": 0.8,
    "Mississippi": 0.6, "Missouri": 1.1, "Montana": 1.3,
    "Nebraska": 1.8, "Nevada": 6.7, "New Hampshire": 0.6,
    "New Jersey": 6.7, "New Mexico": 36.6, "New York": 9.4,
    "North Carolina": 1.0, "North Dakota": 0.6, "Ohio": 1.1,
    "Oklahoma": 1.9, "Oregon": 2.5, "Pennsylvania": 1.3,
    "Rhode Island": 2.1, "South Carolina": 0.6,
    "South Dakota": 0.6, "Tennessee": 0.7, "Texas": 21.0,
    "Utah": 4.1, "Vermont": 0.6, "Virginia": 1.5,
    "Washington": 2.9, "West Virginia": 0.7, "Wisconsin": 1.3,
    "Wyoming": 5.2,
}


def interpolate_hispanic_pct(state, year):
    """Estimate state Hispanic population % for any year between 1940 and 1995.

    Uses Census 1980 and 1990 benchmarks, with exponential back-projection to
    near-zero by 1940 (Hispanic population was negligible before 1950 in most
    states except the Southwest).
    """
    h1980 = CENSUS_1980_HISPANIC_PCT.get(state, 1.0)
    h1990 = CENSUS_1990_HISPANIC_PCT.get(state, 1.0)

    if year >= 1990:
        return h1990
    elif year >= 1980:
        frac = (year - 1980) / 10.0
        return h1980 + (h1990 - h1980) * frac
    elif year >= 1940:
        # Exponential decay toward near-zero by 1940
        # h(year) = h1980 * exp(-k * (1980 - year))
        # We want h(1940) ≈ h1980 * 0.15 for Southwest states, ~0.05 for others
        # A reasonable k gives ~15% of 1980 value at 1940 (40 years back)
        decay_factor = 0.047  # exp(-0.047*40) ≈ 0.15
        years_back = 1980 - year
        return h1980 * math.exp(-decay_factor * years_back)
    else:
        return 0.0


def compute_nh_ratio_from_hispanic_pct(hispanic_pct, calibration_ratio, calibration_hisp_pct):
    """Estimate the WNH/White ratio for a given Hispanic population %.

    The ratio represents: what fraction of "White" births are non-Hispanic.

    We calibrate using a known data point (calibration_ratio at calibration_hisp_pct)
    to account for the state-specific relationship between Hispanic population
    share and Hispanic share of White births (driven by fertility differentials,
    age structure, etc.).
    """
    if calibration_hisp_pct <= 0 or calibration_ratio >= 1.0:
        # If calibration shows near-100% ratio, Hispanic adjustment is minimal
        return min(1.0, calibration_ratio + (calibration_hisp_pct - hispanic_pct) * 0.01)

    # Hispanic share of White births ≈ 1 - ratio
    # This share is related to Hispanic population % via a multiplier
    # (Hispanic fertility is ~1.3-1.5x non-Hispanic fertility, and ~95% of
    # Hispanic births are White-race)
    calibration_hisp_birth_share = 1.0 - calibration_ratio
    if calibration_hisp_pct > 0:
        multiplier = calibration_hisp_birth_share / (calibration_hisp_pct / 100.0)
    else:
        multiplier = 1.5  # default

    hisp_birth_share = multiplier * (hispanic_pct / 100.0)
    hisp_birth_share = max(0.0, min(hisp_birth_share, 0.95))

    return 1.0 - hisp_birth_share


def load_both_parent_factors():
    """Load per-state both-parent WNH correction factors from D149 data.

    Returns dict: state -> {factor, avg_father_unknown_pct}
    where factor = both_parent_wnh / mother_only_wnh (avg over 2016-2024).
    """
    d149_path = os.path.join(BASE, "cdc_wonder", "extracted_d149_both_parent_wnh.csv")
    if not os.path.exists(d149_path):
        print("WARNING: D149 both-parent data not found, using mother-only")
        return {}

    d149 = pd.read_csv(d149_path)
    factors = {}

    for state in d149["state"].unique():
        st = d149[d149["state"] == state]
        total_mom = st["wnh_mother_births"].sum()
        total_both = st["both_parent_wnh_births"].sum()
        total_unk = st["father_unknown_births"].sum()

        if total_mom > 0:
            factor = total_both / total_mom
            unk_pct = total_unk / total_mom * 100
            factors[state] = {"factor": factor, "father_unknown_pct": unk_pct}

    return factors


def build_smooth_wnh():
    best_path = os.path.join(BASE, "extracted_data", "best_estimate.csv")
    df = pd.read_csv(best_path)

    print(f"Loaded {len(df)} rows from best_estimate.csv")
    print(f"Years: {int(df['year'].min())}-{int(df['year'].max())}")

    # Load D149 both-parent correction factors
    bp_factors = load_both_parent_factors()
    if bp_factors:
        avg_factor = np.mean([v["factor"] for v in bp_factors.values()])
        print(f"\nBoth-parent correction factors loaded for {len(bp_factors)} states")
        print(f"  National avg factor: {avg_factor:.3f} (both_parent / mother_only)")
        print(f"  Range: {min(v['factor'] for v in bp_factors.values()):.3f} - "
              f"{max(v['factor'] for v in bp_factors.values()):.3f}")

    # Load D149 actual both-parent WNH data for 2016+
    d149_both = {}
    d149_path = os.path.join(BASE, "cdc_wonder", "extracted_d149_both_parent_wnh.csv")
    if os.path.exists(d149_path):
        d149_df = pd.read_csv(d149_path)
        for _, row in d149_df.iterrows():
            total = row.get("total_births", 0)
            both_wnh = row.get("both_parent_wnh_births", 0)
            if total > 0 and both_wnh > 0:
                d149_both[(int(row["year"]), row["state"])] = {
                    "pct": round(both_wnh / total * 100, 2),
                    "births": int(both_wnh),
                }
        print(f"  D149 actual both-parent data: {len(d149_both)} state×year points")

    # Step 1: For each state, collect ALL reliable WNH calibration points
    all_calibration_points = {}

    for state in df["state"].unique():
        st_df = df[df["state"] == state].sort_values("year")
        points = []

        cdc = st_df[
            st_df["source"].str.startswith("CDC WONDER")
            & st_df["pct_white_nh"].notna()
            & st_df["pct_white"].notna()
            & (st_df["pct_white"] > 0)
        ]
        for _, row in cdc.iterrows():
            points.append({
                "year": int(row["year"]),
                "ratio": row["pct_white_nh"] / row["pct_white"],
            })

        nber = st_df[
            st_df["source"].str.startswith("NBER")
            & st_df["pct_white_nh"].notna()
            & st_df["pct_white"].notna()
            & (st_df["pct_white"] > 0)
            & (st_df["pct_white_nh"] > 0)
        ]
        for _, row in nber.iterrows():
            points.append({
                "year": int(row["year"]),
                "ratio": row["pct_white_nh"] / row["pct_white"],
                "is_nber": True,
            })

        all_calibration_points[state] = points

    # Step 2: Determine which states have reliable NBER data
    nber_reliable = set()
    for state in df["state"].unique():
        nber_1994 = df[
            (df["state"] == state) & (df["year"] == 1994)
            & df["source"].str.startswith("NBER") & df["pct_white_nh"].notna()
            & (df["pct_white"] > 0)
        ]
        cdc_1995 = df[
            (df["state"] == state) & (df["year"] == 1995)
            & df["source"].str.startswith("CDC") & df["pct_white_nh"].notna()
            & (df["pct_white"] > 0)
        ]
        if len(nber_1994) > 0 and len(cdc_1995) > 0:
            nber_ratio = nber_1994.iloc[0]["pct_white_nh"] / nber_1994.iloc[0]["pct_white"]
            cdc_ratio = cdc_1995.iloc[0]["pct_white_nh"] / cdc_1995.iloc[0]["pct_white"]
            ratio_diff = abs(nber_ratio - cdc_ratio)
            if ratio_diff < 0.03:
                nber_reliable.add(state)

    for state in df["state"].unique():
        if state not in nber_reliable:
            all_calibration_points[state] = [
                p for p in all_calibration_points[state] if not p.get("is_nber")
            ]

    def get_nearest_calibration(state, year):
        points = all_calibration_points.get(state, [])
        if not points:
            hisp_pct = CENSUS_1990_HISPANIC_PCT.get(state, 1.0)
            return {"year": 1990, "ratio": max(0.5, 1.0 - (hisp_pct / 100.0) * 1.5)}
        best = min(points, key=lambda p: abs(p["year"] - year))
        return best

    print(f"\n{len(nber_reliable)}/{len(df['state'].unique())} states have "
          f"reliable NBER WNH data (smooth 1994→1995 transition)")
    unreliable = set(df["state"].unique()) - nber_reliable
    if unreliable:
        print(f"  Unreliable (estimation only): {sorted(unreliable)}")

    def apply_both_parent_factor(state, mother_only_wnh, year):
        """Adjust mother-only WNH % to both-parent WNH using D149 factors.

        Pre-1980: No correction — birth certificates used "child's race"
        derived from both parents' races, so the data already reflects
        both-parent status.

        1980-2015: Gradually phase in the correction. Interracial marriage
        was ~3% in 1980 vs ~19% in 2016, so the 2016 factor is too
        aggressive for earlier years. Linear interpolation from factor=1.0
        at 1980 to the D149 factor at 2016.

        2016+: Handled by D149 actual data (Priority 1), not this function.
        """
        if not bp_factors:
            return mother_only_wnh
        if year < 1980:
            return mother_only_wnh

        f = bp_factors.get(state)
        if not f:
            avg = np.mean([v["factor"] for v in bp_factors.values()])
            f = {"factor": avg}

        d149_factor = f["factor"]

        if year >= 2016:
            return round(mother_only_wnh * d149_factor, 2)

        # 1980-2015: linearly interpolate from 1.0 (1980) to d149_factor (2016)
        t = (year - 1980) / (2016 - 1980)
        year_factor = 1.0 + t * (d149_factor - 1.0)
        return round(mother_only_wnh * year_factor, 2)

    # Step 3: Build the smooth WNH series
    output_rows = []

    for _, row in df.iterrows():
        year = int(row["year"])
        state = row["state"]
        pct_white = row["pct_white"]
        pct_white_nh = row["pct_white_nh"]
        source = row["source"]

        if pd.isna(pct_white) or pct_white <= 0:
            output_rows.append({
                **row.to_dict(),
                "pct_white_nh_smooth": np.nan,
                "wnh_method": "no_white_data",
            })
            continue

        # Priority 1: D149 actual both-parent WNH (2016+)
        d149_val = d149_both.get((year, state))
        if d149_val:
            output_rows.append({
                **row.to_dict(),
                "pct_white_nh_smooth": d149_val["pct"],
                "wnh_method": "d149_both_parent",
            })

        # Priority 2: CDC WONDER mother-only (1995-2015) → apply correction
        elif source.startswith("CDC WONDER") and not pd.isna(pct_white_nh):
            adjusted = apply_both_parent_factor(state, pct_white_nh, year)
            output_rows.append({
                **row.to_dict(),
                "pct_white_nh_smooth": adjusted,
                "wnh_method": "cdc_adjusted_both_parent",
            })

        # Priority 3: NBER actual for validated states → apply correction
        elif (state in nber_reliable
              and source.startswith("NBER")
              and not pd.isna(pct_white_nh)
              and pct_white_nh > 0):
            adjusted = apply_both_parent_factor(state, pct_white_nh, year)
            output_rows.append({
                **row.to_dict(),
                "pct_white_nh_smooth": adjusted,
                "wnh_method": "nber_adjusted_both_parent",
            })

        # Priority 4: Estimation from pct_white → apply correction
        else:
            nearest_cal = get_nearest_calibration(state, year)
            cal_year = nearest_cal["year"]
            cal_ratio = nearest_cal["ratio"]
            cal_hisp_pct = interpolate_hispanic_pct(state, cal_year)
            year_hisp_pct = interpolate_hispanic_pct(state, year)

            estimated_ratio = compute_nh_ratio_from_hispanic_pct(
                year_hisp_pct, cal_ratio, cal_hisp_pct
            )
            estimated_ratio = max(0.3, min(estimated_ratio, 1.0))

            estimated_wnh = pct_white * estimated_ratio
            estimated_wnh = max(0, min(estimated_wnh, pct_white))

            adjusted = apply_both_parent_factor(state, estimated_wnh, year)

            output_rows.append({
                **row.to_dict(),
                "pct_white_nh_smooth": round(adjusted, 2),
                "wnh_method": "estimated_both_parent",
            })

    smooth_df = pd.DataFrame(output_rows)

    # Column order
    cols = [
        "year", "state", "source", "total_births", "white_births",
        "white_nh_births", "nonwhite_births", "pct_white", "pct_white_nh",
        "pct_white_nh_smooth", "wnh_method", "race_category_type", "notes",
    ]
    smooth_df = smooth_df[[c for c in cols if c in smooth_df.columns]]
    smooth_df = smooth_df.sort_values(["year", "state"]).reset_index(drop=True)

    out_path = os.path.join(BASE, "extracted_data", "smooth_wnh.csv")
    smooth_df.to_csv(out_path, index=False)
    print(f"\nSmooth WNH: {len(smooth_df)} rows -> {out_path}")

    # Validation report
    print("\n" + "=" * 60)
    print("VALIDATION REPORT")
    print("=" * 60)

    print("\nMethod breakdown:")
    for method, count in smooth_df["wnh_method"].value_counts().items():
        print(f"  {method}: {count} rows")

    print("\nNational average pct_white_nh_smooth by year (should be smooth):")
    for year in range(1940, 2025, 5):
        sub = smooth_df[smooth_df["year"] == year]
        if len(sub) == 0:
            continue
        avg = sub["pct_white_nh_smooth"].mean()
        avg_w = sub["pct_white"].mean()
        n = sub["pct_white_nh_smooth"].notna().sum()
        print(f"  {year}: pct_white={avg_w:.1f}%  smooth_wnh={avg:.1f}%  ({n} states)")

    print("\nKey state series (should be smooth across 1988-1989):")
    for state in ["California", "Texas", "New York", "Florida", "Ohio", "New Mexico"]:
        sub = smooth_df[(smooth_df["state"] == state) & (smooth_df["year"].between(1985, 1996))]
        if len(sub) == 0:
            continue
        print(f"\n  {state}:")
        for _, r in sub.iterrows():
            orig = f"{r.pct_white_nh:.1f}" if pd.notna(r.pct_white_nh) else "N/A"
            smooth = f"{r.pct_white_nh_smooth:.1f}" if pd.notna(r.pct_white_nh_smooth) else "N/A"
            print(f"    {int(r.year)}: white={r.pct_white:.1f}  orig_wnh={orig:>6s}  "
                  f"smooth_wnh={smooth:>6s}  method={r.wnh_method}")

    # Check the critical 1994→1995 boundary (estimated→CDC)
    print("\n1994→1995 boundary check (estimated→CDC transition):")
    boundary_jumps = []
    for state in sorted(smooth_df["state"].unique()):
        r1994 = smooth_df[(smooth_df["state"] == state) & (smooth_df["year"] == 1994)]
        r1995 = smooth_df[(smooth_df["state"] == state) & (smooth_df["year"] == 1995)]
        if len(r1994) > 0 and len(r1995) > 0:
            v94 = r1994.iloc[0]["pct_white_nh_smooth"]
            v95 = r1995.iloc[0]["pct_white_nh_smooth"]
            if pd.notna(v94) and pd.notna(v95):
                jump = v95 - v94
                boundary_jumps.append((state, v94, v95, jump))
                if abs(jump) > 3.0:
                    print(f"  {state}: {v94:.1f} -> {v95:.1f} ({jump:+.1f})")
    if boundary_jumps:
        jumps = [j[3] for j in boundary_jumps]
        print(f"  Avg jump: {np.mean(jumps):+.2f}, Max: {max(jumps, key=abs):+.2f}")
        big = sum(1 for j in jumps if abs(j) > 3.0)
        print(f"  States with >3pt jump: {big}/{len(jumps)}")

    # Check for discontinuities > 3 points between consecutive years
    print("\nDiscontinuity check (>3pt year-over-year jumps in smooth_wnh):")
    disc_count = 0
    for state in smooth_df["state"].unique():
        st = smooth_df[smooth_df["state"] == state].sort_values("year")
        for i in range(1, len(st)):
            prev = st.iloc[i - 1]
            curr = st.iloc[i]
            if pd.notna(prev["pct_white_nh_smooth"]) and pd.notna(curr["pct_white_nh_smooth"]):
                jump = curr["pct_white_nh_smooth"] - prev["pct_white_nh_smooth"]
                if abs(jump) > 3.0 and int(curr["year"]) == int(prev["year"]) + 1:
                    disc_count += 1
                    if disc_count <= 15:
                        print(f"  {state} {int(prev.year)}->{int(curr.year)}: "
                              f"{prev.pct_white_nh_smooth:.1f} -> {curr.pct_white_nh_smooth:.1f} "
                              f"({jump:+.1f})")
    print(f"  Total discontinuities >3pt: {disc_count}")

    return smooth_df


if __name__ == "__main__":
    build_smooth_wnh()
