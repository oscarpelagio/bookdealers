# BookDealers — Plataforma Social tipo Goodreads
## Documento de Arquitectura y Diseño de Dominio (Fase 0)

> **Estado:** Documento de diseño. **No implementado.** Revisiones y aprobación antes de empezar a codificar.
> **Ámbito:** evolución del monobloque modular existente. Sin microservicios de negocio.

---

# ⚠️ DISCLAIMER (regla de oro de implementación)

**NO se toca NADA de lo ya construido del dominio de libros y búsquedas:**
`books`, `catalogs`, `establishments`, `book_establishment`, `search_cache`,
los flujos de búsqueda (Google/OpenLibrary/Z39.50), import de CSV, y el
módulo `auth` (excepto consumo de sus dependencias públicas como
`get_current_user`).

**Solo se construye la parte social** (perfiles, estanterías, reviews, social,
posts, listas, feed, notificaciones, búsqueda social).

**Regla:** cualquier modificación que se necesite hacer sobre código existente
(`app/models/__init__.py`, `app/router/router.py`, `app/main.py`,
`tests/conftest.py`, etc.) será **aditiva** (imports, registros, handlers) y
**se avisará explícitamente** al usuario antes de aplicarla y en el commit.
Si la modificación no fuera aditiva, se pausa y se pregunta.

---

# 0. Contexto y reglas de evolución

## 0.1 Inventario del estado actual (lo que NO se toca)

| Dominio | Lo que ya existe | Dónde vive |
|---|---|---|
| Autenticación | `User`, `Role`, `UserRole`, `RefreshToken`, `EmailVerificationToken`, `PasswordResetToken` · soft delete · lockout · JWT+Google · RBAC | `app/auth/` (módulo autocontenido) |
| Catálogo | `Book` (denormalizado, `author` como string, ISBN, normal_title/author) | `app/models/book.py`, `app/crud/` |
| Disponibilidad | `Establishment`, `Catalog`, `BookEstablishment`, `Search`/`SearchRelation` | `app/models/`, `app/crud/`, `app/services/`, `app/clients/`, `app/adapters/` |
| Búsqueda externa | Google, OpenLibrary, Z39.50 (síncrono, semáforo 1 req/s) | `app/services/`, `app/clients/` |

Patrón general ya consolidado:
```
router (fino) → service (lógica + orquestación) → repository/crud (persistencia) → models
                                               ↘ clients (HTTP) + adapters (transform) → servicios externos
```
- DI vía `Depends`; `get_current_user` en `app/auth/dependencies.py`.
- Excepciones de dominio con `status_code` + `code` estable (patrón `AuthError`).
- UUID como PK para modelos sociales; **los `books` usan `id: int`** (PK mixtas, cuidar las FKs).
- Sesión async `AsyncSession` (`app/core/deps.get_db`).
- `app/models/__init__.py` reexporta todos los modelos → **Alembic y `create_all` los detectan importando `app.models`**.
- Migraciones Alembic autogeneradas (`make new-migration m="..."`), timestamps timezone-aware donde hace falta.

## 0.2 Decisiones arquitectónicas (ADRs compactos)

| # | Decisión | Por qué |
|---|---|---|
| ADR-1 | **Monobloque modular**: cada contexto funcional es un paquete autocontenido dentro de la misma API | Igual que `app/auth/`. Cero Latencia de cómputo, sin infra, fácil de partir si algún día hace falta |
| ADR-2 | **El `User` del módulo auth es la única identidad.** `Profile` es 1:1 con User, no una segunda tabla de usuarios | Evita duplicidad de identidad y syncs de auth |
| ADR-3 | **`books` se mantiene denormalizado (author string)**. No se normaliza a Authors/Editions ahora | Normalizar es un refactor masivo de catálogo+availability+búsqueda+import. Se añadirá `authors` cuando haga falta (páginas de autor). Los contextos sociales referencian `books.id` (int) |
| ADR-4 | **Visibilidad por contexto**: toda lectura pública pasa por un `VisibilityService` que aplica `privacy_settings` + `block` + `mute` + estado del usuario | Centraliza las reglas de contenido y evita olvidos por consulta |
| ADR-5 | **El estado de lectura se deriva de `user_books.status`**, no se duplica en las shelf de estado. `shelf_items` solo para estanterías CUSTOM | Evita doble escritura y ambigüedad (libro en dos estanterías de estado) |
| ADR-6 | **Feed y recomendaciones son read-models (pull-on-read)** en v1, no tablas masivas | Escala de sobra para Goodreads-size; se materializa solo si el rendimiento lo exige (Timeline/Ranking/FeedGenerator como servicios) |
| ADR-7 | **Eventos en proceso** (in-process async bus), admin tras commit. Sin outbox/Saga | Escala actual. Se introduce outbox/kafka solo cuando haya varios workers y delivery confiable de emails |
| ADR-8 | **Soft delete en contenido público** (reviews, posts, comments, lists); **hard delete en relaciones efímeras** (shelf_item, follow, like, user_book) | Moderación + restaurar + referencias a actividad; las efímeras no aportan valor histórico |
| ADR-9 | Contadores agregados (`books.rating_avg/count`, `review_count`) **denormalizados** y actualizados vía eventos en la misma transacción | Evita agregar por libro en cada vista; decisión de read-model |
| ADR-10 | `activities` es append-only con `object_type`/`object_id` polimórfico (sin FK) | Alta escritura, referencias a múltiples agregações; integridad se resuelve en la consulta |

## 0.3 Reglas transversales (invariantes globales)

1. **Cada usuario posee todo su contenido (ownership).** FK de todo contenido → `users.id` ON DELETE CASCADE.
2. **Usuario soft-deleted o desactivado ⇒ su contenido público se oculta** en todas las lecturas (nunca más bloqueado), aunque las filas sigan en BD.
3. **Autores: verificada `/birth `de tu propio contenido** (no puedes auto-seguir, auto-bloquear, auto-like).
4. **Un `block` deshace los `follow` del mismo tetra ambos sentidos** y oculta el contenido del blocker al blocked y viceversa.
5. **Toda identificación oculta se basa en `_id`** (UUID); no se usa `username` como clave foránea.
6. **`created_at`/`updated_at` timezone-aware (`timestamptz`)** en todos los agregados.
7. **Contenido polimórfico referenciado por `object_type` + `object_id`**: sin FK, integridad por servicio.

