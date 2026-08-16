"""Rutas de la API del photo-scraper."""

from fastapi import APIRouter

from .endpoints import router as image_router

router = APIRouter()

router.include_router(image_router, prefix="/photo-search", tags=["Search"])