# Deployment

> Hosting and deployment details. Read when deploying or debugging production issues.

## Hosting

Both repos are hosted on **Render**.

| Service | Repo | URL |
|---------|------|-----|
| Backend API | `~/familymaps-api` | `https://api.wdwwa.com` |
| Frontend SPA | `~/familymaps` | *(domain TBD — check Render dashboard)* |

## Backend Deployment

- FastAPI served by Uvicorn
- `requirements.txt` defines Python dependencies
- Static data files in `app/data/` are included in the deploy
- All display data is pre-baked as static JSON/TopoJSON (~19MB total)
- Raw data pipeline (`data/`) is gitignored — only the distilled output ships
- Auto-deploy on push to `main`
- Start command: `uvicorn app.main:app --host 0.0.0.0 --port $PORT`

## Frontend Deployment

- Angular build output in `dist/`
- Static files in `public/` (births-data.json, states-10m.json) included in build

## Open Questions

- [ ] What is the frontend production URL? (currently `https://familymaps.onrender.com`)
- [x] Is there CI/CD configured? — Yes, Render auto-deploys on push to `main`
- [ ] Are there staging/preview environments?
- [x] How are data updates deployed? — Re-run local pipeline → regenerate `app/data/births.json` → commit & push

---

*Update when deployment process changes.*