---

# FASE 1 — Diseño del dominio

## 1.1 Mapa de bounded contexts

```
┌─────────────────────────────────────────────────────────────────────────┐
│  IDENTITY (existing "auth")                                             │
│  Aggregado raíz: User, Role, Session(refresh)                           │
└───────────────▲────────────────────────────────────────────┬────────────┘
                │ 1:1                                          │ owned by
┌───────────────────────────┐   ┌──────────────────────────────▼──────────┐
│ CATALOG (existing)        │   │ PROFILES (nuevo)                         │
│ Book (root) · Availability│   │ Profile (root) · Preferences · Privacy    │
│ · Establishment · Catalog │   │ ReadingGoal · (ReadingStats read-model)  │
└──────────▼────────────────┘   └──────────────────────────────────────────┘
            │ books.id (int) ▲
 ┌─────────▼───────────────┐ │ ┌──────────────────────────────────────────┐
 │ LIBRARY / SHELVES       │ │ │ REVIEWS                                   │
 │ UserBook (root)         │──┘ │ Rating (root) · Review (root) ·          │
 │  ◄ Rating (owned)       │    │  ReviewLike (owned for Review)           │
 │  ◄ ReadingProgress(log) │    │   // Rating también existe solo           │
 │ Shelf (root)            │    │   // Review puede referir Rating          │
 │  ◄ ShelfItem (custom)   │    └───────────────────┬──────────────────────┘
 └──────────┬──────────────┘                        │ (ReviewUser)
            │ events (shelf_updated, rating, ...)   │ events
 ┌──────────▼───────────────────────────┐   ┌───────▼──────────────────────┐
 │ SOCIAL GRAPH                         │   │ POSTS & ENGAGEMENT            │
 │ Follow · Block · Mute · Report       │   │ Post (root) · Comment (root)  │
 │ Activity (append-only stream)        │   │  ◄ post_likes / comment_likes │
 │                                       │   │ Media (owned) · Mention      │
 └──────────────────┬────────────────────┘   └──────────────┬───────────────┘
                    │ activities                            │ posts/comments
 ┌──────────────────▼────────────────────┐   ┌──────────────▼───────────────┐
 │ FEED & DISCOVERY (read-models)        │   │ NOTIFICATIONS                 │
 │ Timeline · Ranking · Recommendations  │   │ Notification (root)           │
 │ FeedGenerator → lazy pull             │   │ · NotificationSettings        │
 └────────────────────────────────────────┘   │ · PushQueue (technical)      │
                                              └──────────────────────────────┘
        ┌───────────────────────────────────────────────────────────────────┐
        │ LISTS  List (root) · ListItem · Collaborator                       │
        │ SEARCH social: search_users / search_books / search_posts (queries)│
        └───────────────────────────────────────────────────────────────────┘
```

## 1.2 Bounded context — IDENTITY (exists, no cambios de dominio)

- **Aggregate root:** `User`
- **Entidades:** `User` (raíz), `Role`, `Session` (RefreshToken) → muchos a uno con User.
- **Invariantes existentes:** único email/username/google_sub activo (índices parciales); soft delete; lockout.
- **Evolución futura del dominio:** ningún cambio aquí salvo que `Profile` cubra datos públicos.

## 1.3 Bounded context — CATALOG (exists)

- **Aggregate root:** `Book` (id int).
- **Entidades:** `Book`, `Establishment`, `Catalog`, `BookEstablishment` (availability).
- **Decisiones:** se añadirá `rating_avg`, `rating_count`, `review_count` (ADR-9). `Authors/Editions` como contexto futuro, no ahora (ADR-3).

## 1.4 Bounded context — PROFILES

**Aggregate root: `Profile`** (1:1 con `User`).
- **Entidades:** `Profile` (root). `Preferences` y `PrivacySettings` son **value-objects embebidos** del agregado (1:1, parte del Profile, no aggregates separados) — no se pueden modificar sin su User/Profile, viven y mueren con él. `ReadingGoal` es un agregado propio (varios por año).

**Value Objects:**
- `Visibility ::= PUBLIC | FOLLOWERS | PRIVATE`
- `Handle` (slug del usuario, no editable o editable con colisión controlada)
- `Year` (para goals)

**Relaciones:** Profile 1:1→User. ReadingGoal N:1→User.

**Ownership:** todo pertenece a User. **Lifecycle:** Profile nace automáticamente en el registro/backfill; vive con User; si User se soft-deletea, el Profile se oculta (no se borra).

**Invariantes:**
- Cada User tiene exactamente **un** Profile (creado automáticamente, backfill en migración).
- `PrivacySettings` define 5 visibilidades por sección (perfil, librería, reviews, lists, activity) + `allow_follows`, `show_reading_progress`.
- Un usuario **no puede tener visibilidad PRIVATE en librería** si además publica reviews (reviews necesitan ser válidas — a nivel de reglas se permite; se documenta como regla de producto, no de BD).

## 1.5 Bounded context — SHELVES / LIBRARY

**Aggregate roots: `UserBook` y `Shelf`.**

### `UserBook` (raíz — la relación del usuario con un libro)
- **Entidades owned:** `Rating` (1:0..1, `sumary` opcional), `ReadingProgress` (log histórico 0..N).
- **Q** `ReadingStatus :: WANT_TO_READ|READING|READ|DNF`
- **Relaciones:** User N:1; Book N:1; Review 0..1 (apunta al Review de ese user+book).

**Ownership:** User. **Lifecycle:** se crea al añadir el libro a un estado; cambia `status` a lo largo del tiempo (puede ir READING→READ→DNF); **hard delete** cuando el usuario saca el libro de la librería.
- Marca `started_at`/`finished_at` se actualiza automáticamente al cambiar de estado.

**Invariantes:**
- Único UserBook por (user_id, book_id).
- Progress: `current_page <= book.page_count` (cuando `page_count` existe).
- El status shelf **deriva de** `user_books.status` (ADR-5). No se puede crear Item en una shelf STATUS directamente.

### `Shelf` (raíz)
- **Entidades owned:** `ShelfItem` (0..N).
- **Relaciones:** Shelf N:1 User · ShelfItem M:N a Book (a través de shelf_items).
- **Lifecycle:** al registrar un User, se **seedan 3 estanterías de estado** (to-read, currently-reading, read, `kind=STATUS`) + opción de custom. Custom: crear/renombrar/borrar (borrar vacía o la reasigna).

