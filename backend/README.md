# Backend — BookTracker API

API REST async con FastAPI + SQLModel para gestión de libros, búsqueda en Google Books y consulta de disponibilidad en bibliotecas.

## Arquitectura

```
app/
├── main.py                    # FastAPI app + lifespan (init_db)
├── core/
│   ├── config.py              # Settings (pydantic-settings, .env)
│   └── db.py                  # AsyncEngine + AsyncSession factory
├── models/                    # SQLModel table models
│   ├── book.py                # Book (hereda de BookBase schema)
│   ├── search_cache.py        # Search + SearchRelation (cache de queries)
│   ├── establishments.py      # Establishment (bibliotecas)
│   ├── book_establishment.py  # BookEstablishment (disponibilidad)
│   ├── users.py               # User
│   ├── user_book.py           # UserBook (estantería personal)
│   └── enums.py               # ShelfStatus enum
├── schemas/
│   └── book.py                # BookBase, BookCreate, BookUpdate, BookResponse
├── crud/                      # Repository pattern (async)
│   ├── book_repository.py     # CRUD libros + merge/dedup
│   ├── search_repository.py   # Cache de búsquedas (query → books)
│   ├── availability_repository.py  # Disponibilidad en bibliotecas
│   └── establishment_repository.py # Insert bulk establecimientos
├── services/                  # Lógica de negocio
│   ├── search_service.py      # Búsqueda + import CSV + rate limiter
│   └── z3950_service.py       # Disponibilidad via Z39.50
├── clients/                   # Clientes HTTP a APIs externas
│   ├── google_client.py       # Google Books API (httpx async, persistent)
│   └── z3950_client.py        # Proxy HTTP al contenedor z3950
├── adapters/                  # Transformación de datos externos → modelos
│   ├── google_adapter.py      # JSON Google Books → BookBase
│   └── z3950_adapter.py       # MARC text → list[dict] localizaciones
├── router/
│   ├── router.py              # Router principal (prefixes)
│   ├── dependencies.py        # Dependency injection (repos, services, clients)
│   └── endpoints/
│       ├── search_router.py     # GET /search/by-title
│       ├── import_router.py     # POST /import/goodreads-csv
│       └── z3950_router.py      # GET /availability/search
└── utils/
    ├── normalization_utils.py  # Normalización texto (acentos, case, etc.)
    └── csv_utils.py            # Parser de CSV Goodreads
```

## Capas y flujo de datos

```
                    ┌─────────────────────────────────┐
                    │          Router Layer           │
                    │  endpoints/ (thin, no logic)    │
                    └──────────────┬──────────────────┘
                                   │ Depends()
                    ┌──────────────▼──────────────────┐
                    │         Service Layer           │
                    │  SearchService, Z3950Service    │
                    │  (orchestration, rate limiting) │
                    └───┬──────────┬──────────┬───────┘
                        │          │          │
              ┌─────────▼──┐ ┌─────▼───┐ ┌────▼─────────┐
              │ Repository │ │ Client  │ │   Adapter    │
              │  (DB ops)  │ │ (HTTP)  │ │ (transform)  │
              └─────┬──────┘ └────┬────┘ └──────────────┘
                    │             │
              ┌─────▼───┐   ┌─────▼───────┐
              │ Postgres│   │ Google API  │
              │  (async)│   │ Z3950 proxy │
              └─────────┘   └─────────────┘
```

## Dependency Injection

Toda la inyección se centraliza en `router/dependencies.py`:

```
get_db()                    → AsyncSession (yield, auto-close)
  └── get_book_repository() → BookRepository(db)
  └── get_search_repository() → SearchRepository(db)
  └── get_availability_repository() → AvailabilityRepository(db)

get_google_client()  → GoogleBooksClient  (@lru_cache, singleton)
get_google_adapter() → GoogleBooksAdapter (@lru_cache, singleton)
get_z3950_client()   → Z3950Client
get_z3950_adapter()  → Z3950Adapter

get_book_service()   → SearchService(book_repo, search_repo, client, adapter)
get_z3950_service()  → Z3950Service(book_repo, availability_repo, client, adapter)
```

## Endpoints

### `GET /search/by-title`
Busca libros por título y/o autor. Cache en DB antes de llamar a Google.

| Param | Tipo | Requerido | Descripción |
|-------|------|-----------|-------------|
| `title` | string | No | Título del libro |
| `author` | string | No | Autor del libro |

**Response:** `list[BookResponse]` (max 10)

