#!/usr/bin/env python3
"""Build the served county singles JSON: single White non-Hispanic women aged
20-34 per single White NH man aged 20-34, for every county.

"Single" is anyone not currently married: never married, divorced, widowed or
separated.

The Census Bureau does not publish White NH marital status by age for
counties (its White NH marital status table, B12002H, has no age detail), so
this joins two ACS 2020-2024 5-year sources:

    head counts   White NH women and men aged 20-34 in each county (B01001H)
    single share  share of White NH women and of men aged 20-34 who are not
                  married, tabulated from the PUMS microdata for each Public
                  Use Microdata Area (PUMA, ~100k+ people)

    single women  = county women x the women's single share
    single men    = county men   x the men's single share
    ratio         = single women / single men

A county's single share is the average over its tracts' PUMAs, weighted by
each tract's White NH 20-34 population of that sex, so a county split across
PUMAs gets its own mix and rural counties sharing a PUMA get the PUMA's share.
The head counts are the county's own, so college towns and military bases
still show their skew.

Small samples:
- A PUMA's single share is blended with PRIOR_RECORDS sample records' worth of
  its state's share, which only matters for PUMAs with few White NH 20-34
  respondents.
- Census's county head counts by race, sex and age are noisy in small
  counties, so each county's single women and men are blended with
  PRIOR_SINGLES singles' worth of its state's mix before the ratio is taken.
  single_ratio_wnh_raw keeps the unblended figure.

Puerto Rico has its own PUMS file and is almost entirely Hispanic, so its
municipios are null.

Needs a Census API key in census_api_key or CENSUS_API_KEY
(https://api.census.gov/data/key_signup.html).

Usage:
    python3 scripts/build_singles_dataset.py [--dry-run]
"""

from __future__ import annotations

import argparse
import csv
import json
import os
import sys
import urllib.parse
import urllib.request
from collections import defaultdict
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
RAW_DIR = REPO_ROOT / "data" / "census_acs" / "raw-data"
CROSSWALK_URL = (
    "https://www2.census.gov/geo/docs/maps-data/data/rel2020/"
    "2020_Census_Tract_to_2020_PUMA.txt"
)
CROSSWALK = RAW_DIR / "2020_Census_Tract_to_2020_PUMA.txt"
ROSTER = REPO_ROOT / "app" / "data" / "US_county_percentages.json"
TARGET = REPO_ROOT / "app" / "data" / "US_county_singles.json"

API = "https://api.census.gov/data/2024/acs/acs5"
PRIOR_RECORDS = 30
PRIOR_SINGLES = 500

# B01001H White NH by sex and age: 20-24, 25-29, 30-34.
MEN_VARS = ["B01001H_008E", "B01001H_009E", "B01001H_010E"]
WOMEN_VARS = ["B01001H_023E", "B01001H_024E", "B01001H_025E"]

# PUMS codes.
WHITE_ALONE = "1"
NOT_HISPANIC = "01"
MARRIED = "1"
MALE, FEMALE = "1", "2"


def api_key() -> str:
    key = os.environ.get("census_api_key") or os.environ.get("CENSUS_API_KEY")
    if not key:
        sys.exit("set census_api_key or CENSUS_API_KEY to a Census API key")
    return key


def fetch_json(path: str, params: dict[str, str], cache: Path) -> list[list[str]]:
    """Census API response, cached under RAW_DIR so reruns stay offline."""
    if cache.exists():
        return json.loads(cache.read_text())
    query = urllib.parse.urlencode({**params, "key": api_key()}, safe=":*,")
    with urllib.request.urlopen(f"{API}{path}?{query}", timeout=300) as resp:
        rows = json.loads(resp.read())
    cache.parent.mkdir(parents=True, exist_ok=True)
    cache.write_text(json.dumps(rows))
    return rows


