# Feature Vision: Florida Detail Layers

## What It Is

Higher-granularity demographic layers for Florida: census tracts and block groups, showing White NH population percentage.

## Current State

- **Layers:** FL tracts, FL block groups (on the single-ratio page)
- **Data:** Tract and block group TopoJSON + demographics via API
- **API endpoints:**
  - `GET /api/geo/fl_tracts`, `GET /api/geo/fl_block_groups`
  - `GET /api/demographics/fl_tracts`, `GET /api/demographics/fl_block_groups`

## Desired End State

<!-- NEEDS INPUT -->
- [ ] Why Florida specifically? Is this a prototype for expanding to all states?
- [ ] Should other states get tract/block-group layers too?
- [ ] Is there a plan to add more data fields beyond White NH % at tract level?
- [ ] Should the detail layers be visible at all zoom levels or only when zoomed into FL?

## Open Questions

<!-- NEEDS INPUT -->
- [ ] How is the FL data generated? (Census API scripts in `scripts/`)
- [ ] What Census vintage is current? (2020 decennial? ACS 5-year?)
- [ ] Should this auto-update when new Census data releases?

---

*Update when Florida layers expand or generalize to other states.*
