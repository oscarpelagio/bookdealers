# To-Fix — BookTracker

## CRITICO — Bugs activos

### 1. `datetime` naive/aware inconsistente
**Archivos:** `backend/app/models/users.py`, `backend/app/models/user_book.py`

`datetime.now(timezone.utc)` genera datetimes **timezone-aware**, pero las columnas PostgreSQL son `TIMESTAMP WITHOUT TIME ZONE`. Ya corregido en `Book`, `Establishment` y `BookEstablishment`, pero estos 2 modelos siguen rotos — fallarán al insertar.

**Fix:** Cambiar `datetime.now(timezone.utc)` → `datetime.utcnow` en ambos archivos.

---

### 2. `import httpx` sin usar en `z3950_router.py`
**Archivo:** `backend/app/router/endpoints/z3950_router.py` línea 6

Import muerto. Indica que antes se hacía la llamada HTTP directamente en el router.

**Fix:** Eliminar `import httpx`.

---

### 3. `NormalizationUtils` no se usa en `z3950_service.py`
**Archivo:** `backend/app/services/z3950_service.py` línea 8

Import muerto.

**Fix:** Eliminar `from app.utils import NormalizationUtils`.

---

### 4. `EstablishmentRepository` nunca se usa
**Archivo:** `backend/app/crud/establishment_repository.py`

Está registrado en `__init__.py` pero ningún servicio ni dependency lo inyecta. Además, su método `insert_establishment` tiene el tipo `list[Establishment]` pero lo trata como `list[str]` — bug de tipos.

**Fix:** Eliminar el archivo y su referencia en `__init__.py`, o integrarlo si se necesita.

---

## ALTO — Eficiencia / Performance

### 5. `save_availability` hace N+1 queries por ítem
**Archivo:** `backend/app/crud/availability_repository.py` método `save_availability`

Para cada biblioteca del resultado (pueden ser 150+):
- 1 SELECT para buscar establishment
- 1 INSERT + COMMIT si no existe
- 1 SELECT para buscar relación existente
- 1 INSERT o UPDATE

Con 179 resultados = ~540 queries + ~180 commits individuales.

**Fix:**
- Bulk insert establishments con `on_conflict_do_nothing`
- Cachear establishments en memoria durante el loop
- Un solo commit al final

---

### 6. `check_cache` en SearchRepository hace N+1 queries
**Archivo:** `backend/app/crud/search_repository.py` método `check_cache`

Primero obtiene las relaciones, luego hace `db.get(Book, id)` **por cada relación**.

**Fix:** Un solo JOIN:
```python
select(Book).join(SearchRelation).where(SearchRelation.id_search == ...).limit(max_results)
```

---

### 7. `save_cache` hace commit por cada relación
**Archivo:** `backend/app/crud/search_repository.py` método `_insert_relation`

`commit()` en cada iteración. Con 10 libros = 10 commits.

**Fix:** Batch insert + 1 commit al final.

---

### 8. `insert_books` hace 1 SELECT por libro
**Archivo:** `backend/app/crud/book_repository.py` método `insert_books`

`find_by_title_author` se llama para cada libro del batch. Con 10 resultados = 10 SELECTs.

**Fix:** Un solo query con `WHERE (normal_title, normal_author) IN (...)`.

---

### 9. `Z3950Client` crea/destruye un `httpx.AsyncClient` en cada llamada
**Archivo:** `backend/app/clients/z3950_client.py`

`async with httpx.AsyncClient()` no reutiliza conexiones, a diferencia de `GoogleBooksClient` que sí lo hace.

**Fix:** Reutilizar un client persistente como en `GoogleBooksClient`.

---

## MEDIO — Diseño / Mantenibilidad

### 10. `GoogleBooksClient._client` es atributo de clase, no de instancia
**Archivo:** `backend/app/clients/google_client.py` línea 11

`_client` es compartido entre todas las instancias. Combinado con `@lru_cache()` en dependencies, funciona por casualidad, pero es frágil.

**Fix:** Mover `_client` a `__init__` como atributo de instancia.

---

