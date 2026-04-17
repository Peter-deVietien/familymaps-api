# Backend Wiki Index

> Compact routing table (FastAPI / data pipeline). Read this to decide which wiki files are relevant to the current task.

## Vision (what we want)

| Topic | File | When to Read |
|-------|------|--------------|
| Product vision & open questions | `vision/product.md` | Starting a new feature; goals unclear |
| Births choropleth layer | `vision/births-choropleth.md` | Working on births feature |
| WDWWA ranking system | `vision/wdwwa-ranking.md` | Working on ranking/scoring |
| County demographics layers | `vision/backend-vision-county-demographics.md` | Working on county/tract/block group layers |
| Church events directory | `vision/backend-vision-church-events.md` | Working on church events |
| Florida detail layers | `vision/backend-vision-florida-detail.md` | Working on FL-specific layers |
| Feature vision template | `vision/_template.md` | Creating a new feature |

## Data Sources (deep reference)

| Topic | File | When to Read |
|-------|------|--------------|
| Data source overview & coverage matrix | `data/overview.md` | Any data download/extraction task |
| CDC WONDER (1995–2024) | `data/cdc_wonder.md` | Working with CDC WONDER |
| KFF (2016–2023, validation) | `data/kff.md` | Working with KFF data |
| NHGIS/IPUMS (1915–2007) | `data/nhgis.md` | Working with NHGIS data |
| NBER Historical (1940–1968) | `data/nber_historical.md` | Working with pre-1968 data |
| NBER Microdata (1973–1994) | `data/nber_microdata.md` | Working with 1973–1994 gap data |
| NCHS public-use (deprioritized) | `data/nchs.md` | Only if other sources fail |
| Extraction pipeline & output schema | `data/pipeline.md` | Running/modifying extract_all_data.py |

## Architecture (how it's built)

| Topic | File | When to Read |
|-------|------|--------------|
| Backend (FastAPI) | `architecture/backend.md` | Modifying API endpoints or structure |
| Frontend (Angular + Leaflet) | `architecture/frontend.md` | Modifying UI components |
| API contract | `architecture/backend-api-contract.md` | Changing endpoint shapes |
| Deployment | `architecture/backend-deployment.md` | Deploy/hosting issues |

## Learnings (hard-won knowledge)

| Topic | File | When to Read |
|-------|------|--------------|
| Scraping patterns | `learnings/scraping.md` | Building or debugging a scraper |
| Race categories by era | `learnings/race-categories.md` | Understanding what race data exists when |
| Data quirks & gotchas | `learnings/data-quirks.md` | Encountering unexpected data issues |

## Status (where we are)

| Topic | File | When to Read |
|-------|------|--------------|
| Current status & next steps | `status/backend-current.md` | Starting a session; understanding state |
| Action/download log | `status/backend-action-log.md` | Checking what's been done and when |

## Scratchpad

`scratchpad/` — ephemeral agent notes. Distill useful findings into proper wiki files, discard the rest.