**Flujo interno:**
1. `GoogleBooksAdapter.build_search(title, author)` → query string
2. `SearchRepository.check_cache(query)` → DB lookup
3. Si cache hit → return
4. Si miss → `_rate_limited_search()` → Google Books API (semáforo 1 req/sec)
5. `GoogleBooksAdapter.parse_books()` → lista de `BookBase`
6. `BookRepository.insert_books()` → deduplica por `normal_title + normal_author`
7. `SearchRepository.save_cache()` → persiste query → books
8. Return

---

### `POST /import/goodreads-csv`
Importa un CSV exportado de Goodreads. Cada libro se busca en Google Books.

| Param | Tipo | Descripción |
|-------|------|-------------|
| `csv_file` | File | CSV de export de Goodreads |

**Response:** `list[BookResponse]`

**Flujo interno:**
1. `CsvUtils.parse_goodreads_book()` → extrae title + author de cada fila
2. Para cada libro: `search_and_process(title, author, max_results=1)`
3. Rate limiter: máximo 1 llamada/segundo a Google (semáforo + sleep)
4. Errores individuales se loguean y se continúa con el siguiente

---

### `GET /availability/search`
Consulta disponibilidad de un libro en bibliotecas catalanas (red ALADI).

| Param | Tipo | Descripción |
|-------|------|-------------|
| `book_id` | int | ID del libro en la DB |

**Response:** `list[dict]` con `{biblioteca, language, estado}`

**Flujo interno:**
1. `AvailabilityRepository.get_availability(book_id)` → DB cache check
2. Si cache hit → return
3. Si miss → `BookRepository.get_by_id()` → obtener `normal_title`, `normal_author`
4. `Z3950Client.search_z3950()` → HTTP al contenedor z3950
5. `Z3950Adapter.extraer_localizaciones()` → parseo de MARC records
6. `AvailabilityRepository.save_availability()` → persiste establishments + relaciones
7. Return

## Rate Limiting (Google Books)

```python
class SearchService:
    _google_semaphore = asyncio.Semaphore(1)   # 1 llamada concurrente
    _last_google_call: float = 0.0
    _min_interval: float = 1.0                  # 1 segundo entre llamadas
```

- **Semáforo de clase**: funciona entre múltiples requests concurrentes
- Solo aplica cuando hay cache miss (búsquedas cacheadas son instantáneas)
- ~60 req/min, bien debajo del límite de Google (100/min)

## Normalización y deduplicación

`NormalizationUtils.normalize_text()`:
1. NFD → elimina acentos → NFC
2. Lowercase
3. Elimina caracteres no alfanuméricos
4. Colapsa espacios

Ejemplo: `"La Casa de los Espíritus"` → `"la casa de los espiritus"`

Los libros se deduplican por `(normal_title, normal_author)`. Si un libro ya existe en DB, se hace _merge_ (rellena campos `None` con datos nuevos, no sobreescribe existentes).

## Base de datos

- **Engine**: `asyncpg` (PostgreSQL async driver)
- **Session**: `sqlmodel.ext.asyncio.session.AsyncSession` (SQLModel wrapper con `.exec()`)
- **Migraciones**: Alembic (en `alembic/versions/`)
- **Init**: `init_db()` en lifespan crea tablas si no existen via `SQLModel.metadata.create_all`

```bash
# Crear migración
make new-migration m="add_new_field"

# Ejecutar migraciones
make migrate

# Ver estado
make current-migration
```

## Configuración

Variables de entorno (`.env`):

| Variable | Descripción | Default |
|----------|-------------|---------|
| `POSTGRES_USER` | Usuario PostgreSQL | — |
| `POSTGRES_PASSWORD` | Password PostgreSQL | — |
| `POSTGRES_HOST` | Host PostgreSQL | `db` |
| `POSTGRES_PORT` | Puerto PostgreSQL | `5432` |
| `POSTGRES_DB` | Nombre de la BD | — |
| `GOOGLE_API_KEY` | API key de Google Books | `None` |
| `API_PORT` | Puerto del backend | `8000` |

## Dependencias

| Paquete | Uso |
|---------|-----|
| `fastapi` | Framework web async |
| `uvicorn` | ASGI server |
| `sqlmodel` | ORM (SQLAlchemy + Pydantic) |
| `asyncpg` | Driver PostgreSQL async |
| `psycopg2-binary` | Driver PostgreSQL sync (Alembic) |
| `httpx` | HTTP client async |
| `pydantic-settings` | Configuración desde .env |
| `alembic` | Migraciones de DB |
| `python-multipart` | File upload (CSV) |
