# Race Categories on Birth Certificates by Era

> Reference for understanding what race/ethnicity data exists in each historical period. Read this when working with birth data across eras or when encountering unfamiliar race category labels.

## Timeline

| Period | Race? | Hispanic Origin? | Best Available Category |
|--------|-------|-----------------|------------------------|
| 1940–1977 | Yes (child's race) | **No** | White / Nonwhite only |
| 1978–1992 | Yes (child→mother 1980) | Partial (expanding states) | White / Nonwhite + partial White NH |
| 1993–present | Yes (mother's race) | **Yes — all states** | White Non-Hispanic |
| 2003–present | Multiple race allowed | Yes | Bridged-race for backward compat (through 2019) |

**Key implication:** True "White non-Hispanic" at the state level is only cleanly available from ~1993+. For 1940–1977, only "White" (includes Hispanic whites) exists. For 1978–1992, Hispanic origin data exists for a growing subset of states.

## Race Category Evolution in Data Sources

- **Pre-1959:** White / Nonwhite only (NHGIS ds224, ds229; NBER Historical)
- **1959–1972:** White / Negro / Other (NHGIS ds230)
- **1973–1979:** Child's race (`crace`): 1=White, 2=Black, etc. No Hispanic field.
- **1978+:** Hispanic origin begins (partial states, expanding)
- **1980+:** Mother's race (`mrace`) replaces child's race
- **1993+:** White Non-Hispanic cleanly available in all states
- **2003+:** Multiple-race categories; bridged-race for backward compatibility (through 2019)

## NBER Microdata Schema Changes (Critical)

| Era | State Field | Race Field | Hispanic Field | Notes |
|-----|-------------|-----------|---------------|-------|
| 1973–1979 | `stateres` (NCHS alpha 1-51) | `crace` (child) | `origm` (1978+ only, 4-6 states) | |
| 1980–1988 | `stateres` (NCHS alpha 1-51) | `mrace` (mother) | `origm` (8-16 states) | |
| 1989–1994 | `stresfip` (FIPS codes) | `mrace` (mother) | **`ormoth`** — NOT `origm`! | `origm` became binary flag in 1989+ |

### The origm → ormoth Bug (2026-04-10)

In 1989+ files, `origm` was recoded to a binary flag (value=1 for ~99.8% of rows). The correct field for Hispanic origin is `ormoth` (0=Non-Hispanic, 1-5=Hispanic subcategories, 9=Unknown). Using `origm` caused all WNH counts for 1989-1994 to be zero.

## NCHS Alpha State Codes (pre-1989)

States numbered 1-51 alphabetically. DC is between Delaware (8) and Florida (10):
1=Alabama, 2=Alaska, 3=Arizona, ..., 9=District of Columbia, ..., 51=Wyoming.
Codes 52+ are territories (excluded from analysis).

## KFF "White" = White Non-Hispanic

Cross-validated exact match with CDC WONDER White NH for all checked states (2016-2023). KFF footnote confirms: "persons of Hispanic origin may be of any race" — Hispanic listed separately.

## ✅ Mother's Race ≠ Baby's Race (Resolved)

**All post-1980 raw data uses mother's race, not the baby's race.** This means "White NH births" in the source data really means "births to White NH mothers." Our pipeline corrects this using D149 father's race data and historical phase-in (see `data/overview.md`).

### Father's Race Data Availability

| Source | Years | Father's Race? | Father's Hispanic? |
|--------|-------|---------------|-------------------|
| NHGIS / NBER Historical (pre-1973) | 1940-1972 | N/A — uses child's race (from both parents) | No |
| NBER Microdata | 1973-2004 | ✅ `frace` field in raw microdata | Partial (from `origf`/`orfath`) |
| CDC WONDER D10/D27/D66 | 1995-2024 | ❌ Mother's characteristics only | ❌ |
| CDC WONDER D149 (Expanded) | 2016-2024 | ✅ Paternal Race (6/15/31 categories) | ✅ Father's Hispanic Origin |
| KFF | 2016-2023 | ❌ | ❌ |

### Child's Race Algorithm (pre-1980)

Before 1980, the race on birth certificates was the **child's race**, determined by an algorithm:
- If both parents same race → child = that race
- If one parent White → child = other parent's race
- If neither parent White → child = father's race

This means pre-1980 "White" births required BOTH parents to be White, which is actually what we want. However, Hispanic origin was not tracked, so "White" includes Hispanic.

### Missing Father Data Problem

~15-30% of births (rising over time with increasing unmarried births, now ~40% of all births) have father's race "Unknown or Not Stated." Our approach:
- **2016+:** Use D149 actual data, which counts only births where father is explicitly WNH (option 1 — conservative). ~10% of WNH-mother births have unknown father race.
- **1980-2015:** Apply per-state correction factor from D149, linearly phased in from 1.0 (1980) to the D149 factor (2016), reflecting increasing interracial marriage.
- **Pre-1980:** No correction needed — "child's race" was already derived from both parents.

---

*Update when new race category findings emerge or when adding data from a new era.*
