"""Endpoints de l'API per a Google Books."""
from fastapi import APIRouter, Depends, File, UploadFile

from app.schemas import BookResponse
from app.router import get_book_service
from app.services import SearchService

router = APIRouter()

@router.post("/goodreads-csv")
async def import_goodreads_csv(
    csv_file: UploadFile = File(...),
    service: SearchService = Depends(get_book_service)
) -> list[BookResponse] :
    books = await service.import_goodreads_csv(csv_file)
    return books