**Invariantes:**
- Slug único por user (nombre de estantería).
- `ShelfItem` **solo** en estanterías `CUSTOM` (no STATUS) — la de ESTADO la controla `UserBook.status` (ADR-5).
- Único ShelfItem por (user_id, shelf_id, book_id).

## 1.6 Bounded context — REVIEWS

**Aggregate roots: `Rating` y `Review`.**

### `Rating` (raíz)
- **QO:** `Score` (1..5 enteros).
- **Ownership:** User.
- **Lifecycle:** se crea al valorar sin/ca con review. **hard delete** (borrar review no borra rating si ya existía → deixa el score). Actualizable.

**Invariantes:**
- Único Rating por (user_id, book_id).
- `score BETWEEN 1 AND 5` `CHECK`.

### `Review` (raíz)
- **Entidades owned:** `ReviewLike` (0..N).
- **QO:** `Spoiler`, `ReviewStatus` (PUBLISHED|HIDDEN|DELETED vía `deleted_at`), `Language`.
- **Lifecycle:** se publica con rating opcional (si no hay rating se crea uno) → se crea `Rating` en la misma transacción (regla de producto). Se edita. **soft delete** → se puede re-revisitar (índice parcial de unicidad).
- Nota: si se borra un Review, su `Rating` queda (el score sobrevive).

**Invariantes:**
- Único Review activo por (user_id, book_id) (índice parcial `deleted_at IS NULL`).
- Para escribir Review (típico) requieres `UserBook`; al menos el `Rating` es obligatorio si publicas review (producto; puede tener cabida sin review).

## 1.7 Bounded context — SOCIAL GRAPH

**Aggregate roots:** `Follow`, `Block`, `Mute`, `Report`, `Activity` (cada uno es raíz, simple).

### `Activity` (append-only, raíz)
- **QO:** `Verb`, `Visibility`.
- Es el **log de eventos de UX** (no el mismo que el bus de eventos): `shelf_updated`, `rating_added`, `review_added`, `followed`, `joined`, `post_added`, `comment_added`, `list_created`, `goal_updated`, ...
- `object_type`/`object_id` polimórfico. `actor_id` (quien generó).
- **Lifecycle:** append-only, nunca se edita; TTL.

**Invariantes:**
- `follower_id != followee_id` (CHECK). etc.
- Un Block **borra** Follows a dos sentidos y activa visibilidad de ocultado.
- Mute: igual que Block pero solo silencia el feed, no oculta mecánicamente (cada consulta de feed lo filtra).

## 1.8 Bounded context — POSTS & ENGAGEMENT

### `Post` (raíz)
- **Entidades owned:** `Media` (0..N) (imágenes/vídeo), `Like` (0..N), y referencia opcional a `Book` y `Review`.
- **QO:** `PostType` (TEXT | BOOK_SHARE | MEDIA), `Visibility` (PUBLIC|FOLLOWED).
- **Ownership:** User. **Lifecycle:** published → edited → **soft deleted**.

**Invariantes:** el autor no puede auto-like; like único por (user, post).

### `Comment` (raíz)
- **Entidades owned:** `Like` (0..N), replies (via `parent_id`, **un solo nivel**).
- **QO:** `Visibility`.
- **Lifecycle:** soft delete. **Invariante:** comment hijo no puede tener hijo (solo 1 nivel de anidado; un reply no puede ser padre).

### `Mention` (entidad)
- Entidad polimórfica: `@user` dentro de Post o Comment. Se extraen al crear y generan notificación.

## 1.9 Bounded context — LISTS

**Aggregate root: `List`**
- **Entidades owned:** `ListItem` (0..n), `Collaborator` (0..n).
- **QO:** `Visibility`, `CollaboratorRole` (EDITOR|VIEWER).
- **Ownership:** User owner. **Lifecycle:** create → share/curate → **soft delete**.
- **Invariantes:** único ListItem por (list_id, book_id); único Collaboration por (list_id, user_id); los EDITOR pueden añadir/eliminar items, los VIEWER solo ver; solo la owner cambia título/privacidad.

## 1.10 Bounded context — FEED & DISCOVERY (read-models)

No agregates de dominio; son **proyecciones**:
- `Timeline` (feed de un usuario): mezcla `Activity` de follows + `Post` de follows + suscripciones, filtrado por `Visibility`, `block`/`mute`.
- `Ranking` / `Recommendations`: lecturas derivadas de ratings/reviews/datos.
- `FeedGenerator`: servicio de composición (pull-on-read, ADR-6), con **cursor pagination** (opaque key por `created_at`+id).

## 1.21 Bounded context — NOTIFICATIONS

**Aggregate root: `Notification`**
- **Entidades:** `Notification` (raíz, own) · `NotificationSettings` (owned value-ish) · `PushQueue` (técnica).

**QO:** `NotificationType`, `Channel` (IN_APP|EMAIL|PUSH).
**Lifecycle:** notification generada por eventos (`review_liked`, `comment`, `mention`, `follow`, `post_like`...) → **unread → read** → TTL/expiración.

**Invariantes:**
- Notificación dirigida a un recipient; actor nullable (si el actor se soft-deletea la notif persiste pero "de user anónimo").
- `NotificationSettings` define por canal qué tipos llegan (config JSONB de excepciones, ADR‑simple).

### 1.22 Search
- `search_users`, `search_books`, `search_posts` como **servicios/queries** sobre las mismas tablas con índices `pg_trgm` (trigram) en `handle`/`display_name`/`title` y FTS en textos. Sin tablas nuevas (adiós índice GIN).

---

# FASE 2 — Modelo SQL

> Convenciones: UUID PK (`gen_random_uuid()`), `timestamptz` + `DEFAULT now()`, `created_at`/`updated_at` no nulos. `id` del User = UUID (auth), `book_id` = INT (catálogo). Enums de PostgreSQL vs VARCHAR: **enums nativos** para estados cerrados (status, visibility, verb, notification type). `object_type` como VARCHAR (para polimorfi).

## 2.1 — TABLA `profiles`

