from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.config import DATA_DIR, MEDIA_DIR, SOURCES_DIR
from app.db import init_db
from app.routers import assemblies, sources, tags


@asynccontextmanager
async def lifespan(app: FastAPI):
    SOURCES_DIR.mkdir(parents=True, exist_ok=True)
    MEDIA_DIR.mkdir(parents=True, exist_ok=True)
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    await init_db()
    yield


app = FastAPI(title="Kalinsky API", version="0.1.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(sources.router)
app.include_router(assemblies.router)
app.include_router(tags.router)

app.mount("/media", StaticFiles(directory=str(MEDIA_DIR)), name="media")
app.mount("/sources", StaticFiles(directory=str(SOURCES_DIR)), name="sources")
