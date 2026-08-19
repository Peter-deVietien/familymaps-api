# CDC PLACES — County Adult Obesity

> Source of the `us_counties_obesity` dataset. Read when touching the obesity metric or adding another PLACES health measure (they all come from the same file for free).

## Why This Source

PLACES is the only source that publishes an obesity estimate for **every US county** on a **recurring annual schedule**, keyed on 5-digit county FIPS. It is the same data County Health Rankings and the USDA Food Environment Atlas republish, so going straight to PLACES avoids a hop.

| | |
|---|---|
| **API** | Socrata: `https://data.cdc.gov/resource/{dataset}.json` |
| **Auth** | None. No key, no rate limit hit at these volumes |
| **Coverage** | 50 states + DC. **No Puerto Rico**, no territories |
| **Volume** | One request per release (~6k rows), ~2 s total |
| **Licence** | Public domain |

### Dataset ids

Each release year is a **separate Socrata dataset** with its own id — there is no single "latest" URL, so adding a newer release means adding an id.

| Release | Dataset id | BRFSS year | Counties w/ obesity |
|---|---|---|---|
| 2025 | `swc5-untb` | 2023 | 2,956 |
| 2024 | `fu4u-a9bh` | 2022 | 3,144 |
| 2023 | `h3ej-a9ec` | 2021 | — |
| 2022 | `duw2-7jbt` | 2020 | — |

Tract-level equivalents exist under different ids (2025 tracts = `cwsq-ngmh`) if the FL tract layer ever wants this.

## ⚠️ The 2025 release is missing two entire states

BRFSS produced no usable 2023 data for **Kentucky (120 counties) and Pennsylvania (67)**, so they are absent from the 2025 release — not null, *absent*. Querying `stateabbr=KY` returns an empty array.

This matters more than it sounds: the frontend rank algorithm drops any county with a null field, so naively adopting the newest release would have unranked 187 extra counties and left both states blank on the map.

`download_cdc_places_obesity.py` therefore pulls **both releases and coalesces**, newest first, recording the BRFSS year per county. 2,956 counties are BRFSS 2023; 188 fall back to BRFSS 2022. Mixing years is what CDC itself does — the 2025 release already carries 5 of its 40 measures over from BRFSS 2022.

## ⚠️ A national aggregate hides in the county file

The county dataset includes a **United States** row under `locationid = "59"`, which is neither a county nor a state FIPS. It slipped into the join as an orphan on the first run. The download script now drops any `locationid` that is not 5 digits.

It is worth keeping as a sanity check though: `59` reads 32.8% for BRFSS 2023, matching CDC's published national adult obesity rate.

## Measure Definition

`measureid = OBESITY` → share of adults **18 and over** with BMI ≥ 30, from self-reported height and weight.

Two value types per county, both of which we store:

| `datavaluetypeid` | Field | Meaning |
|---|---|---|
| `CrdPrv` | `obesity_pct` | Crude — the actual share of that county's adults |
| `AgeAdjPrv` | `obesity_pct_age_adj` | Reweighted to a standard age distribution |

### Neither one is age-specific

This is the trap worth naming, because "age-adjusted" reads like an age breakdown. **PLACES has no age stratification at any geography.** Both value types cover all adults 18+; age-adjustment only neutralises the county's age *composition* so a retirement county and a college town compare fairly. Confirmed directly — `OBESITY` has exactly two value types and no others.

If county-level obesity *by age group* is ever needed, the only source is IHME's [US High BMI dataset](https://ghdx.healthdata.org/us-high-bmi-prevalence-ylls-2000-2019) (county × age × sex × race, plus mean BMI), which ends at **2019** and is **non-commercial licence only**.

### Self-report understates the level

BRFSS asks people their height and weight over the phone; NHANES physically measures them. Self-report runs several points low. The **geographic spread is the usable signal, not the absolute value.**

## Small-Area Model Caveat

Values are **modelled, not measured**. PLACES applies multilevel regression and poststratification: a small county's estimate is largely predicted from its ACS demographic profile plus its state's BRFSS mean. So the map shows more apparent local signal than genuinely exists, and confidence intervals are wide for small counties (Twiggs County, GA: 39.7%, CI 31.3–48.1%). We store `ci_low` / `ci_high` so the tooltip can be honest about this.

CDC explicitly warns against using PLACES for program or policy evaluation.

## Observed Distribution (BRFSS 2023/2022 coalesced)

| | |
|---|---|
| Range | 16.7% (Boulder County, CO) – 52.9% (Perry County, AL) |
| Median county | 38.0% |
| National (population-weighted) | 32.8% |

The median county sits ~5 points above the national rate because small rural counties are heavier and the national figure is population-weighted toward big metros. Leanest counties are dense/affluent (Boulder, San Francisco 17.2%, Manhattan 19.2%); heaviest cluster in the Mississippi/Alabama Black Belt.

## GEOID Notes

**No crosswalk needed.** Both releases already use Connecticut's nine **planning regions** (`09110` Capitol, etc.), matching the ACS 2023 GEOIDs in `US_county_percentages.json`. This is unlike nClimGrid, which still reports the legacy CT counties and needs a crosswalk.

Of the 3,222 roster counties, **3,144 match** and 78 are null — all Puerto Rico.

## Other Measures Available Free

The same request returns 40 measures; only `measureid` changes. Relevant ones: `LPA` (physical inactivity), `DIABETES`, `CSMOKING`, `BPHIGH`, `SLEEP` (short sleep), `GHLTH` (fair/poor health), `DEPRESSION`.

## Scripts

```bash
python3 scripts/download_cdc_places_obesity.py   # both releases -> CSV
python3 scripts/build_obesity_dataset.py [--dry-run]
```

Output lands in `data/extracted_data/county_obesity.csv` (gitignored) and builds `app/data/US_county_obesity.json` (committed and served at `/api/demographics/us_counties_obesity`). The frontend paints that file as its own layer and joins crude `obesity_pct` onto the WDWWA rank as the 8th factor (`reverse: true`).

The build step joins onto the county roster in `US_county_percentages.json` so the output always carries the same 3,222 counties in the same order as every other county dataset, with canonical display names. PLACES' own `locationname` is a bare stem ("Orleans", "Capitol") that cannot be turned into a display name without knowing whether the county is a parish, borough, independent city or planning region.

---

*See also: [overview.md](overview.md) · [../architecture/backend-api-contract.md](../architecture/backend-api-contract.md) · [../learnings/data-quirks.md](../learnings/data-quirks.md)*