| Columna | Tipo | Nulo | PK/FK/Unique |
|---|---|---|---|
| `id` | UUID | no | **PK** |
| `user_id` | UUID | no | FK `users.id` ON DELETE **CASCADE** · **UNIQUE** |
| `display_name` | VARCHAR(120) | sí | — |
| `bio` | TEXT | sí (500) | — |
| `location` | VARCHAR(120) | sí | — |
| `website` | VARCHAR(500) | sí | — |
| `avatar_url` | VARCHAR(500) | sí | — |
| `cover_url` | VARCHAR(500) | sí | — |
| `created_at` | timestamptz | no | — |
| `updated_at` | timestamptz | no | — |

**Índices:** `user_id` ya es UNIQUE. Se añadirá GIN trigram sobre `display_name`/`handle` cuando llegue search_users (el handle vive en `users.username`).
**Delete:** CASCADE (Profile no puede existir sin User). **Justificación:** 1:1 real, el Profile muere con el usuario.

Nota: `handle` público = `users.username` (ya existe y es único activo). No se replica en `profiles`.

## 2.2 — `profile_preferences` (owned, tabla de 1:1 por claridad)
| Columna | Tipo | Nulo | Notas |
|---|---|---|---|
| `id` | UUID | no | PK |
| `user_id` | UUID | no | FK users CASCADE · UNIQUE |
| `language` | VARCHAR(10) | sí | e.g. 'es', 'ca' |
| `default_review_visibility` | enum `visibility` (no) | sí | default PUBLIC |
| `reading_tracking_enabled` | BOOL | no | default TRUE |
| `content_languages` | VARCHAR ARRAY o JSONB | sí | idiomas de preferencia p/ recom |

## 2.3 — `privacy_settings` (parte del agregado Profile, tabla 1:1)
| Columna | Tipo | default |
|---|---|---|
| `id` PK, `user_id` UUID FK UNIQUE | | |
| `profile_visibility` | enum `visibility` | PUBLIC |
| `library_visibility` | enum `visibility` | PUBLIC |
| `reviews_visibility` | enum `visibility` | PUBLIC |
| `lists_visibility` | enum `visibility` | PUBLIC |
| `activity_visibility` | enum `visibility` | PUBLIC |
| `allow_follows` | BOOL | TRUE |
| `show_reading_progress` | BOOL | TRUE |
| `block_anonymous` | BOOL | FALSE |
| `created_at`, `updated_at` | timestamptz | |

## 2.4 — `reading_goals`
| `id` UUID PK | `user_id` UUID FK CASCADE | `year` SMALLINT | `books_goal` INT (sí) | `pages_goal` INT (sí) |
| **UNIQUE (user_id, year)** | created/updated |

## 2.5 — `shelves`
| Columna | Tipo | Nulo | Notas |
|---|---|---|---|
| `id` | UUID | no | PK |
| `user_id` | UUID | no | FK users CASCADE · idx |
| `name` | VARCHAR(80) | no | — |
| `slug` | VARCHAR(80) | no | — |
| `kind` | ENUM `shelf_kind` (**STATUS** \| **CUSTOM**) | no | |
| `is_default` | BOOL | no | true para seeded |
| `is_private` | BOOL | no | default FALSE |
| `position` | INT | no | default 0 (orden de la lista) |
| `description` | VARCHAR(200) | sí | |
| `created_at`, `updated_at` | | |

**Unique:** `UNIQUE (user_id, slug)`. **Índice:** `(user_id, kind)`. **Delete:** `shelf_items` CASCADE (borrar estantería borra sus items).
**Justificación:** kind separa la galaxia poderosa; `is_private` para estantes privadas.

## 2.6 — `user_books` (raíz del shelf)
| Column | Tipo | Nulo | Notas |
|---|---|---|---|
| `id` | UUID | no | PK |
| `user_id` | UUID | no | FK users CASCADE |
| `book_id` | INT | no | FK books(id) **ON DELETE RESTRICT** |
| `status` | enum `reading_status` | no | WANT_TO_READ\|READING\|READ\|DNF |
| `current_page` | INT | sí | |
| `percent_read` | NUMERIC(5,2) | sí | 0–100 |
| `started_at` | DATE | sí | se autoasigna READING |
| `finished_at` | DATE | sí | se autoasigna READ/DNF |
| `notes` | TEXT | sí | privado del usuario |
| `created_at`, `updated_at` | | |

**Unique:** `UNIQUE (user_id, book_id)`. **Índices:** `(user_id, status)`, `(book_id)`. 
**Delete:** user CASCADE (contenido del user); book RESTRICT (no borrar libro con vida social — protección del catálogo).
**CHECK app:** `current_page <= book.page_count` cuando book.page_count no nulo (tomado en service).

## 2.7 — `shelf_items` (only CUSTOM shelves)
| Column | Type | Notas |
|---|---|---|
| `id` | UUID PK | |
| `user_id` | UUID | FK users CASCADE · denormalizado para joins + idx |
| `shelf_id` | UUID | FK `shelves(id)` **ON DELETE CASCADE** |
| `book_id` | INT | FK books RESTRICT |
| `created_at` | | |
**Unique:** `UNIQUE (user_id, shelf_id, book_id)`. **Índices:** `(shelf_id)`, `(user_id, book_id)`. No `kind` en item: solo shelves CUSTOM (ADR-5).

## 2.8 — `reading_progress` (historial append-only)
| `id` UUID PK · `user_book_id` UUID FK `user_books` CASCADE · `page` INT (sí) · `percent_read` NUMERIC · `channel_note` TEXT sí · `created_at` |
**Índice:** `(user_book_id, created_at DESC)`.

## 2.9 — `ratings`
| `id` UUID PK · `user_id` UUID FK CASCADE · `book_id` INT FK RESTRICT · **`score` SMALLINT CHECK (score BETWEEN 1 AND 5)** · `created_at`, `updated_at` |
**Unique:** `UNIQUE (user_id, book_id)`. **Índices:** `(book_id)` (para media), `(user_id)`. **Delete:** RESTRICT del book.

## 2.10 — `reviews`
| `id` UUID PK · `user_id` UUID FK CASCADE · `book_id` INT FK RESTRICT · `title` VARCHAR(200) sí · `body` TEXT sí · `rating_id` UUID FK ratings **ON DELETE SET NULL** (si se borra rating → review pierde score) o NULL · `language` VARCHAR(10) sí · `spoiler` BOOL default FALSE · `status` → **soft delete** via `deleted_at` · `created_at` · `updated_at` |
**UNIQUE parcial:** `(user_id, book_id) WHERE deleted_at IS NULL`. **Índices:** `(book_id, created_at DESC)`, `(user_id)`, `(rating_id)` UNIQUE.
**Delete:** CASCADE usuario (RESTRICT del labro). Para re-review tras borrado necesitas soft delete → se re-crea por el user+book.

