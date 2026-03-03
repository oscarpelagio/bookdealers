"""Rutes principals de l'API."""

from fastapi import APIRouter
from .endpoints import router

api_router = APIRouter()

api_router.include_router(router, prefix="/Z3950-search", tags=["Search"])
