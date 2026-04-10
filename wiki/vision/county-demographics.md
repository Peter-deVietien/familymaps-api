# Feature Vision: County Demographics

## What It Is

County-level choropleth layers showing current White NH population percentage, with configurable range sliders to highlight counties in a target range.

## Current State

- **Layers:** County (all US), County Under-5, Florida tracts, Florida block groups
- **Controls:** Range sliders for filtering demographic percentage
- **Data:** Census-derived demographics via API endpoints

## Desired End State

<!-- NEEDS INPUT -->
- [ ] Should this expand beyond White NH %? (age distribution, income, education)
- [ ] Should range sliders support multiple demographics simultaneously?
- [ ] Should there be a "find counties like this one" feature?
- [ ] Is the under-5 layer a permanent feature or exploratory?

## Data Sources

- `GET /api/demographics/us_counties` — county demographics
- `GET /api/demographics/us_counties_under5` — under-5 demographics
- `GET /api/demographics/us_counties_percentages` — WDWWA factors

---

*Update when new demographic layers are added or filter logic changes.*