### 11. Código comentado en `google_adapter.py`
**Archivo:** `backend/app/adapters/google_adapter.py` líneas 22-32

Versión anterior de `build_search` comentada.

**Fix:** Eliminar código comentado.

---

### 12. `search_and_process` no valida que `title` y `author` no sean ambos `None`
**Archivo:** `backend/app/services/search_service.py` método `search_and_process`

Si llamas `/search/by-title` sin parámetros, construirá un query vacío y buscará en Google Books con string vacío.

**Fix:** Validar al inicio del método o en el endpoint.

---

### 13. `z3950_service.search_book` no maneja `book = None`
**Archivo:** `backend/app/services/z3950_service.py` método `search_book`

Si `book_id` no existe, `get_by_id` retorna `None` y `book.normal_title` lanza `AttributeError`.

**Fix:** Raise `HTTPException(404)` si book es None.

---

### 14. No hay `response_model` en `/availability/search`
**Archivo:** `backend/app/router/endpoints/z3950_router.py`

Devuelve `list[dict]` sin tipo. No hay validación de respuesta ni documentación OpenAPI útil.

**Fix:** Crear un schema `AvailabilityResponse` y usarlo como `response_model`.

---

### 15. `import_goodreads_csv` no devuelve progreso
**Archivo:** `backend/app/services/search_service.py` método `import_goodreads_csv`

Con muchos libros (100+), el endpoint tarda minutos (1 req/seg por rate limiter). No hay SSE, WebSocket ni respuesta parcial.

**Fix:** Implementar SSE o background task con polling.

---

### 16. `CsvUtils.parse_goodreads_book` extrae campos que nunca se usan
**Archivo:** `backend/app/utils/csv_utils.py`

Extrae `my_rating`, `average_rating`, `bookshelves`, etc., pero `import_goodreads_csv` solo usa `title` y `author`. El resto se descarta.

**Fix:** Extraer solo lo necesario, o usar los campos extra para enriquecer el UserBook.

---

## BAJO — Estilo / Convenciones

### 17. Mezcla de idiomas
Catalán en docstrings/nombres de archivos, castellano en comentarios, inglés en variables.

**Fix:** Escoger un idioma y ser consistente.

---

### 18. `_insert_search_` tiene trailing underscore innecesario
**Archivo:** `backend/app/crud/search_repository.py` línea 53

**Fix:** Renombrar a `_insert_search`.

---

### 19. `BookBase` como base de `Book` (table model)
**Archivos:** `backend/app/schemas/book.py`, `backend/app/models/book.py`

`Book` hereda de `BookBase` (schema) y agrega `table=True`. Acopla schema de validación al modelo de DB.

**Fix:** Separar modelos de DB y schemas de API completamente si divergen.

---

### 20. `get_user() -> int: return 1`
**Archivo:** `backend/app/router/dependencies.py` línea 66

Stub hardcodeado.

**Fix:** Implementar autenticación real o marcarlo claramente como TODO.

---

### 21. `echo=True` en el engine
**Archivo:** `backend/app/core/db.py` línea 20

Loguea cada query SQL a stdout. Bien para debug pero ruidoso en producción.

**Fix:** Hacerlo configurable via variable de entorno (`DEBUG_SQL=true`).

---

### 22. Requirements sin pinear versiones
**Archivo:** `backend/requirements.txt`

`fastapi`, `sqlmodel`, etc. sin versión fija. Un `docker build` mañana puede romper todo.

**Fix:** Pinear versiones (`fastapi==0.115.x`, `sqlmodel==0.0.37`, etc.).

---

## Resumen

| Prioridad | # Issues | Acción clave |
|-----------|----------|-------------|
| **Critico** | 1, 2, 3, 4 | Fix datetime en User/UserBook, eliminar imports muertos, borrar EstablishmentRepository |
| **Alto** | 5, 6, 7, 8, 9 | Reducir queries N+1 con JOINs y batch operations |
| **Medio** | 10-16 | Validaciones, error handling, response models |
| **Bajo** | 17-22 | Estilo, configuración, versiones |


**Done:** Crical : 2 - 3 - 1 -
