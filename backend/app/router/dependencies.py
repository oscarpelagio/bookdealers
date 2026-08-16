# ------- IMPORTS --------
from fastapi import Depends
from functools import lru_cache
from sqlmodel.ext.asyncio.session import AsyncSession

from app.adapters import (
    Z3950SearchAdapter,
    GoogleBooksAdapter,
    OpenLibraryAdapter,
    Z3950Adapter,
    eBiblioAdapter,
    TodostuslibrosAdapter,
)
from app.auth.dependencies import (
    get_auth_repository,
    get_auth_service,
    get_current_user,
    get_google_verifier,
    require_roles,
)
from app.clients import (
    Z3950SearchClient,
    Z3950ImportClient,
    GoogleBooksClient,
    OpenLibraryClient,
    Z3950Client,
    eBiblioClient,
    TodostuslibrosClient,
    GooglePhotoClient,
    PenguinClient,
    AsteroideClient,
)
from app.core.deps import get_db
from app.crud import BookRepository, SearchRepository, AvailabilityRepository, CatalogRepository, AuthorPhotoRepository, AnagramaRepository, AuthorSourceRepository, PenguinIndexRepository, AsteroideIndexRepository, CentralArticleRepository
from app.services import (
    GoogleBooksService,
    OpenLibraryService,
    Z3950Service,
    Z3950SearchService,
    EBiblioService,
    TodostuslibrosService,
    AuthorPhotoService,
    AnagramaLookupService,
    PenguinLazyService,
    AsteroideLazyService,
    AuthorProfileLookupService,
)


# ------- DATABASE --------
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

def get_author_photo_repository(
    db: AsyncSession = Depends(get_db),
) -> AuthorPhotoRepository:
    return AuthorPhotoRepository(db)

def get_anagrama_repository(
    db: AsyncSession = Depends(get_db),
) -> AnagramaRepository:
    return AnagramaRepository(db)

def get_author_source_repository(
    db: AsyncSession = Depends(get_db),
) -> AuthorSourceRepository:
    return AuthorSourceRepository(db)

def get_penguin_index_repository(
    db: AsyncSession = Depends(get_db),
) -> PenguinIndexRepository:
    return PenguinIndexRepository(db)

def get_asteroide_index_repository(
    db: AsyncSession = Depends(get_db),
) -> AsteroideIndexRepository:
    return AsteroideIndexRepository(db)

def get_central_article_repository(
    db: AsyncSession = Depends(get_db),
) -> CentralArticleRepository:
    return CentralArticleRepository(db)

# ------- CLIENTS --------
@lru_cache()
def get_z3950_search_client() -> Z3950SearchClient:
    return Z3950SearchClient()

@lru_cache()
def get_z3950_import_client() -> Z3950ImportClient:
    return Z3950ImportClient()

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

@lru_cache()
def get_google_photo_client() -> GooglePhotoClient:
    return GooglePhotoClient()


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
def get_z3950_search_adapter() -> Z3950SearchAdapter:
    return Z3950SearchAdapter()

@lru_cache()
def get_ebiblio_adapter() -> eBiblioAdapter:
    return eBiblioAdapter()

@lru_cache()
def get_todostuslibros_adapter() -> TodostuslibrosAdapter:
    return TodostuslibrosAdapter()


# ------- SERVICES --------
def get_z3950_search_service(
    book_repo: BookRepository = Depends(get_book_repository),
    search_repo: SearchRepository = Depends(get_search_repository),
    catalog_repo: CatalogRepository = Depends(get_catalog_repository),
    client: Z3950SearchClient = Depends(get_z3950_search_client),
    adapter: Z3950SearchAdapter = Depends(get_z3950_search_adapter),
) -> Z3950SearchService:
    return Z3950SearchService(book_repo, search_repo, catalog_repo, client, adapter)

def get_z3950_import_service(
    book_repo: BookRepository = Depends(get_book_repository),
    search_repo: SearchRepository = Depends(get_search_repository),
    catalog_repo: CatalogRepository = Depends(get_catalog_repository),
    client: Z3950ImportClient = Depends(get_z3950_import_client),
    adapter: Z3950SearchAdapter = Depends(get_z3950_search_adapter),
) -> Z3950SearchService:
    return Z3950SearchService(book_repo, search_repo, catalog_repo, client, adapter)

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

def get_author_photo_service(
    repo: AuthorPhotoRepository = Depends(get_author_photo_repository),
    client: GooglePhotoClient = Depends(get_google_photo_client),
) -> AuthorPhotoService:
    return AuthorPhotoService(repo, client)

def get_anagrama_lookup_service(
    repo: AnagramaRepository = Depends(get_anagrama_repository),
) -> AnagramaLookupService:
    return AnagramaLookupService(repo)

async def get_penguin_client():
    client = PenguinClient()
    try:
        yield client
    finally:
        await client.aclose()

def get_penguin_lazy_service(
    repo: AuthorSourceRepository = Depends(get_author_source_repository),
    index_repo: PenguinIndexRepository = Depends(get_penguin_index_repository),
    client: PenguinClient = Depends(get_penguin_client),
) -> PenguinLazyService:
    return PenguinLazyService(repo, index_repo, client)

async def get_asteroide_client():
    client = AsteroideClient()
    try:
        yield client
    finally:
        await client.aclose()

def get_asteroide_lazy_service(
    repo: AuthorSourceRepository = Depends(get_author_source_repository),
    index_repo: AsteroideIndexRepository = Depends(get_asteroide_index_repository),
    client: AsteroideClient = Depends(get_asteroide_client),
) -> AsteroideLazyService:
    return AsteroideLazyService(repo, index_repo, client)

def get_author_profile_lookup_service(
    repo: AuthorSourceRepository = Depends(get_author_source_repository),
    lazy: PenguinLazyService = Depends(get_penguin_lazy_service),
    asteroide_lazy: AsteroideLazyService = Depends(get_asteroide_lazy_service),
) -> AuthorProfileLookupService:
    return AuthorProfileLookupService(repo, lazy, asteroide_lazy)
