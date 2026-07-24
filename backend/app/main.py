"""Main application"""

from contextlib import asynccontextmanager
from fastapi import FastAPI

from app.core.db import init_db
from app.core.catalog_seed import seed_catalogs
from app.router import api_router

@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    await seed_catalogs()
    yield

app = FastAPI(title="Book Tracker API", lifespan=lifespan, swagger_ui_parameters={"displayRequestDuration": True})
app.include_router(api_router)


@app.get("/", tags=["Backend"])
def status():
    return {"status": "ok", "message": "Running"}