## 2.11 — `review_likes`
| `id` UUID PK · `user_id` FK CASCADE · `review_id` FK reviews **CASCADE** · `created_at` | **UNIQUE (user_id, review_id)**. Índice `(review_id)`.

## 2.12 — `follows`
| `id` UUID PK · `follower_id` UUID FK CASCADE · `followee_id` UUID FK CASCADE (users) · `created_at` |
**UNIQUE (follower, followee)**. **CHECK (follower_id <> followee_id)**. **Índices:** `(followee_id)` (seguidores de X), `(follower_id)` (a quién sigo). **Delete:** CASCADE — si hay block, el service borra la fila y la del reverso.

## 2.13 — `blocks`
| `id` UUID PK · `blocker_id` FK CASCADE · `blocked_id` FK CASCADE · `created_at` |
**UNIQUE (blocker, blocked)** · **CHECK (blocker <> blocked)**.

## 2.14 — `mutes`
| `id` UUID PK · `muter_id` FK CASCADE · `mutee_id` FK CASCADE · `created_at` |
**UNIQUE (muter, mutee)** · CHECK !=.

## 2.15 — `reports`
| `id` UUID PK · `reporter_id` UUID FK users CASCADE · `target_type` enum `report_target` (USER\|POST\|COMMENT\|REVIEW\|LIST) · `target_id` UUID (polimorfi, sin FK) · `reason` VARCHAR(200) no · `details` TEXT sí · `status` enum `report_status` (OPEN/REVIEWING/RESOLVED/DISMISSED) · `resolved_by` UUID FK users SET NULL sí · `created_at` · `resolved_at` |
**Índices:** `(status)`, `(target_type, target_id)`.

## 2.16 — `activities` (append-only)
| `id` UUID PK · `actor_id` UUID FK users **ON DELETE SET NULL** · `verb` enum `activity_verb` · `object_type` enum `object_type` (POST/COMMENT/REVIEW/RATING/LIST/GOAL/USER_BOOK) sí · `object_id` UUID · `target_type`/`target_id` sí · `visibility` enum `visibility` (al crearse, copia de privacy del actor) sí · `created_at` |
**Índices:** `(actor_id, created_at DESC)`, parcial `WHERE visibility='PUBLIC'` (feed público), `(object_type, object_id)`.
**Delete:** SET NULL actor (si se borra el usuario, la actividad de "X ha seguido a Y" sigue pero como anónimo) → útil para audit. Append-only; no editar.

## 2.17 — `posts`
| `id` UUID PK · `author_id` UUID FK users CASCADE · `type` enum `post_type` (TEXT|BOOK_SHARE|MEDIA) · `body` TEXT no · `book_id` INT FK RESTRICT sí · `review_id` UUID FK reviews SET NULL sí · `visibility` enum `visibility` · `deleted_at` sí · `created_at` · `updated_at` |
**Índices:** `(author_id, created_at DESC)`, `(book_id)`. Eliminación CASCADE user; RESTRICT book.

## 2.18 — `post_media`
| `id` UUID PK · `post_id` FK posts CASCADE · `media_type` enum (IMAGE/VIDEO/AUDIO) · `url` VARCHAR(500) · `position` INT | 

## 2.19 — `likes` (Post / Comment / Review unificada opcional)
Decisión: mantengo **3 tablas separadas** (`post_likes`, `comment_likes`, `review_likes`) por integridad FK (la unified requiere FK polimórfica). Cada una:
`post_likes`: `id` PK · `user_id` FK CASCADE · `post_id` FK posts CASCADE · `created_at` · UNIQUE(user,post)
`comment_likes`: idem con comment.
*(en el doc se listan juntas)*.

## 2.20 — `comments`
| `id` UUID PK · `post_id` FK posts **CASCADE** · `parent_id` UUID FK comments **SET NULL** · `author_id` FK CASCADE · `body` TEXT no · `deleted_at` · `created_at` |
**Índices:** `(post_id, created_at)`, `(parent_id)`. **Nivel único de anidamiento** (invariante): parent no puede tener su propio parent.

## 2.21 — `mentions`
| `id` UUID PK · `content_type` enum `mention_target` (POST/COMMENT) · `content_id` UUID sin FK · `mentioned_user_id` UUID FK users CASCADE · `created_at` |
**UNIQUE (content_type, content_id, mentioned_user_id)** · **Índice `(mentioned_user_id)`.**

## 2.22 — `lists`
| `id` UUID PK · `owner_id` FK CASCADE · `title` VARCHAR(150) no · `description` TEXT sí · `visibility` enum · `slug` VARCHAR(160) no · `created_at` · `updated_at` |
**UNIQUE (owner_id, slug)** · **Índice (owner_id)**. soft delete `deleted_at`.

## 2.23 — `list_items`
| `id` UUID PK · `list_id` FK lists **CASCADE** · `book_id` INT FK RESTRICT · `added_by` UUID FK CASCADE · `note` VARCHAR(200) sí · `position` INT · `created_at` |
**UNIQUE (list_id, book_id)** · Índices `(list_id)`, `(book_id)`.

## 2.24 — `list_collaborators`
| `id` UUID PK · `list_id` FK CASCADE · `user_id` FK CASCADE · `role` enum `collaborator_role` (EDITOR/VIEWER) · `can_add_books` BOOL · `created_at` |
**UNIQUE (list_id, user_id)**.

## 2.25 — `notifications`
| `id` UUID PK · `recipient_id` FK users CASCADE · `actor_id` UUID FK **SET NULL** · `type` enum `notification_type` · `object_type` enum · `object_id` UUID (sin FK) · `message` TEXT sí (preview) · `read_at` timestamptz sí · `created_at` |
**Índices:** `(recipient_id, read_at)`, parcial `WHERE read_at IS NULL` (contador unread), `(created_at DESC)`.
**Delete:** CASCADE recipient (cesta de cada usuario), SET NULL actor.

