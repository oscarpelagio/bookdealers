# Backend — BookTracker API

Async REST API with FastAPI + SQLModel for book management, Google Books search, and library availability checks.

## Architecture

```
app/
├── main.py                    # FastAPI app + lifespan (init_db)
├── core/
│   ├── config.py              # Settings (pydantic-settings, .env)
│   └── db.py                  # AsyncEngine + AsyncSession factory
├── models/                    # SQLModel table models
│   ├── book.py                # Book (inherits from BookBase schema)
│   ├── search_cache.py        # Search + SearchRelation (query cache)
│   ├── catalogs.py            # Catalog (availability sources)
│   ├── establishments.py      # Establishment (libraries/stores)
│   ├── book_establishment.py  # BookEstablishment (availability)
│   ├── availability_status_enum.py # AvailabilityStatusEnum
│   ├── establishment_type_enum.py  # EstablishmentTypeEnum
│   └── enums.py               # Other enums
├── schemas/
│   └── book.py                # BookBase, BookCreate, BookUpdate, BookResponse
├── crud/                      # Repository pattern (async)
│   ├── book_repository.py     # Book CRUD + merge/dedup
│   ├── search_repository.py   # Search cache (query → books)
│   ├── availability_repository.py  # Library availability (24h cache)
│   ├── availability_repo_db.py # Alternative availability repository
│   └── catalog_repository.py  # Catalog management
├── services/                  # Business logic
│   ├── search_base_service.py       # Base class for search
│   ├── google_books_service.py      # Google Books search
│   ├── open_library_service.py      # OpenLibrary search
│   ├── availability_base_service.py # Base class for availability (semaphore 1 req/sec)
│   ├── z3950_service.py             # ALADI Z39.50 availability
│   ├── ebiblio_service.py           # eBiblio (Catalan libraries) availability
│   └── todostuslibros_service.py    # Todostuslibros (booksellers) availability
├── clients/                   # HTTP clients for external APIs
│   ├── search_base_client.py  # Base class for search
│   ├── google_client.py       # Google Books API (httpx async, persistent)
│   ├── open_library_client.py # OpenLibrary API
│   ├── availability_base_client.py  # Base class for availability
│   ├── z3950_client.py        # HTTP proxy to the z3950 container
│   ├── ebiblio_client.py      # eBiblio API
│   └── todostuslibros_client.py    # Todostuslibros API
├── adapters/                  # External data transforms → models
│   ├── search_base_adapter.py # Base class for search
│   ├── google_adapter.py      # JSON Google Books → BookBase
│   ├── open_library_adapter.py# OpenLibrary JSON → BookBase
│   ├── availability_base_adapter.py # Base class for availability
│   ├── z3950_adapter.py       # MARC text → Availability list
│   ├── ebiblio_adapter.py     # eBiblio HTML → Availability list
│   └── todostuslibros_adapter.py   # Todostuslibros JSON → Availability list
├── router/
│   ├── router.py              # Main router (prefixes)
│   ├── dependencies.py        # Dependency injection (repos, services, clients)
│   └── endpoints/
│       ├── search_router.py      # GET /search/by-title
│       ├── import_router.py      # POST /import/goodreads-csv
│       └── availability_router.py # GET /availability/{z3950,ebiblio,todostuslibros}
└── utils/
    ├── normalization_utils.py  # Text normalization (accents, case, etc.)
    └── csv_utils.py            # Goodreads CSV parser
```

## Layers and data flow

```
                    ┌─────────────────────────────────┐
                    │          Router Layer           │
                    │  endpoints/ (thin, no logic)    │
                    └──────────────┬──────────────────┘
                                   │ Depends()
                    ┌──────────────▼──────────────────┐
                    │         Service Layer           │
                    │  Search, Availability services  │
                    │  (orchestration, rate limiting) │
                    └───┬──────────┬──────────┬───────┘
                        │          │          │
              ┌─────────▼──┐ ┌─────▼───┐ ┌────▼─────────┐
              │ Repository │ │ Client  │ │   Adapter    │
              │  (DB ops)  │ │ (HTTP)  │ │ (transform)  │
              └─────┬──────┘ └────┬────┘ └──────────────┘
                    │             │
           ┌────────▼────────┐    │
           │   PostgreSQL    │    │
           │   (async)       │    │
           └─────────────────┘    │
                                  │
                    ┌─────────────▼──────────────────┐
                    │    External APIs / Services    │
                    │  Google | OpenLibrary | Z39.50 │
                    │  eBiblio | Todostuslibros      │
                    └────────────────────────────────┘
```

## Dependency Injection

All injection is centralized in `router/dependencies.py`:

