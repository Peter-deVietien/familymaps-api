from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.database import create_tables
from app.routers import geodata, demographics, churchevents, births


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
    # Also allow private LAN dev origins (any port) so devs can test on
    # phones via `ng serve --host 0.0.0.0`. Matches RFC 1918 ranges only.
    allow_origin_regex=(
        r"^http://("
        r"localhost"
        r"|127\.\d+\.\d+\.\d+"
        r"|10\.\d+\.\d+\.\d+"
        r"|192\.168\.\d+\.\d+"
        r"|172\.(1[6-9]|2\d|3[0-1])\.\d+\.\d+"
        r")(:\d+)?$"
    ),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(geodata.router)
app.include_router(demographics.router)
app.include_router(churchevents.router)
app.include_router(births.router)


@app.get("/health")
async def health_check():
    return {"status": "ok"}
