# Feature Vision: Births Choropleth

## What It Is

State-level choropleth showing % White (NH where available) births from 1940 to present, with year-by-year navigation.

## Current State

- **Coverage:** 1940–2024 from 6 data sources (NHGIS, NBER Historical, NBER Microdata, CDC WONDER D10/D27/D66, KFF)
- **Navigation:** Arrow keys + buttons to step through years
- **Legend:** Dynamically labels "White NH" vs "White (incl. Hispanic)" based on era
- **Data file:** `public/births-data.json` (generated from `best_estimate.csv`)
- **Component:** `src/app/single-ratio/single-ratio.component.ts`

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

## Known Issue: 1988→1989 Metric Switch Discontinuity

**Problem:** `births-data.json` currently switches from `pct_white` (White incl. Hispanic) to `pct_white_nh` (White NH) at 1989. This creates a visual cliff — e.g., Texas drops from 84% to 49% in one year. Average jump across all states: **-8.28 points**. Worst: New Mexico at **-43.65 points**. Full analysis in `wiki/learnings/data-quirks.md`.

### Proposed Solutions

- [ ] **Option A: Move the switch to 1995 (recommended).** Show `pct_white` through 1994, `pct_white_nh` from 1995+. The transition aligns with the CDC WONDER data source boundary where WNH data is authoritative and complete for all states. The NBER Microdata WNH values (1989–1994) have quality issues — varying unknown rates and a -7 point discrepancy with CDC WONDER for New York — so it's safer to treat them as reference data rather than display data. Drawback: 6 extra years of "White incl. Hispanic" that could show WNH.

- [ ] **Option B: Per-state metric selection.** For each state×year, use `pct_white_nh` if available, otherwise `pct_white`. This avoids the nationwide cliff (e.g., Texas transitions smoothly at 50.49% → 49.00% from 1988 to 1989 since it has WNH in both years). But different states would use different metrics in the same year, and the unknown-rate issues in some states would still cause smaller discontinuities.

- [ ] **Option C: Adjusted WNH estimates for 1978–1988.** For states with `origm` data, redistribute unknown-Hispanic-origin births proportionally. Testing shows this eliminates NY's 12-point gap (43.88% → 55.59% adjusted, matching 1989's 55.86%). But it's speculative estimation and worsens some states (CT adjusted gap: -6.88).

- [ ] **Option D: Visual transition indicator.** Keep the current switch at 1989 but add a clear visual marker (vertical line, color shift, or label change animation) to signal the metric change to the user.

## UX Questions

<!-- NEEDS INPUT -->
- [ ] What color scale? (current: presumably white→color gradient)
- [ ] Should states with missing data be grayed out or hidden?
- [ ] Should there be a timeline scrubber in addition to arrow navigation?
- [ ] Should clicking a state show its time series?

---

*Update when the user clarifies births layer goals or when data coverage changes.*