```
get_db()                        → AsyncSession (yield, auto-close)
  └── get_book_repository()     → BookRepository(db)
  └── get_search_repository()   → SearchRepository(db)
  └── get_availability_repository() → AvailabilityRepository(db)
  └── get_catalog_repository()  → CatalogRepository(db)

# Search services + clients
get_google_client()    → GoogleBooksClient (@lru_cache, singleton)
get_google_adapter()   → GoogleBooksAdapter (@lru_cache, singleton)
get_google_books_service() → GoogleBooksService(...)

get_open_library_client()    → OpenLibraryClient (@lru_cache, singleton)
get_open_library_adapter()   → OpenLibraryAdapter (@lru_cache, singleton)
get_open_library_service()   → OpenLibraryService(...)

# Availability services + clients (shared semaphore: 1 req/sec)
get_z3950_client()    → Z3950Client
get_z3950_adapter()   → Z3950Adapter
get_z3950_service()   → Z3950Service(book_repo, availability_repo, catalog_repo, client, adapter)

get_ebiblio_client()  → EBiblioClient
get_ebiblio_adapter() → EBiblioAdapter
get_ebiblio_service() → EBiblioService(book_repo, availability_repo, catalog_repo, client, adapter)

get_todostuslibros_client()   → TodostuslibrosClient
get_todostuslibros_adapter()  → TodostuslibrosAdapter
get_todostuslibros_service()  → TodostuslibrosService(book_repo, availability_repo, catalog_repo, client, adapter)
```

## Endpoints

### `GET /search/by-title`
Search books by title and/or author. Cache in DB before calling Google.

| Param | Type | Required | Description |
|-------|------|----------|-------------|
| `title` | string | No | Book title |
| `author` | string | No | Book author |

**Response:** `list[BookResponse]` (max 10)

**Internal flow:**
1. `GoogleBooksAdapter.build_search(title, author)` → query string
2. `SearchRepository.check_cache(query)` → DB lookup
3. If cache hit → return
4. If miss → `_rate_limited_search()` → Google Books API (semaphore 1 req/sec)
5. `GoogleBooksAdapter.parse_books()` → list of `BookBase`
6. `BookRepository.insert_books()` → dedupe by `normal_title + normal_author`
7. `SearchRepository.save_cache()` → persist query → books
8. Return

---

### `POST /import/goodreads-csv`
Import a CSV exported from Goodreads. Each book is searched in Google Books.

| Param | Type | Description |
|-------|------|-------------|
| `csv_file` | File | Goodreads export CSV |

**Response:** `list[BookResponse]`

**Internal flow:**
1. `CsvUtils.parse_goodreads_book()` → extract title + author per row
2. For each book: `search_and_process(title, author, max_results=1)`
3. Rate limiter: max 1 call/sec to Google (semaphore + sleep)
4. Individual errors are logged and the loop continues

---

### `GET /availability/z3950`
Check availability of a book in ALADI libraries (Z39.50 catalog).

| Param | Type | Description |
|-------|------|-------------|
| `book_id` | int | Book ID in the DB |
| `catalog` | string | Catalog name (e.g., "aladi") |

**Response:** `list[dict]` with `{establishment_name, book_status, queue, link}`

**Internal flow:**
1. `AvailabilityRepository.get_availability(book, catalog)` → DB cache check (< 24h)
2. If cache hit (< 24h) → return instantly
3. If cache miss:
   - `BookRepository.get_by_id()` → get book data
   - `CatalogRepository.get_catalog()` → get catalog data
   - Acquire semaphore (1 concurrent request across all availability services)
   - `Z3950Client.fetch_books()` → HTTP to z3950 container
   - `Z3950Adapter.response_adapter()` → parse MARC records → availability objects
   - `AvailabilityRepository.save_availability()` → persist with `updated_at` (cache expiry)
4. Return

---

### `GET /availability/ebiblio`
Check availability of a book in Catalan libraries (eBiblio).

| Param | Type | Description |
|-------|------|-------------|
| `book_id` | int | Book ID in the DB |
| `catalog` | string | Catalog name (e.g., "ebiblio") |

**Response:** `list[dict]` with `{establishment_name, book_status, link}`

**Internal flow:** Same as Z39.50, but:
- Calls `EBiblioClient` (parse HTML/JSON)
- Uses `EBiblioAdapter` to extract availability

---

### `GET /availability/todostuslibros`
Check availability of a book at Spanish booksellers (Todostuslibros).

| Param | Type | Description |
|-------|------|-------------|
| `book_id` | int | Book ID in the DB |

**Response:** `list[dict]` with `{establishment_name, establishment_city, book_status, quantity, link}`

**Internal flow:** Same as Z39.50, but:
- Calls `TodostuslibrosClient` (parse HTML/JSON)
- Uses `TodostuslibrosAdapter` to extract store information

## Rate Limiting

### Google Books & OpenLibrary (Search)

```python
class SearchBaseService:
    _semaphore: asyncio.Semaphore = asyncio.Semaphore(1)
```

- **1 concurrent call** to external search APIs
- Only on cache miss (cached searches are instant)
- ~60 req/min, well below API limits

### Availability Services (Z39.50, eBiblio, Todostuslibros)

```python
class AvailabilityBaseService:
    _semaphore = asyncio.Semaphore(1)  # Shared across all 3 services
```

- **1 concurrent call** shared across Z39.50, eBiblio, and Todostuslibros
- Only on cache miss (< 24h cached results bypass semaphore)
- Respects external API rate limits
- If cached < 24h → returns instantly (no semaphore)

## Normalization and deduplication