def load_crosswalk() -> dict[str, str]:
    """Tract GEOID -> state + PUMA."""
    if not CROSSWALK.exists():
        CROSSWALK.parent.mkdir(parents=True, exist_ok=True)
        print(f"downloading {CROSSWALK_URL}")
        urllib.request.urlretrieve(CROSSWALK_URL, CROSSWALK)
    with CROSSWALK.open(newline="", encoding="utf-8-sig") as fh:
        return {
            r["STATEFP"] + r["COUNTYFP"] + r["TRACTCE"]: r["STATEFP"] + r["PUMA5CE"]
            for r in csv.DictReader(fh)
        }


def puma_single_shares(states: list[str]) -> tuple[dict, dict]:
    """Single share of White NH 20-34 by (PUMA, sex) and by (state, sex)."""
    # (area, sex) -> [single weight, total weight, records]
    puma = defaultdict(lambda: [0.0, 0.0, 0])
    state = defaultdict(lambda: [0.0, 0.0, 0])
    for st in states:
        rows = fetch_json(
            "/pums",
            {
                "get": "PWGTP,SEX,MAR,PUMA",
                "RAC1P": WHITE_ALONE,
                "HISP": NOT_HISPANIC,
                "AGEP": "20:34",
                "for": f"state:{st}",
            },
            RAW_DIR / "pums_wnh_20_34" / f"{st}.json",
        )
        header = rows[0]
        i_w, i_sex, i_mar, i_puma = (header.index(c) for c in ("PWGTP", "SEX", "MAR", "PUMA"))
        for r in rows[1:]:
            weight = int(r[i_w])
            single = r[i_mar] != MARRIED
            for acc in (puma[(st + r[i_puma], r[i_sex])], state[(st, r[i_sex])]):
                acc[0] += weight * single
                acc[1] += weight
                acc[2] += 1

    state_share = {k: s / t for k, (s, t, _) in state.items() if t > 0}
    puma_share = {}
    for (area, sex), (s, t, n) in puma.items():
        prior = state_share[(area[:2], sex)]
        puma_share[(area, sex)] = (n * s / t + PRIOR_RECORDS * prior) / (n + PRIOR_RECORDS)
    return puma_share, state_share


def county_head_counts() -> dict[str, tuple[int, int]]:
    rows = fetch_json(
        "",
        {"get": ",".join(WOMEN_VARS + MEN_VARS), "for": "county:*"},
        RAW_DIR / "b01001h_counties.json",
    )
    header = rows[0]
    out = {}
    for r in rows[1:]:
        rec = dict(zip(header, r))
        women = sum(int(rec[v]) for v in WOMEN_VARS)
        men = sum(int(rec[v]) for v in MEN_VARS)
        out[rec["state"] + rec["county"]] = (women, men)
    return out


def tract_head_counts(states: list[str]) -> dict[str, tuple[int, int]]:
    out = {}
    for st in states:
        rows = fetch_json(
            "",
            {"get": ",".join(WOMEN_VARS + MEN_VARS), "for": "tract:*", "in": f"state:{st} county:*"},
            RAW_DIR / "b01001h_tracts" / f"{st}.json",
        )
        header = rows[0]
        for r in rows[1:]:
            rec = dict(zip(header, r))
            women = sum(int(rec[v]) for v in WOMEN_VARS)
            men = sum(int(rec[v]) for v in MEN_VARS)
            out[rec["state"] + rec["county"] + rec["tract"]] = (women, men)
    return out


