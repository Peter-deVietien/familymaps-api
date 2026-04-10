# Product Vision

> High-level vision for FamilyMaps as a whole. Fill in the open questions below to guide all feature development.

## What FamilyMaps Is

A demographic visualization tool that overlays racial/ethnic composition data on interactive maps across US geographies and over time. Built as an Angular SPA with a FastAPI backend.

## Target Users

<!-- NEEDS INPUT -->
- [ ] Who is the primary audience? (personal research tool / public site / specific community)
- [ ] What decisions should the tool help users make?
- [ ] Is there a specific use case driving the project? (e.g., choosing where to live, understanding demographic trends)

## North Star

<!-- NEEDS INPUT -->
- [ ] What single metric or outcome defines success for this tool?
- [ ] What should a user walk away knowing after 5 minutes with FamilyMaps?

## Feature Roadmap

Current features (see individual vision pages for detail):
1. **Births Choropleth** — historical White birth % by state → `births-choropleth.md`
2. **WDWWA Ranking** — composite county scoring → `wdwwa-ranking.md`
3. **County Demographics** — current White NH % by county → `county-demographics.md`
4. **Florida Detail** — tract/block group granularity for FL → `florida-detail.md`
5. **Church Events** — church event directory → `church-events.md`

### Planned / Desired Features

<!-- NEEDS INPUT -->
- [ ] Are there additional map layers or data overlays planned?
- [ ] Should there be user accounts, saved searches, or sharing?
- [ ] Is there a mobile app or just web?
- [ ] Should the tool expand beyond the US?
- [ ] Are there other demographic metrics beyond race/ethnicity? (income, education, religion, etc.)

## Design Principles

<!-- NEEDS INPUT — validate or modify these -->
1. **Data-first** — the map should feel like a window into real data, not a curated narrative
2. **Fast and responsive** — data loads should feel instant; no spinners blocking exploration
3. **Honest about uncertainty** — clearly label data limitations (era, coverage, category definitions)
4. **Progressively detailed** — start at the national/state level, drill into county, then tract

---

*Update this file whenever the user clarifies goals, adds features, or changes direction.*
