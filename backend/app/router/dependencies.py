# ------- IMPORTS --------
from fastapi import Depends
from functools import lru_cache
from sqlmodel.ext.asyncio.session import AsyncSession
from collections.abc import AsyncGenerator

from app.adapters import (
    GoogleBooksAdapter,
    OpenLibraryAdapter,
    Z3950Adapter,
    eBiblioAdapter,
    TodostuslibrosAdapter,
)
from app.clients import (
    GoogleBooksClient,
    OpenLibraryClient,
    Z3950Client,
    eBiblioClient,
    TodostuslibrosClient,
)
from app.core.db import async_session
from app.crud import BookRepository, SearchRepository, AvailabilityRepository, CatalogRepository
from app.services import (
    GoogleBooksService,
    OpenLibraryService,
    Z3950Service,
    EBiblioService,
    TodostuslibrosService,
)


# ------- DATABASE --------
async def get_db() -> AsyncGenerator[AsyncSession]:
    async with async_session() as session:
        yield session

# ------- REPOSITORIES --------
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

def get_catalog_repository(
    db: AsyncSession = Depends(get_db),
) -> CatalogRepository:
    return CatalogRepository(db)

# ------- CLIENTS --------
@lru_cache()
def get_google_client() -> GoogleBooksClient:
    return GoogleBooksClient()

@lru_cache()
def get_open_library_client() -> OpenLibraryClient:
    return OpenLibraryClient()

@lru_cache()
def get_z3950_client() -> Z3950Client:
    return Z3950Client()

@lru_cache()
def get_ebiblio_client() -> eBiblioClient:
    return eBiblioClient()

@lru_cache()
def get_todostuslibros_client() -> TodostuslibrosClient:
    return TodostuslibrosClient()


# ------- ADAPTERS --------
@lru_cache()
def get_google_adapter() -> GoogleBooksAdapter:
    return GoogleBooksAdapter()

@lru_cache()
def get_open_library_adapter() -> OpenLibraryAdapter:
    return OpenLibraryAdapter()

@lru_cache()
def get_z3950_adapter() -> Z3950Adapter:
    return Z3950Adapter()

@lru_cache()
def get_ebiblio_adapter() -> eBiblioAdapter:
    return eBiblioAdapter()

@lru_cache()
def get_todostuslibros_adapter() -> TodostuslibrosAdapter:
    return TodostuslibrosAdapter()


# ------- SERVICES --------
def get_google_books_service(
    book_repo: BookRepository = Depends(get_book_repository),
    search_repo: SearchRepository = Depends(get_search_repository),
    client: GoogleBooksClient = Depends(get_google_client),
    adapter: GoogleBooksAdapter = Depends(get_google_adapter)
) -> GoogleBooksService:
    return GoogleBooksService(book_repo, search_repo, client, adapter)

def get_open_library_service(
    book_repo: BookRepository = Depends(get_book_repository),
    search_repo: SearchRepository = Depends(get_search_repository),
    client: OpenLibraryClient = Depends(get_open_library_client),
    adapter: OpenLibraryAdapter = Depends(get_open_library_adapter),
) -> OpenLibraryService:
    return OpenLibraryService(book_repo, search_repo, client, adapter)

def get_z3950_service(
    book_repo: BookRepository = Depends(get_book_repository),
    availability_repo: AvailabilityRepository = Depends(get_availability_repository),
    catalog_repo: CatalogRepository = Depends(get_catalog_repository),
    client: Z3950Client = Depends(get_z3950_client),
    adapter: Z3950Adapter = Depends(get_z3950_adapter),
) -> Z3950Service:
    return Z3950Service(book_repo, availability_repo, catalog_repo, client, adapter)

def get_ebiblio_service(
    book_repo: BookRepository = Depends(get_book_repository),
    availability_repo: AvailabilityRepository = Depends(get_availability_repository),
    catalog_repo: CatalogRepository = Depends(get_catalog_repository),
    client: eBiblioClient = Depends(get_ebiblio_client),
    adapter: eBiblioAdapter = Depends(get_ebiblio_adapter),
) -> EBiblioService:
    return EBiblioService(book_repo, availability_repo, catalog_repo, client, adapter)

def get_todostuslibros_service(
    book_repo: BookRepository = Depends(get_book_repository),
    availability_repo: AvailabilityRepository = Depends(get_availability_repository),
    catalog_repo: CatalogRepository = Depends(get_catalog_repository),
    client: TodostuslibrosClient = Depends(get_todostuslibros_client),
    adapter: TodostuslibrosAdapter = Depends(get_todostuslibros_adapter),
) -> TodostuslibrosService:
    return TodostuslibrosService(book_repo, availability_repo, catalog_repo, client, adapter)
