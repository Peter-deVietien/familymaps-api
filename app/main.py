from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.routers import geodata, demographics

app = FastAPI(
    title="FamilyMaps API",
    description="Backend API serving demographic and geographic data for FamilyMaps",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:4200",
        "http://localhost:3000",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(geodata.router)
app.include_router(demographics.router)


@app.get("/health")
async def health_check():
    return {"status": "ok"}
