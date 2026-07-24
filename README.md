# BookTracker

Personal book tracking system and availability checks in Catalan libraries (ALADI network) via the Z39.50 protocol.

## Architecture

```
┌──────────────────────────────────────────────────────────────────┐
│                        Docker Compose                            │
│                                                                  │
│  ┌──────────┐     ┌──────────────┐     ┌───────────────────┐    │
│  │ postgres │◄────│   backend    │────►│      z3950        │    │
│  │   :5432  │     │    :8000     │     │      :8001        │    │
│  │          │     │   FastAPI    │     │  FastAPI + yaz    │    │
│  └──────────┘     └──────┬───────┘     └────────┬──────────┘    │
│                          │                      │               │
└──────────────────────────┼──────────────────────┼───────────────┘
                           │                      │
                    ┌──────▼───────┐      ┌───────▼────────┐
                    │ Google Books │      │  ALADI Z39.50  │
                    │     API      │      │   Catalog      │
                    └──────────────┘      └────────────────┘
                           │                      │
                           │              ┌───────▼────────┐
                           │              │ eBiblio        │
                           │              │ (Catalan libs) │
                           │              └────────────────┘
                           │                      │
                           │              ┌───────▼──────────┐
                           │              │ Todostuslibros   │
                           │              │ (Booksellers)    │
                           └──────────────└──────────────────┘
```

## Services

| Service | Port | Description |
|---------|------|-------------|
| **backend** | 8000 | Main API — search, CSV import, availability queries |
| **z3950** | 8001 | Z39.50 proxy — ALADI catalog availability |
| **postgres** | 5432 (internal) / 5433 (host) | PostgreSQL 15 database |

## Availability Services

| Service | Source | Rate Limit | Cache |
|---------|--------|------------|-------|
| **Z39.50** | ALADI catalog (yaz-client) | 1 req/sec (shared) | 24h |
| **eBiblio** | Catalan library network | 1 req/sec (shared) | 24h |
| **Todostuslibros** | Spanish booksellers | 1 req/sec (shared) | 24h |

## Main flows

### 1. Book search (`GET /search/by-title`)

```
Client                Backend                  Google Books
  │                      │                          │
  │  ?title=X&author=Y   │                          │
  ├─────────────────────►│                          │
  │                      │  check_cache(query)      │
  │                      ├──► DB                    │
  │                      │◄── hit? → return cached  │
  │                      │                          │
  │                      │  miss → search_books()   │
  │                      ├─────────────────────────►│
  │                      │◄─────────────────────────┤
  │                      │                          │
  │                      │  insert_books() + cache  │
  │                      ├──► DB                    │
  │                      │                          │
  │  ◄── JSON books ─────┤                          │
```

### 2. Goodreads CSV import (`POST /import/goodreads-csv`)

```
Client                Backend                  Google Books
  │                      │                          │
  │  CSV file upload     │                          │
  ├─────────────────────►│                          │
  │                      │  parse CSV               │
  │                      │  for each book:          │
  │                      │    check cache           │
  │                      │    if miss:              │
  │                      │      rate_limit (1/sec)  │
  │                      │      search Google ─────►│
  │                      │      ◄───────────────────┤
  │                      │      persist + cache     │
  │                      │  end loop                │
  │  ◄── JSON books ─────┤                          │
```

### 3. Library availability (`GET /availability/{service}`)

Supported services: `/availability/z3950`, `/availability/ebiblio`, `/availability/todostuslibros`

```
Client          Backend              Service              External
  │                │                    │                     │
  │  ?book_id=78   │                    │                     │
  ├───────────────►│                    │                     │
  │                │  get_availability()│                     │
  │                ├──► DB query        │                     │
  │                │◄── cached < 24h? ──┤                     │
  │                │  YES  ◄─────────────────────────────────┐
  │                │  return cached (no external call)       │
  │                │                                        │
  │                │  NO → check semaphore (1 concurrent)   │
  │                ├────────────────────────────────────┐   │
  │                │    async with _semaphore:         │   │
  │                │    call external service ──────────┼──►│
  │                │    ◄──────── response ────────────┐│   │
  │                │                                   ││   │
  │                │  save to DB (expires in 24h)     ││   │
  │                ├──► DB write ◄──────────────────────┘   │
  │                │                                        │
  │  ◄── JSON ─────┤                                        │
```

## Tech stack

| Layer | Technology |
|-------|------------|
| API Framework | FastAPI (async) |
| ORM | SQLModel + SQLAlchemy (async) |
| Database | PostgreSQL 15 + asyncpg |
| Migrations | Alembic |
| HTTP Client | httpx (async) |
| Z39.50 | yaz-client (CLI wrapper) |
| Containers | Docker Compose |

## Data model

```
┌─────────────┐     ┌────────────────┐     ┌────────────────┐
│   books     │     │ search_query   │     │  search_cache  │
├─────────────┤     ├────────────────┤     ├────────────────┤
│ id          │◄────┤ id             │◄────┤ id             │
│ title       │     │ query (unique) │     │ id_book (FK)   │
│ author      │     └────────────────┘     │ id_search (FK) │
│ isbn        │                            └────────────────┘
│ publisher   │
│ language    │     ┌─────────────────────┐
│ normal_title│     │ book_establishment  │
│ normal_auth │     ├─────────────────────┤
│ created_at  │◄────┤ id                  │
└─────┬───────┘     │ book_id (FK)        │
      │             │ establishment_id(FK)│────►┌────────────────┐
      │             │ language            │     │ establishments │
      │             │ status              │     ├────────────────┤
      │             └─────────────────────┘     │ id             │
      │                                         │ name (unique)  │
      │             ┌─────────────────┐         │ type           │
      │             │   user_books    │         └────────────────┘
      │             ├─────────────────┤
      └─────────────┤ book_id (FK)    │
                    │ user_id (FK)    │────►┌──────────┐
                    │ shelf_status    │     │  users   │
                    │ rating          │     ├──────────┤
                    │ review_text     │     │ id       │
                    └─────────────────┘     │ username │
                                            │ email    │
                                            └──────────┘
```

## Quick Start

```bash
# 1. Configure environment variables
cp .env.example .env
# Edit .env with PostgreSQL credentials and Google API key

# 2. Start services
make build

# 3. Run migrations
make migrate

# 4. Test
curl "http://localhost:8000/"
curl "http://localhost:8000/search/by-title?title=don+quixote&author=cervantes"
curl "http://localhost:8000/availability/z3950?book_id=1&catalog=aladi"
curl "http://localhost:8000/availability/ebiblio?book_id=1&catalog=ebiblio"
curl "http://localhost:8000/availability/todostuslibros?book_id=1"
```

## Makefile

| Command | Description |
|---------|-------------|
| `make build` | Build + up all containers |
| `make up` | Start existing containers |
| `make down` | Stop containers |
| `make migrate` | Run Alembic migrations |
| `make new-migration m="description"` | Create a new migration |
| `make migration-history` | View migration history |

## Endpoints

| Method | Route | Description |
|--------|-------|-------------|
| `GET` | `/` | Health check |
| `GET` | `/search/by-title` | Search books by title and/or author |
| `POST` | `/import/goodreads-csv` | Import Goodreads CSV |
| `GET` | `/availability/z3950` | Check availability in ALADI libraries (cached 24h) |
| `GET` | `/availability/ebiblio` | Check availability in Catalan libraries (cached 24h) |
| `GET` | `/availability/todostuslibros` | Check availability at booksellers (cached 24h) |

## API documentation

With services running:
- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc
- **Z39.50 health**: http://localhost:8001/health
