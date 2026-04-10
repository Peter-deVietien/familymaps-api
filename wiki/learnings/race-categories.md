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

---

*Update when new race category findings emerge or when adding data from a new era.*