## 2.26 — `notification_settings`
| `id` PK · `user_id` UUID UNIQUE FK CASCADE · `email_digest_enabled` BOOL · `in_app_master` BOOL · `exceptions` JSONB (map tipo→canal activado/desactivado) |
**JSONB exceptiones** evita 15 columnas booleanas: `{"follow": {"in_app":true,"email":false}, ...}` (validado en schema).

## 2.27 — `push_queue` (técnica)
| `id` PK · `user_id` UUID FK CASCADE · `channel` enum (PUSH/EMAIL) · `payload` JSONB · `status` enum (PENDING/SENT/FAILED/CANCELLED) · `attempts` INT · `next_attempt_at` timestamptz · `created_at` · `sent_at` |
**Índice:** `(status, next_attempt_at)`.

## 2.28 — Cambios al esquema EXISTENTE
- `books`: add `rating_avg NUMERIC(3,2)` NULL, `rating_count INT` NOT NULL DEFAULT 0, `review_count INT` NOT NULL DEFAULT 0. Actualizado en transacción por eventos `rating_changed`/`review_changed` (**ADR-9**). Migración additive, no destructiva.
- `books`: **no** añadir autores aún (ADR-3).
- `users`: **sin cambios** (Profile cubre lo público).

**Diagrama FK textual:**
```
users 1──1 profiles ; 1──N preferences/privacy/reading_goals
users 1──N user_books ──N books ; user_books ◄──(owned) rating/reading_progress
users 1──N shelves ◄──N shelf_items ──N books
users 1──N ratings ──N books ; 1──N reviews ◄──N review_likes ; ratings 1:0..1 review
users 1──N follows / blocks / mutes (self-N:N)
users 1──N posts ◄──N post_media ; 1──N comments ◄─N comment_likes ; 1──N post_likes
users 1──N reports ; 1──N activities ; 1──N mentions
users 1──N lists ◄──N list_items ──N books ; ◄──N list_collaborators
users 1──N notifications ◄──N notification_settings ; 1──N push_queue
```
---

# FASE 3 — Estructura del proyecto

## 3.1 Patrón de módulo (igual a `app/auth/`)

Cada contexto es un paquete autocontenido. Las tablas **DEBEN importarse en `app/models/__init__.py`** (o los módulos se importan ahí) porque `alembic/env.py` hace `from app import models` (FASE: registro de modelos).

```
app/<modulo>/
  __init__.py
  models.py        # SQLModel table models
  schemas.py       # pydantic create/update/response
  repository.py    # persistencia (AsyncSession), sin lógica
  service.py       # lógica de dominio + eventos
  router.py        # endpoints finos
  dependencies.py  # DI: repos/servicio + reutiliza get_current_user
  exceptions.py    # DomainError(status_code, code) con jerarquía
  events.py        # emisores de eventos de dominio
```

## 3.2 Módulos propuestos

```
app/
├── core/                # EXISTE: config, db, deps
│   ├── events.py        # NUEVO: bus de eventos in-process (async)
│   └── pagination.py    # NUEVO: cursor pagination (opaque key) + util de filtros de visib.
├── auth/                # EXISTE (User, roles, DI get_current_user) — sin cambios
├── books_tag/           # EXISTE (catálogo) + se añade contadores-denormal
├── profiles/            # NUEVO
├── shelves/             # NUEVO (user_book, shelf, shelf_item, reading_progress)
├── reviews/             # NUEVO (rating, review, review_likes)
├── social/              # NUEVO (follow, block, mute, report, activity)
├── posts/               # NUEVO (post, media, comment, like, mention)
├── lists/               # NUEVO
├── feed/                # NUEVO (read-models: timeline, ranking, feed_generator)
├── notifications/       # NUEVO
└── search/              # NUEVO (search_users/books/posts queries)
```

### Registro de modelos (imprescindible)
`app/models/__init__.py` (o `app/models.py`) debe importar los tablas de los nuevos módulos para que `SQLModel.metadata` y Alembic las vean:
```python
from app.profiles.models import Profile, ProfilePreference, PrivacySetting, ReadingGoal
from app.shelves.models import UserBook, Shelf, ShelfItem, ReadingProgress
from app.reviews.models import Rating, Review, ReviewLike
from app.social.models import Follow, Block, Mute, Report, Activity
from app.posts.models import Post, PostMedia, Comment, PostLike, CommentLike, Mention
from app.lists.models import List, ListItem, ListCollaborator
from app.notifications.models import Notification, NotificationSettings, PushNotification
```

## 3.3 Infraestructura compartida (base de módulos)

**`core/events.py` — bus in-process (ADR-7):**
- `emit(event)` tras `COMMIT` del servicio.
- `Handlers` registrados: `subscribies en module.dependencies` (ej. notificaciones en `reviews`, `social`, `posts`, `lists`; `statistics` el `books`).
- Event list (de dominio): `ProfileCreated`, `UserBookStatusChanged`, `RatingCreated`, `ReviewCreated`, `ReviewUpdated`, `ReviewDeleted`, `FollowCreated`, `BlockCreated`, `MuteCreated`, `PostCreated`, `CommentCreated`, `MentionDetected`, `ListCreated`, `PostLiked`, `CommentLiked`, `ReviewLiked`, `ReadingGoalProgressed`.

**`core/pagination.py`:** cursor base64 `(created_at, id)` → solo before-based; response `{"next": cursor, "items": []}`.

**`core/visibility.py` — `VisibilityService` (ADR-4):** dado `viewer_id` (o anónimo) + `author` devolver la lista de contenidos visibles aplicando `privacy_settings.author` + si está blockeado/mutado + `author.deleted_at IS NULL`. Una sola función `visible_ids(viewer, columns)` usada por todos los feeds/depts.

**`core/deps.py`:** ya existe `get_db`. Los módulos usan `get_current_user` desde `app.auth.dependencies` (no se duplica auth logic).

## 3.4 Integración con el código existente
- `app/router/router.py` (o `app/main.py`): incluye los routers de los módulos con prefijos: `/profiles`, `/shelves`, `/reviews`, `/social`, `/posts`, `/lists`, `/feed`, `/notifications`, `/search`.
- Los **contadores denormalizados** de `books` se actualizan desde handlers de eventos en `app/models/book.py` (helper) o un `app/reviews/services` → no se meten dentro de `crud/book_repository` para no acoplar.
- Las `exceptions` nuevas cogen el mismo patrón que `AuthError`; registrar un handler base en `main.py` para `DomainError` (no solo `AuthError`).

