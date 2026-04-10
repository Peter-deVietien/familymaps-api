# Frontend Architecture

> Angular 18 + Leaflet SPA at `~/familymaps`. Read when modifying UI components or map layers.

## Stack

- **Framework:** Angular 18 (standalone components, no NgModules)
- **Map library:** Leaflet
- **Hosting:** Render
- **Entry point:** `src/main.ts` → `AppComponent` → `<router-outlet>`

## Routes

| Route | Component | Description |
|-------|-----------|-------------|
| `/single-ratio` (default) | `SingleRatioComponent` | Main map with all demographic layers |
| `/churchevents` | `ChurchEventsComponent` | Church events directory |

## Key Files

| File | Role |
|------|------|
| `src/app/single-ratio/single-ratio.component.ts` | Main map (~1290 lines), all 6 layers |
| `src/app/single-ratio/single-ratio.component.html` | Layer selection UI, range/year controls |
| `src/app/single-ratio/single-ratio.component.scss` | Responsive styles, legend, tooltips |
| `src/environments/environment.ts` | API URL (`https://api.wdwwa.com`) |

## Architecture Notes

- No Angular services — data loading uses raw `fetch()` in components
- All layers built in a single `Promise.all` in `loadLayers()`
- Standalone components throughout
- Leaflet manages map rendering with custom legends, tooltips, and state labels

## Map Layers (on single-ratio page)

1. **Rank** — WDWWA composite county score
2. **County** — White NH % by county
3. **County Under 5** — White NH % for under-5 population
4. **Tracts (FL)** — Florida census tract White NH %
5. **Block Groups (FL)** — Florida block group White NH %
6. **Births** — Historical both-parent WNH baby % by state with year navigation

---

*Update when components change or new layers are added. See also `~/familymaps/wiki/` for the frontend's own wiki.*
