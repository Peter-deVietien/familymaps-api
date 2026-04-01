from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.database import create_tables
from app.routers import geodata, demographics, churchevents


@asynccontextmanager
async def lifespan(app: FastAPI):
    create_tables()
    yield


app = FastAPI(
    title="FamilyMaps API",
    description="Backend API serving demographic and geographic data for FamilyMaps",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:4200",
        "http://localhost:3000",
        "https://familymaps.onrender.com",
        "https://wdwwa.com",
        "https://www.wdwwa.com",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(geodata.router)
app.include_router(demographics.router)
app.include_router(churchevents.router)


@app.get("/health")
async def health_check():
    return {"status": "ok"}