---

# FASE 4 — Roadmap (orden óptimo min refactors)

> Principio: se construyee **la infraestructura** una vez (events, pagination, visibility), luego los context con menos dependencias, y el feed/notificaciones se apoyan en el sistema de **eventos/activity** ya existente. **El feed NO va primero**; va después de tener contenido (library+reviews+social+posts) y de la infra de activity.

| Fase | Nombre | Depende de | Contenido principal |
|---|---|---|---|
| **F0** | Infraestructura compartida | — | events bus, cursor pagination, VisibilityService, DomainError, registro de modelos |
| **F1** | Profiles | F0, auth | Profile/Preferences/Privacy/Goals + backfill + API pública de perfiles |
| **F2** | Library (Shelves) | F1, catálogo | UserBook/Shelf/ShelfItem/ReadingProgress |
| **F3** | Reviews & Ratings | F1, F2 | Rating/Review/ReviewLike + denormalización en books |
| **F4** | Social Graph | F1 | Follow/Block/Mute/Report + **Activity** (log stream) |
| **F5** | Feed v1 (read-model) | F0, F2, F4 (activity) | Timeline = activity de follows + library + visibility |
| **F6** | Posts & Engagement | F4 (activity), F1 | Post/Media/Comment/Like/Mention (+activity) |
| **F7** | Lists & Collaborators | F1, feed | List/ListItem/Collaborator |
| **F8** | Notifications | F4/F6 (events) | Notification/Settings/PushQueue |
| **F9** | Reading stats, goals & retos | F2/F3 | dashboards, goals, retos anuales |
| **F10** | Search social | F0, búsqueda existente | search users/books/posts |
| **F11** | Recommendations | F3 (ratings/reviews) | feed de recomendaciones |

**Por qué este orden:**
1. **F0** desbloquea escalabilidad: pagination+visibility+eventos se usan en todas partes.
2. **F1 (Profiles)** primero porque **todo** el resto muestra autor+visibilidad (feed, reviews, posts, notifs). Es la base de la "pizarra pública".
3. **F2 (Shelf)** es el núcleo Goodreads y depende solo de catálogo (exist). Reviews (F3) lo aprovechan funcional cuando el usuario deja el libro.
4. **F4** aporta las relaciones y sobre todo **Activity** (el stream de dónde nace el feed). Cerca de F5 sin posts.
5. **F6 (Posts)** después de activity: introduce "contenido propio" que el feed ya proyecta (fase v2 del feed).
6. **F7/F8** dependen de que existan eventos de el módulo anterior → se posponen hasta que las fuentes (reviews/posts/follow) generan eventos.
7. Los **Stats/Retos/Recomendación** buscan aprovechar los datos acumulado (F2..F3) → al final.

---

# FASE 5 — Detalle por fase

## FASE 0 · Infraestructura compartida
Estado: no público, refactor puro.
- **Dependencias:** ninguna nueva. Usa `appcore/auth` existente.
- **Migraciones:** ninguna (no tablas).
- **Endpoints:** ninguno.
- **Tests:**
  - `test_pagination.py` (cursor inválido, límites, before, edad).
  - `test_visibility.py` (privado car vs seguidor vs anónimo; bloqueado arroja oculto; mute).
  - `test_events.py` (handlers registrados se invocan en orden en 1 commit; idempotencia).
  - `test_domain_error.py` (status_code/code/payload).

## Fase 1 · Profiles
- **Dependencias:** F0, auth (`get_current_user`, `User`).
- **Migraciones:** `profiles`, `profile_preferences`, `privacy_settings`, `reading_goals` + **backfill** de `profiles` para usuarios existentes (INSERT 1:1 from users) y seed 3 estanterías? (deja default en F2). En Alembic: data migration o script en `seed`.
- **Endpoints:**
  - `GET /profiles/{handle}` → perfil público (privacy-aware) con mini-stats
  - `GET/PATCH /profiles/me` → mi propio perfil (edit bio/avatar/location/website)
  - `GET/PATCH /profiles/me/privacy` → privacy_settings
  - `GET/PATCH /profiles/me/preferences`
  - `POST/GET/DELETE /profiles/me/goals/{year}` (goal anual de libros)
- **Tests:** `test_profiles_*` (GET público vie protected; PATCH me; privacidad (book PRIVATE oculta); backfill idempotente; goal único por año).

## Fase 2 · Shelves (Library)
- **Dependencias:** F1 (para URL de autor del libro), catálogo existente (Book).
- **Migraciones:** `shelves`, `user_books`, `shelf_items`, `reading_progress`.
- **Endpoints:**
  - `POST /shelves` · `GET /shelves` (mia) · `PATCH/DELETE /shelves/{id}`
  - `POST /me/library/{book_id}` (crea sujar) o `PATCH /me/library/{book_id}` (crop status)
  - `GET /me/library` ; `GET /users/{handle}/library?status=`
  - `GET/PUT/DELETE /shelves/{id}/books` (books en una CUSTOM shelf)
  - `PATCH /me/library/{book_id}/progress` (update reading_progress + progress log)
  - `GET /me/library/{book_id}` (detalle UserBook + progress)
- **Tests:** invariantes (unique user+book → 409); statustransition autoasigna fechas; shelf item solo CUSTOM; delete shelf reasigna; private shelf no expuesta a otros; progreso ≤ page_count.

## Fase 3 · Reviews & Ratings
- **Dependencias:** F2 (UserBook) opcional, F0, books (Book).
- **Migraciones:** `ratings`, `reviews`, `review_likes` + **colisiones denormalizadas** en `books` (rating_avg/rating_count/review_count) + recálculo backfill existe.
- **Endpoints:**
  - `POST/GET/PATCH/DELETE /reviews/{book_id}` (con rating) → crea Rating/Review (+ event `rating_changed` → books)
  - `GET /books/{id}/reviews?page=` ; `GET /users/{handle}/reviews`
  - `POST /reviews/{id}/like` · `DELETE ...` (ReviewLike)
  - `GET /reviews/{id}` público; `GET /me/reviews`
- **Tests:** única review activa por user+book; re-review tras soft-delete; rating bounds; like unique; counters books se actualizan; privacidad de reviews.

