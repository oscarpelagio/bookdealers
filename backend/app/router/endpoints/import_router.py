"""API endpoints for Google Books."""
from fastapi import APIRouter, Depends, File, UploadFile

from app.schemas import BookResponse
from app.router import get_google_books_service, get_z3950_service
from app.services import GoogleBooksService, Z3950Service

router = APIRouter()

@router.post("/goodreads-csv")
async def import_goodreads_csv(
    csv_file: UploadFile = File(...),
    google_service: GoogleBooksService = Depends(get_google_books_service),
    z3950_service: Z3950Service = Depends(get_z3950_service)

) -> list[BookResponse] :
    books = await google_service.import_goodreads_csv(csv_file)
    for book in books:
        await z3950_service.get_availabity(book.id,"aladi")
    return books
