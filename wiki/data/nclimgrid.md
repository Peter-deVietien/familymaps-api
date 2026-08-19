# NOAA nClimGrid-Daily — County Climate

> Source of the `pleasant_days` WDWWA rank factor. Read when touching the climate metric or adding another weather variable.

## Why This Source

NCEI publishes nClimGrid-Daily **already aggregated to county polygons**, so we get daily county values without doing zonal statistics against our own TopoJSON. That is the entire reason this source was chosen over PRISM or gridMET, which are gridded and would need real geoprocessing.

| | |
|---|---|
| **Base URL** | `https://www.ncei.noaa.gov/data/nclimgrid-daily/access/averages/{year}/` |
| **File pattern** | `{var}-{YYYYMM}-cty-scaled.csv` where var ∈ `tmax`, `tmin`, `prcp` |
| **Coverage** | 3,107 CONUS counties + DC. **No Alaska, no Hawaii.** 1951–present |
| **Units** | Temperature °C, precipitation mm |
| **Auth** | None. No API key, no rate limiting encountered at 8 concurrent workers |
| **Volume** | ~1 MB per file. 1995–2024 × 3 vars = 1,080 files ≈ 1 GB, ~85 s to download |

## Row Format

No header. One row per county per month, with one column per day:

```
cty,{CODE},{ST: County Name},{YYYY},{MM},{VAR},{day1},{day2},...,{dayN}
```

### ⚠️ The leading digits are NOT a FIPS state code

This is the single biggest trap in this dataset. NCEI numbers the CONUS states **01–48 alphabetically**, omitting Alaska and Hawaii entirely. So:

| NCEI code | Actually means | Would be misread as |
|---|---|---|
| `01001` | Autauga County, **Alabama** | Autauga County, Alabama ✅ |
| `04013` | Contra Costa County, **California** | Maricopa County, Arizona ❌ |
| `17031` | York County, **Maine** | Cook County, Illinois ❌ |
| `18511` | **District of Columbia** | Somerset County, Maryland ❌ |

Alabama is `01` under both schemes, so **checking the first row of the file falsely confirms that the codes are FIPS**. Every row after Arizona is silently wrong. This cost a full recompute cycle on 2026-08-19.

The trailing **three** digits *are* a real county FIPS. `compute_pleasant_days.py` therefore rebuilds each GEOID as `STATE_FIPS[abbrev] + code[-3:]`, taking the state abbreviation from the name field. DC is special-cased: NCEI files it as `18511` under Maryland, but its Census code is `11001`.

Verification: every rebuilt GEOID's county name matches `US_county_percentages.json` exactly.

## Pleasant Days Metric

A day counts as pleasant when **all** of these hold:

| Condition | Threshold | Source units |
|---|---|---|
| High temperature | 60–85°F | 15.56–29.44 °C |
| Low temperature | 40–68°F | 4.44–20.0 °C |
| Precipitation | below measurable | < 0.254 mm |

The metric is `pleasant_days / valid_days × 365.25`, normalising over gaps rather than assuming complete records. Computed over **1995–2024** (30 years, 10,958 valid days per county).

**The 68°F ceiling on the overnight low is doing real work.** nClimGrid carries no humidity variable, but warm nights track high dewpoint closely, so that bound is a humidity proxy. Without it a muggy Gulf Coast night scores identically to a dry Mountain West one — a serious problem given how many high-Trump, high-White-NH counties are Southern.

### Known bias

Requiring the high *and* the low to both land in range penalises large diurnal swings, which favours maritime climates over continental ones. Coastal California sweeps the top; high-altitude Colorado bottoms out. This is inherent to the definition rather than a bug, but it means dry inland counties with lovely afternoons and cold mornings score lower than a resident would judge them.

| | Days/yr |
|---|---|
| Min | 18.5 — Lake County, CO (Leadville, ~10,000 ft) |
| Median | 79.8 |
| Max | 254.2 — Orange County, CA |

## GEOID Crosswalks

Two Census geographies have no nClimGrid counterpart and are mapped in `add_pleasant_days_field.py`:

- **Connecticut** retired its 8 counties for 9 planning regions in 2022. ACS 2023 uses the new GEOIDs; nClimGrid still reports legacy counties. Each region borrows the county covering most of it. Values span 74.8–89.6 days statewide, too wide to justify one statewide average. Tolland County goes unused because it splits across two regions rather than dominating either.
- **Lexington city, VA** (`51678`) is an independent-city enclave inside Rockbridge County (`51163`), too small for nClimGrid to resolve.

## Scripts

```bash
python3 scripts/download_nclimgrid.py --start 1995 --end 2024   # resumable, skips cached
python3 scripts/compute_pleasant_days.py --start 1995 --end 2024
python3 scripts/add_pleasant_days_field.py [--dry-run]
```

Output lands in `data/extracted_data/county_pleasant_days.csv` (gitignored) and merges into `app/data/US_county_percentages.json` (committed and served).

Raw CSVs in `data/nclimgrid/` are gitignored by the existing `data/**/*.csv` rule.

---

*See also: [overview.md](overview.md) · [../learnings/data-quirks.md](../learnings/data-quirks.md)*
