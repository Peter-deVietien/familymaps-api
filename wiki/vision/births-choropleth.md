# Feature Vision: Births Choropleth

## What It Is

State-level choropleth showing % of births where the baby is White Non-Hispanic (both parents WNH) from 1940 to present, with year-by-year navigation.

## Current State

- **Coverage:** 1940–2024 from 7 data sources (NHGIS, NBER Historical, NBER Microdata, CDC WONDER D10/D27/D66, CDC WONDER D149, KFF)
- **Metric:** Both-parent WNH — % of babies where both mother and father are White Non-Hispanic
- **Navigation:** Arrow keys + buttons to step through years
- **Legend:** "White NH Babies Born (%)" with "est." suffix for pre-1978
- **Tooltip:** "WNH Babies: X%"
- **Data source:** `GET /api/births` endpoint (reads `smooth_wnh.csv`)
- **Component:** `src/app/single-ratio/single-ratio.component.ts`

## ✅ Methodology: Both-Parent WNH (Resolved 2026-04-10)

Previously, data only measured mother's race/ethnicity, overstating WNH birth %. Now resolved:

**How it works:**
- **2016-2024:** CDC WONDER D149 actual both-parent WNH (father's race + Hispanic origin available in expanded database)
- **1980-2015:** Mother-only WNH adjusted by per-state correction factor from D149, linearly phased in from 1.0 (1980) to D149 factor (2016) to account for increasing interracial marriage over time
- **Pre-1980:** No correction needed — birth certificates used "child's race" determined algorithmically from both parents' races, so the data already reflects both-parent status. Hispanic adjustment still applied.

**National impact (2024):** Mother-only WNH was 49.1%, both-parent WNH is 39.1% (10pt gap). Correction factor averages 0.794, range 0.578 (Hawaii) to 0.878 (New Hampshire).

**Remaining limitation:** ~10% of births to WNH mothers have father's race "Unknown or Not Stated." These births are excluded from the both-parent WNH count in D149 data.

## Desired End State

<!-- NEEDS INPUT -->
- [ ] Should this go to county-level granularity? (data available for many years)
- [ ] Animation/playback across years? (auto-advance with play/pause)
- [ ] Comparison mode? (two years side by side, or delta view)
- [ ] What should happen for years with only partial WNH coverage (1978–1988)?
- [ ] Should we interpolate missing years (e.g., 1976-79, 1981-84, 1986-89 from NHGIS ds231 gaps)?
- [ ] Is there a minimum state threshold before showing WNH data for a year?

## Data Dependencies

Full source coverage matrix: `data/overview.md`

Key limitations:
- **1940–1977:** Only "White (incl. Hispanic)" — WNH impossible
- **1978–1988:** WNH available for 4–16 states only
- **1989–1994:** WNH available for 48–51 states
- **1995+:** Full WNH coverage

## ✅ Resolved: 1988→1989 Metric Switch Discontinuity

Previously, switching from `pct_white` to `pct_white_nh` at 1989 caused a massive visual cliff (avg -8.3 pts, worst NM -43.7 pts). **Resolved** by `build_smooth_wnh.py` which produces a continuous smooth series using Hispanic adjustment estimation for pre-1978 and calibrated factors for all years. The 1988→1989 transition is now smooth. Full analysis of the original issue in `wiki/learnings/data-quirks.md`.

## UX Questions

<!-- NEEDS INPUT -->
- [ ] What color scale? (current: presumably white→color gradient)
- [ ] Should states with missing data be grayed out or hidden?
- [ ] Should there be a timeline scrubber in addition to arrow navigation?
- [ ] Should clicking a state show its time series?

---

*Update when the user clarifies births layer goals or when data coverage changes.*
