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

## Frontend Deployment

- Angular build output in `dist/`
- Static files in `public/` (births-data.json, states-10m.json) included in build

## Open Questions

<!-- NEEDS INPUT -->
- [ ] What is the frontend production URL?
- [ ] Is there CI/CD configured?
- [ ] Are there staging/preview environments?
- [ ] How are data updates deployed? (re-run pipeline → rebuild → deploy?)

---

*Update when deployment process changes.*
