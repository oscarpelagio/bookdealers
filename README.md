# BookTracker

Sistema de tracking de libros personales con búsqueda en Google Books y consulta de disponibilidad en bibliotecas catalanas (red ALADI) via protocolo Z39.50.

## Arquitectura

```
┌─────────────────────────────────────────────────────────────────┐
│                        Docker Compose                           │
│                                                                 │
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
```

## Servicios

| Servicio | Puerto | Descripción |
|----------|--------|-------------|
| **backend** | 8000 | API principal — búsqueda, import CSV, persistencia |
| **z3950** | 8001 | Proxy Z39.50 — consulta disponibilidad en bibliotecas |
| **postgres** | 5432 (interno) / 5433 (host) | Base de datos PostgreSQL 15 |

## Flujos principales

### 1. Búsqueda de libros (`GET /search/by-title`)

```
Cliente                Backend                  Google Books
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

### 2. Import CSV Goodreads (`POST /import/goodreads-csv`)

```
Cliente                Backend                  Google Books
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

### 3. Disponibilidad bibliotecas (`GET /availability/search`)

```
Cliente          Backend              Z3950 Service          ALADI
  │                │                      │                    │
  │  ?book_id=78   │                      │                    │
  ├───────────────►│                      │                    │
  │                │  get_availability()  │                    │
  │                ├──► DB                │                    │
  │                │◄── hit? → return     │                    │
  │                │                      │                    │
  │                │  miss → get book     │                    │
  │                ├──► DB                │                    │
  │                │                      │                    │
  │                │  search_z3950()      │                    │
  │                ├─────────────────────►│                    │
  │                │                      │  yaz-client ──────►│
  │                │                      │  ◄─── MARC data  ──┤
  │                │  ◄── parsed locs  ───┤                    │
  │                │                      │                    │
  │                │  save_availability() │                    │
  │                ├──► DB                │                    │
  │                │                      │                    │
  │  ◄── JSON ─────┤                      │                    │
```

## Stack tecnológico

| Capa | Tecnología |
|------|-----------|
| API Framework | FastAPI (async) |
| ORM | SQLModel + SQLAlchemy (async) |
| Base de datos | PostgreSQL 15 + asyncpg |
| Migraciones | Alembic |
| HTTP Client | httpx (async) |
| Z39.50 | yaz-client (CLI wrapper) |
| Contenedores | Docker Compose |

## Modelo de datos

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
# 1. Configurar variables de entorno
cp .env.example .env
# Editar .env con credenciales de PostgreSQL y Google API key

# 2. Levantar servicios
make build

# 3. Ejecutar migraciones
make migrate

# 4. Probar
curl "http://localhost:8000/"
curl "http://localhost:8000/search/by-title?title=don+quijote&author=cervantes"
curl "http://localhost:8000/availability/search?book_id=1"
```

## Makefile

| Comando | Descripción |
|---------|-------------|
| `make build` | Build + up de todos los contenedores |
| `make up` | Levantar contenedores existentes |
| `make down` | Parar contenedores |
| `make migrate` | Ejecutar migraciones Alembic |
| `make new-migration m="descripcion"` | Crear nueva migración |
| `make migration-history` | Ver historial de migraciones |

## Endpoints

| Método | Ruta | Descripción |
|--------|------|-------------|
| `GET` | `/` | Health check |
| `GET` | `/search/by-title` | Buscar libros por título y/o autor |
| `POST` | `/import/goodreads-csv` | Importar CSV de Goodreads |
| `GET` | `/availability/search` | Consultar disponibilidad en bibliotecas |

## Documentación API

Con los servicios levantados:
- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc
- **Z39.50 health**: http://localhost:8001/health