## Fase 4 · Social Graph
- **Dependencias:** F1.
- **Migraciones:** `follows`, `blocks`, `mutes`, `reports`, `activities`.
- **Endpoints:**
  - `POST/DELETE /users/{id}/follow` · `GET /users/{id}/followers` · `GET /users/{id}/following` ; `GET /users/{id}/is-following`
  - `POST/DELETE /users/{id}/block` · `/mute`
  - `POST /reports` (target_type/target_id)
  - `GET /users/{handle}/activity?after=` (stream público)
- **Tests:** no auto-follow; block borra follow (dos lados) e inhabilita contenido; unique follow; actividades append-only con visibilidad; pagination.

## Fase 5 · Feed v1 (read-model)
- **Dependencias:** F0, F4 (activity), usuarios comes.
- **Migraciones:** ninguna tablas de negocio (solo posiblemente un índice en `activity`). 
- **Endpoints:**
  - `GET /feed` (timeline propia: activity de followed + propia, filtrado por visibility/block/mute, cursor) 
- **Tests:** feed respeta `privacy.activity_visibility`; excluye blocked; mutaet; cursor estable; `{feed}` con activity vacía ok; paginación cursor.

## Fase 6 · Posts & Engagement
- **Dependencias:** F4 (activity), F1, F0.
- **Migraciones:** `posts`, `post_media`, `comments`, `post_likes`, `comment_likes`, `mentions`.
- **Endpoints:**
  - `POST/GET/PATCH/DELETE /posts` (+ media) · `GET /users/{id}/posts`
  - `POST/GET/DELETE /posts/{id}/comments` (nested 1 nivel)
  - `POST/DELETE /posts/{id}/like` · `/comments/{id}/like`
  - Mención en Post/Comment cuerpo → `mentions`.
- **Feed v2:** incluye posts de followed y menores en el mismo timeline (`POST` verb en activity). Se re-añade una query.
- **Tests:** autores; solo nivel de anidado; unique likes; mención genera actividad/notify (event); post soft delete; book POST RESTRICT.

## Fase 7 · Lists & Collaborator
- **Dependencias:** F1, catálogo, F0.
- **Migraciones:** `lists`, `list_items`, `list_collaborators`.
- **Endpoints:**
  - `POST/GET/PATCH/DELETE /lists` · `GET /lists/{id}`
  - `POST /lists/{id}/items` (`book_id`) · `DELETE /lists/{id}/items/{book_id}` · `GET /lists/{id}/items`
  - `POST/PATCH/DELETE /lists/{id}/collaborators` (invitation por owner)
- **Activity: list_created.** Tests: perm de editor/viewer; único item; soft delete con re-curar; colaboraciones de owner.

## Fase 8 · Notificaciones
- **Dependencies:** F4 (events), F4 (events), F6 (events), F4 (Activity) , settings.
- **Migraciones:** `notifications`, `notification_settings`, `push_queue`.
- **Endpoints:**
  - `GET /notifications` (cursor + unread_count) · `POST /notifications/read` (all) · `PATCH /notifications/{id}/read`
  - `GET/PATCH /notifications/settings`
  - (técnica) `push_queue` worker.
- **Eventos atendidos:** follow (notif al seguido), review_like (al autor), comment (al autor del post), mention (al nombrado), like post/comentario.
- **Tests:** solo si el setting lo permite; mark read; unread_count; actor anónimo si se borra.

## Fase 9 · Stats y Retos de lectura
- **Dependencias:** F2..F5 (datos).
- **Migresiones:** `reading_goals` usados en F1 (maybe ya) + opcional vista/matview `reading_stats`.
- **Endpoints:**
  - `GET /users/{handle}/stats?year=` (libros leídos, páginas, avg de rating,  mejor género, racha, etc.)
  - `GET/POST /users/{id}/goals/{year}` (ya en F1) + `POST /goals/{year}/progress` updates.
  - Retos: `POST /users/{id}/challenges` ... (definir en backlog, no MVP inicial)
- **Tests:** estadísticas derivadas de user_books+reviews; año límite; vacío.

## Fase 10 · Búsqueda social
- **Dependencias:** F0, catálogo (books), perfiles, posts.
- **Migración base:** índices `pg_trgm` GIN sobre `users.username`/`profiles.display_name`, FTS posts body.
- **Endpoints:**
  - `GET /search/users?q=` · `GET /search/books?q=` (mezcla), `GET /search/posts?q=`
- **Tests:** ranking, filtros de visibilidad (no devuelve privados), tildes (normalización), límites, timeout.

## Fase 11 · Recomendaciones
- **Dependencias:** F3 (ratings/reviews), F0.
- **Migraciones:** ninguna (derivado) o tablas `ranking` opcional; no bloquear.
- **Endpoints:** `GET /recommendations`, `GET /feed/popular`.
- **Tests:** datos fríos (author-based collaborative) y sanity.

---

# Defininy de enums (Value Objects centrales)
- `visibility`: PUBLIC | FOLLOWERS | PRIVATE
- `reading_status`: WANT_TO_READ | READING | READ | DNF
- `shelf_kind`: STATUS | CUSTOM
- `score`: 1..5 (SMALLINT)
- `report_target`: USER | POST | COMMENT | REVIEW | LIST
- `report_status`: OPEN | REVIEWING | RESOLVED | DISMISSED
- `activity_verb`: SHELF_UPDATED | RATING_ADDED | REVIEW_ADDED | FOLLOWED | POST | COMMENTED | LIST_CREATED | GOAL_UPDATED | JOINED
- `object_type`: POST | COMMENT | REVIEW | RATING | BOOK | GOAL | USER_BOOK
- `post_type`: TEXT | BOOK_SHARE | MEDIA
- `visibility` (posts): PUBLIC | FOLLOWERS
- `notify_type`: FOLLOW | REVIEW_LIKE | COMMENT | MENTION | POST_LIKE | POST_ON_BOOK | GOAL | SYSTEM
- `collaborator_role`: EDITOR | VIEWER
- `channel`: INBOX | EMAIL | PUSH

---
# Checklist de aprobación
- [ ] Bounded contexts y agregados correctamente delimitados
- [ ] Ownership e invariantes claras
- [ ] Modelo SQL sin ambigüedades (FK/unique/delete/enums)
- [ ] Estructura de módulos coherente con `app/auth/`
- [ ] Orden de roadmap minimiza refactors
- [ ] Aprobado → se implementa módulo por módulo (comenzando F0)