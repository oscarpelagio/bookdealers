"""Rutes principals de l'API."""

from fastapi import APIRouter
from app.router.endpoints import search_router, import_router, z3950_router

api_router = APIRouter()

api_router.include_router(search_router, prefix="/search", tags=["Search"])
api_router.include_router(import_router, prefix="/import", tags=["Import"])
api_router.include_router(z3950_router, prefix="/availability", tags=["z3950"])
