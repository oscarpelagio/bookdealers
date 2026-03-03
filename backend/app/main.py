"""Aplicació principal."""

from contextlib import asynccontextmanager
from fastapi import FastAPI

from app.core.db import init_db
from app.router import api_router

@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    yield

app = FastAPI(title="Book Tracker API", lifespan=lifespan)
app.include_router(api_router)


@app.get("/", tags=["Backend"])
def status():
    return {"status": "ok", "message": "Running"}
