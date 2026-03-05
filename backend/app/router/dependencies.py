# ------- IMPORTS --------
from fastapi import Depends
from functools import lru_cache
from sqlmodel.ext.asyncio.session import AsyncSession
from collections.abc import AsyncGenerator

from app.adapters import GoogleBooksAdapter, Z3950Adapter
from app.clients import GoogleBooksClient, Z3950Client
from app.core.db import async_session
from app.crud import BookRepository, SearchRepository, AvailabilityRepository
from app.services import SearchService, Z3950Service


# ------- BASE DE DATOS --------
async def get_db() -> AsyncGenerator[AsyncSession]:
    async with async_session() as session:
        yield session


# ------- REPOSITORIOS --------
def get_book_repository(
    db: AsyncSession = Depends(get_db),
) -> BookRepository:
    return BookRepository(db)

def get_availability_repository(
    db: AsyncSession = Depends(get_db),
) -> AvailabilityRepository:
    return AvailabilityRepository(db)

def get_search_repository(
    db: AsyncSession = Depends(get_db),
) -> SearchRepository:
    return SearchRepository(db)


# ------- CLIENTES --------
@lru_cache()
def get_google_client() -> GoogleBooksClient:
    return GoogleBooksClient()

@lru_cache()
def get_z3950_client() -> Z3950Client:
    return Z3950Client()


# ------- ADAPTADORES --------
@lru_cache()
def get_google_adapter() -> GoogleBooksAdapter:
    return GoogleBooksAdapter()

@lru_cache()
def get_z3950_adapter() -> Z3950Adapter:
    return Z3950Adapter()


# ------- SERVICIOS --------
def get_book_service(
    book_repo: BookRepository = Depends(get_book_repository),
    search_repo: SearchRepository = Depends(get_search_repository),
    client: GoogleBooksClient = Depends(get_google_client),
    adapter: GoogleBooksAdapter = Depends(get_google_adapter),
) -> SearchService:
    return SearchService(book_repo, search_repo, client, adapter)

def get_z3950_service(
    book_repo: BookRepository = Depends(get_book_repository),
    availability_repo: AvailabilityRepository = Depends(get_availability_repository),
    client: Z3950Client = Depends(get_z3950_client),
    adapter: Z3950Adapter = Depends(get_z3950_adapter),
) -> Z3950Service:
    return Z3950Service(book_repo, availability_repo, client, adapter)


# ------- USER (TO-DO) --------
def get_user() -> int:
    return 1