`NormalizationUtils.normalize_text()`:
1. NFD → remove accents → NFC
2. Lowercase
3. Remove non-alphanumeric characters
4. Collapse spaces

Example: `"The House of the Spirits"` → `"the house of the spirits"`

Books are deduplicated by `(normal_title, normal_author)`. If a book already exists in DB, a _merge_ is done (fills `None` fields with new data, does not overwrite existing).

## Database

- **Engine**: `asyncpg` (PostgreSQL async driver)
- **Session**: `sqlmodel.ext.asyncio.session.AsyncSession` (SQLModel wrapper with `.exec()`)
- **Migrations**: Alembic (in `alembic/versions/`)
- **Init**: `init_db()` in lifespan creates tables if missing via `SQLModel.metadata.create_all`

```bash
# Create migration
make new-migration m="add_new_field"

# Run migrations
make migrate

# Check status
make current-migration
```

## Configuration

Environment variables (`.env`):

| Variable | Description | Default |
|----------|-------------|---------|
| `POSTGRES_USER` | PostgreSQL user | — |
| `POSTGRES_PASSWORD` | PostgreSQL password | — |
| `POSTGRES_HOST` | PostgreSQL host | `db` |
| `POSTGRES_PORT` | PostgreSQL port | `5432` |
| `POSTGRES_DB` | Database name | — |
| `GOOGLE_API_KEY` | Google Books API key | `None` |
| `API_PORT` | Backend port | `8000` |

## Authentication

Módulo autocontenido en `app/auth/` con arquitectura por capas
(modelo/repositorio/servicio/router/dependencias/excepciones). No depende de
servicios externos de autenticación (AWS Cognito, Keycloak, etc.).

### Flujos y endpoints (`/auth`)

| Método | Ruta | Descripción |
|--------|------|-------------|
| POST | `/auth/register` | Registro por email/username/contraseña. No revela si el email existe. |
| POST | `/auth/login` | Login por email (+rate limit y bloqueo por fuerza bruta). |
| POST | `/auth/refresh` | Rota el refresh token (detección de replay/revolucion del token robado). |
| POST | `/auth/logout` | Revoca un refresh token (o todas las sesiones con `logout_everywhere`). |
| POST | `/auth/google` | Login/registro con ID token de Google (validado por JWKS). |
| GET  | `/auth/me` | Usuario actual (protector). |
| POST | `/auth/verify-email` | Verifica correo con token de un solo uso. |
| POST | `/auth/reset-password/request` + `/confirm` | Recuperación de contraseña. |
| POST | `/auth/change-password` | Cambio de contraseña (revoca sesiones). |

### Seguridad

- **Contraseñas**: Argon2id via `pwdlib` (reemplazo mantenido de passlib). Nunca en claro.
- **Access JWT**: 15 min, firmado `HS256` con `iss`/`aud`/`jti` y claims de roles.
- **Refresh token**: opaco (48 bytes), **30 días**, guardado hasheado con `HMAC-SHA256` + pepper. Rotación encadenada en BD. Si un token ya usado se reutiliza, se revoca **toda la familia** (replay protection).
- **No enumeración**: errores genéricos de login/registro; los timings se igualan con un hash dummy.
- **Fuerza bruta**: lockout por cuenta (intentos en BD) + rate limiter en memoria por IP+email (configurables).
- **Google**: se valida la firma del ID token contra la JWKS pública (iss/aud/exp). Los tokens de Google nunca autorizan peticiones internas; se emiten JWT propios.
- **Roles**: RBAC normalizado (`roles` + `user_roles`). `require_roles(RoleKey.ADMIN)` como dependency.
- **Email**: tablas, tokens y servicios listos para verificación/reset. El envío es un *stub* (`_send_email`). Con `EMAIL_SEND_ENABLED=false` se devuelven los tokens en la respuesta (modo dev).

### Tablas (migración `a1b2c3d4e5f6`)

`roles`, `user_roles`, `users` (UUID, soft delete, bloqueo), `refresh_tokens` (hash, familia, rotación), `email_verification_tokens`, `password_reset_tokens`. Todas las fechas timezone-aware.

### Tests

Ejecuta contra un PostgreSQL (docker) usando una base dedicada `TEST_DATABASE_NAME`:

```bash
make test   # docker compose exec back pytest -q
```

Cubre registro, login, refresh (rotación + replay), logout, google login y permisos RBAC.

## Dependencies

| Package | Use |
|---------|-----|
| `fastapi` | Async web framework |
| `uvicorn` | ASGI server |
| `sqlmodel` | ORM (SQLAlchemy + Pydantic) |
| `asyncpg` | PostgreSQL async driver |
| `psycopg2-binary` | PostgreSQL sync driver (Alembic) |
| `httpx` | Async HTTP client |
| `pydantic-settings` | Settings from .env |
| `alembic` | DB migrations |
| `python-multipart` | File upload (CSV) |
| `pwdlib[argon2]` | Argon2id password hashing |
| `PyJWT` + `cryptography` | JWT access tokens + RS256 (Google) |
| `email-validator` | Validación `EmailStr` |