def tract_puma(tract: str, crosswalk: dict[str, str], by_state_tract: dict[str, str | None]) -> str | None:
    """Connecticut's 2022 switch to planning regions changed its tracts' county
    codes but not their tract codes, so fall back to state + tract code."""
    return crosswalk.get(tract) or by_state_tract.get(tract[:2] + tract[5:])


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    crosswalk = load_crosswalk()
    by_state_tract: dict[str, str | None] = {}
    for tract, puma in crosswalk.items():
        key = tract[:2] + tract[5:]
        by_state_tract[key] = puma if by_state_tract.get(key, puma) == puma else None
    roster = json.loads(ROSTER.read_text())
    states = sorted({e["GEOID"][:2] for e in roster} - {"72"})

    puma_share, state_share = puma_single_shares(states)
    counties = county_head_counts()
    tracts = tract_head_counts(states)

    # County single share by sex: tract-population-weighted mean of PUMA shares.
    weighted = defaultdict(lambda: [0.0, 0.0, 0.0, 0.0])  # women x share, women, men x share, men
    unmatched = 0
    for tract, (women, men) in tracts.items():
        puma = tract_puma(tract, crosswalk, by_state_tract)
        st = tract[:2]
        if puma is None or (puma, FEMALE) not in puma_share:
            unmatched += women + men
            f_share, m_share = state_share[(st, FEMALE)], state_share[(st, MALE)]
        else:
            f_share, m_share = puma_share[(puma, FEMALE)], puma_share.get((puma, MALE), state_share[(st, MALE)])
        acc = weighted[tract[:5]]
        acc[0] += women * f_share
        acc[1] += women
        acc[2] += men * m_share
        acc[3] += men

    singles: dict[str, tuple[float, float]] = {}
    state_singles = defaultdict(lambda: [0.0, 0.0])
    for geoid, (women, men) in counties.items():
        st = geoid[:2]
        if st == "72":
            continue
        acc = weighted.get(geoid)
        f_share = acc[0] / acc[1] if acc and acc[1] > 0 else state_share[(st, FEMALE)]
        m_share = acc[2] / acc[3] if acc and acc[3] > 0 else state_share[(st, MALE)]
        singles[geoid] = (women * f_share, men * m_share)
        state_singles[st][0] += women * f_share
        state_singles[st][1] += men * m_share

    out = []
    for entry in roster:
        geoid = entry["GEOID"]
        heads = counties.get(geoid)
        s = singles.get(geoid)
        raw = smoothed = None
        if s is not None:
            f, m = s
            raw = f / m if m > 0 else None
            sf, sm = state_singles[geoid[:2]]
            f_mix = sf / (sf + sm)
            smoothed = (f + PRIOR_SINGLES * f_mix) / (m + PRIOR_SINGLES * (1 - f_mix))
        out.append(
            {
                "GEOID": geoid,
                "name": entry["name"],
                "total_pop": entry.get("total_pop"),
                "wnh_women_20_34": heads[0] if heads and s else None,
                "wnh_men_20_34": heads[1] if heads and s else None,
                "wnh_single_women_20_34": round(s[0]) if s else None,
                "wnh_single_men_20_34": round(s[1]) if s else None,
                "single_ratio_wnh_raw": round(raw, 3) if raw is not None else None,
                "single_ratio_wnh": round(smoothed, 3) if smoothed is not None else None,
            }
        )

    us_f = sum(v[0] for v in state_singles.values())
    us_m = sum(v[1] for v in state_singles.values())
    total_tract_pop = sum(w + m for w, m in tracts.values())
    print(f"roster counties: {len(roster)}")
    print(f"PUMAs: {len({p for p, _ in puma_share})}, tracts: {len(tracts)}")
    print(f"tract population with no PUMA match: {unmatched} of {total_tract_pop}")
    print(f"US single White NH 20-34: {us_f:,.0f} women, {us_m:,.0f} men, ratio {us_f / us_m:.3f}")
    for key in ("single_ratio_wnh_raw", "single_ratio_wnh"):
        values = sorted(c[key] for c in out if c[key] is not None)
        print(
            f"{key}: {len(values)}/{len(out)} populated, min {values[0]}, "
            f"median {values[len(values) // 2]}, max {values[-1]}"
        )
    missing = [c["GEOID"] for c in out if c["single_ratio_wnh"] is None and not c["GEOID"].startswith("72")]
    print(f"non-PR counties missing single_ratio_wnh: {missing}")

    if args.dry_run:
        print("\ndry run - nothing written")
        return 0

    TARGET.write_text(json.dumps(out))
    print(f"\nwrote {TARGET}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
