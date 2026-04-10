# FamilyMaps — Constitution

FamilyMaps is a demographic visualization tool showing racial/ethnic composition across US geographies and over time.

| | |
|---|---|
| **Frontend** | `~/familymaps` — Angular 18 + Leaflet SPA |
| **Backend** | `~/familymaps-api` — FastAPI serving geo/demographic JSON + TopoJSON |
| **Hosting** | Render (both repos) |
| **Live** | `https://api.wdwwa.com` (API) |

## Core Principles

1. **Data accuracy over coverage** — better to show nothing than wrong data.
2. **Pre-aggregated sources preferred** over microdata when available.
3. **White Non-Hispanic** is the target demographic metric where available; "White (incl. Hispanic)" used for eras where WNH is impossible (pre-1978).
4. **Wiki is the project's persistent memory** — always update it; never repeat yourself. Record what worked, what didn't, what the user wants.
5. **Read selectively** — read `wiki/index.md` to route to the right wiki page; never read every wiki file.

## Product Vision

<!-- NEEDS INPUT: Fill these in to guide all future work -->

- [ ] What is the ultimate product goal? Personal tool? Public-facing site? Research resource?
- [ ] Who are the target users?
- [ ] What geographic granularity matters most long-term? (state / county / tract)
- [ ] What is the single most important insight the user should get from this tool?
- [ ] Are there planned features beyond the current set (births, demographics, ranking, church events)?

## Active Features

1. **Births Choropleth** — state-level % White births over time (1940–2024) → `vision/births-choropleth.md`
2. **WDWWA Ranking** — composite county score (female %, Trump %, age, pop, White NH %) → `vision/wdwwa-ranking.md`
3. **County Demographics** — county-level White NH % with range sliders → `vision/county-demographics.md`
4. **Florida Detail** — tract + block group layers for FL → `vision/florida-detail.md`
5. **Church Events** — xAI-powered church event directory → `vision/church-events.md`

→ **Full routing table:** `wiki/index.md`
