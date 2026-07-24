"""API endpoints for Z39.50."""

from fastapi import APIRouter, Depends
from app.services import Z3950Service, EBiblioService, TodostuslibrosService
from app.router import get_z3950_service, get_ebiblio_service, get_todostuslibros_service

router = APIRouter()

@router.get("/z3950")
async def search(
    book_id: int,
    catalog: str,
    service: Z3950Service = Depends(get_z3950_service)
): 
    return await service.get_availabity(book_id, catalog)


@router.get("/ebiblio")
async def search(
    book_id: int,
    catalog: str,
    service: EBiblioService = Depends(get_ebiblio_service)
):
    return await service.get_availabity(book_id, catalog)


@router.get("/todostuslibros")
async def search(
    book_id: int,
    service: TodostuslibrosService = Depends(get_todostuslibros_service)
):
    return await service.get_availabity(book_id, "todostuslibros")
