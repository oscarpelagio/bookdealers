"""Endpoints de l'API per a Z39.50."""

from fastapi import APIRouter, Depends
from app.services import Z3950Service
from app.router import get_z3950_service

router = APIRouter()

@router.get("/search")
async def search(
    book_id: int,
    service: Z3950Service = Depends(get_z3950_service)
) :
    return await service.search_book(book_id)
