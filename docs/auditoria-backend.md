# Auditoría del backend BookDealers

Revisión técnica tipo **Senior Engineer** sobre el monobloque FastAPI + SQLModel.
Fecha: 2026-08-06. Alcance: seguridad/visibilidad, cobertura de tests, rendimiento
(N+1/índices/read-models), bugs/carreras, DDD/SOLID, y redundancia/limpieza.

Suite: **191 tests pasando** (Postgres dedicado de test, `conftest` con `TRUNCATE`).
El diagnóstico no rompe catálogo ni auth: los cambios propuestos tocan capas de
visibilidad/reviews/social, nunca `books` ni los flujos de token.

---

## 1. Resumen ejecutivo

La arquitectura es sólida: agregados claros por contexto, repositorios finos,
eventos de dominio desacoplados (bus en memoria, ADR-7), handlers de contadores
con `_session_factory` inyectable, y un `is_visible()` puro que evita acoplamiento
circular. Auth está bien hecho (rotación de refresh con detección de replay,
lockout de login, verificación de email, respuestas genéricas anti-enumeración).

Sin embargo, la visibilidad está implementada de forma **inconsistente entre
módulos**: los módulos más nuevos (posts, lists, social, stats, feed) la aplican
correctamente, pero **profiles, shelves y reviews hardcodean `is_follower=False`
e `is_blocked=False`**, lo que produce dos defectos de seguridad reales:

1. **Fuga de reviews PRIVATE/FOLLOWERS** en `GET /books/{id}/reviews` (P1).
2. **Bloqueos no aplicados** y **tier FOLLOWERS roto** en lecturas públicas de
   perfil, biblioteca y reviews (P1/P2).

Hallazgos por severidad:

| Severidad | Cantidad |
|---|---|
| Crítico (P1) | 2 |
| Alto (P2) | 5 |
| Medio (P3) | 6 |
| Bajo / limpieza | 8 |

---

## 2. Seguridad, visibilidad e IDOR/BOLA

### P1-1. Fuga de reviews PRIVATE/FOLLOWERS en la lista de un libro

- **Dónde:** `app/reviews/service.py:163-172` (`list_book_reviews`) →
  `app/reviews/repository.py:102-115` (`list_active_reviews_by_book`) →
  `_paginate`/`_responses` (`app/reviews/service.py:265-332`).
- **Problema:** el listado de reviews de un libro no filtra por
  `privacy_settings.reviews_visibility` del autor de cada review. Devuelve todas
  las reviews activas del libro a cualquiera (incluso anónimo), incluidas las de
  usuarios con `reviews_visibility = PRIVATE` o `FOLLOWERS`. Tampoco aplica
  bloqueos (una review de un usuario que bloqueó al espectador sigue visible).
- **Impacto:** violación directa de ADR-4. Un usuario que marca sus reviews como
  privadas las expone sin querer en la página del libro.
- **Solución (recomendada):** añadir columna `visibility` con snapshot en `reviews`
  (mismo patrón que `activities`, ADR-4) + backfill desde `privacy_settings` +
  filtrado en `list_active_reviews_by_book`. Alternativa sin migración: JOIN a
  `privacy_settings` y `is_visible()` por review en el servicio, resolviendo
  follower/block en batch.

### P1-2. `is_follower=False` / `is_blocked=False` hardcodeados en lecturas públicas

- **Dónde:**
  - `app/profiles/service.py:101-111` (`get_public`).
  - `app/shelves/service.py:391-411` (`list_public_library`).
  - `app/reviews/service.py:174-197` (`list_user_reviews`) y `241-263`
    (`_visible_review`).
- **Problema A (FOLLOWERS roto):** un seguidor real de un usuario con
  `profile_visibility`/`library_visibility`/`reviews_visibility = FOLLOWERS`
  recibe 403: nunca se consulta `follows`. La funcionalidad "solo seguidores"
  queda inutilizable salvo para el propio autor.
- **Problema B (bloqueo no aplicado):** un usuario bloqueado (o que bloquea) sigue
  viendo el contenido público del otro. ADR-4 dice que el bloqueo oculta el
  contenido del bloqueado; en perfiles/biblioteca/reviews no se cumple.
- **Contraste:** `app/stats/service.py:110-136` lo hace bien (resuelve follower y
  block antes de `is_visible`). Posts (`app/posts/service.py:337-371`) y lists
  (`app/lists/service.py:347-383`) también. **El patrón correcto ya existe; hay que
  replicarlo.**
- **Solución:** extraer un helper compartido
  `async def viewer_relation(db, viewer, author) -> (is_follower, is_blocked)` y
  usarlo en profiles/shelves/reviews, en vez de reimplementar las consultas.

### P2-1. `block_anonymous` solo se respeta en búsqueda

- `app/search/service.py:76` lo cumple; `profiles.get_public`, `shelves
  .list_public_library`, `reviews.*` y `stats` no. Un usuario que activa
  `block_anonymous` sigue expuesto a anónimos en esos endpoints.

### P2-2. `show_reading_progress` nunca se aplica

- `app/shelves/service.py:413-419` (`_user_book_response`) expone `current_page`,
  `percent_read`, `started_at`, `finished_at` en la biblioteca pública. El flag
  `privacy.show_reading_progress` (modelado en `app/profiles/models.py:141`) solo
  se devuelve en `/me/privacy`; no se lee en ninguna parte. Progreso de lectura
  expuesto contra la preferencia del usuario.

### P3-1. Lists de followers/following visibles a anónimos

- `app/social/service.py:242-245` (`_can_view_relations`): devuelve `True` si
  `viewer is None`. Quién sigue a quién queda expuesto sin autenticación y sin
  respetar la privacidad de la lista. Es información pública en redes sociales
  tipo Goodreads, pero conviene gatearla con `profile_visibility` si el producto
  decide ocultarla.

### P3-2. Notificaciones de usuarios bloqueados/muteados

- `app/notifications/handlers.py`: no consulta `blocks`/`mutes`. Tras bloquear a
  alguien, ese actor sigue pudiendo generar notificaciones al bloqueador
  (p. ej. like a un post). Falta un `get_block_relation` antes de `_delivery`.

### P3-3. `spoiler` no oculta el body

- `app/reviews/schemas.py`/`ReviewResponse` devuelve `body` completo aunque
  `spoiler=True`. Si el producto quiere ocultar spoilers, falta lógica de
  revelado.

### Nota positiva: IDOR/BOLA en escrituras

- Todos los writes están bien acotados por el usuario autenticado:
  - Posts: `post.author_id != user.id → PostForbiddenError` (`posts/service.py:138`).
  - Comments: autor del comentario **o** autor del post (`posts/service.py:276-279`).
  - Reviews: siempre por `(user.id, book_id)` (`reviews/service.py:106,134`).
  - Lists: owner para gestión, `_require_editor` para items (`lists/service.py:385-392`).
  - Notifications: `mark_read` valida `recipient_id` (`notifications/service.py:71-76`).
  - Shelves: `_own_shelf` (`shelves/service.py:161-165`).

---

## 3. Cobertura de tests

**Puntos fuertes:** auth completo (registro anti-enumeración, refresh con replay,
logout everywhere, lockout), migraciones con drift-check, paginación por cursor,
feed, social (blocks, mutes, visibilidad de actividad), posts, lists (colaboradores),
stats, search, recommendations y notificaciones. Tests contra Postgres real
dedicado (`conftest.py`).

**Huecos que ocultan exactamente los bugs de la sección 2:**

| # | Test que falta | Bug que detectaría |
|---|---|---|
| 1 | `GET /books/{id}/reviews` no debe devolver reviews PRIVATE/FOLLOWERS de terceros (ni anónimo ni logueado). | P1-1 |
| 2 | Un seguidor debe poder ver perfil/biblioteca/reviews con visibilidad FOLLOWERS. | P1-2A |
| 3 | Un usuario bloqueado no debe ver el perfil/biblioteca/reviews públicos del bloqueador (y viceversa). | P1-2B |
| 4 | `block_anonymous=True` oculta contenido a anónimos en perfiles/biblioteca/reviews/stats. | P2-1 |
| 5 | `show_reading_progress=False` no devuelve progreso en biblioteca pública. | P2-2 |
| 6 | Like doble concurrente → 409/204, nunca 500 (IntegrityError). | Carreras (sec. 4) |
| 7 | Creación concurrente de `UserBook` → idempotente (upsert), no 500. | Carreras (sec. 4) |
| 8 | Bloqueo/mute no genera notificación al actor. | P3-2 |
| 9 | `default_review_visibility` y `shelf.is_private` sin efecto real (regresión si se eliminan). | Limpieza (sec. 6) |
| 10 | Transición de estados de UserBook hacia atrás (READ → WANT_TO_READ) limpia fechas. | `_apply_status_dates` (`shelves/service.py:72-79`) |

El test existente `test_private_reviews_visibility` (`tests/test_reviews.py:253`)
solo cubre detalle y `/users/{handle}/reviews`, no la lista por libro — por eso la
fuga pasó desapercibida.

---

## 4. Rendimiento: N+1, índices y read-models

### P3-4. N+1 en `list_shelves`

- `app/shelves/service.py:148-159`: un `COUNT` por estantería
  (`count_by_status`/`count_items`). Con las 3 de estado + N custom → N+1.
  Sustituir por un `GROUP BY` en batch (mismo patrón que
  `count_items_by_list_ids` en `lists/repository.py:245-256`).

### P3-5. Feed: pull-on-read con `IN` gigante

- `app/feed/repository.py:54-66`: `actor_id.in_(pool)` (miles de UUIDs) + OR de
  visibilidad + `ORDER BY created_at DESC`. `ix_activities_actor_created` ayuda
  por actor, pero el OR obliga a Bitmap Heap Scan y un `IN` con miles de valores
  degrada el planificador. Correcto para monobloque (ADR-7), pero es el cuello de
  botella nº1 a medio plazo. Opciones: fan-out (timeline materializada por
  seguidor) o al menos batching del `IN` y `ANY(:ids)`.

### P3-6. Índice de paginación de notificaciones

- El cursor mezcla leídos/no leídos ordenando por `(recipient_id, created_at DESC)`.
  El índice parcial `ix_notifications_recipient_unread` solo cubre no-leídos
  (`notifications/models.py:52-57`); el compuesto `(recipient_id, read_at)` no
  ordena por `created_at`. Añadir `(recipient_id, created_at DESC)` completo para
  la paginación mixta.

### P3-7. `mark_all_read` carga todos los no-leídos

- `app/notifications/repository.py:58-66`: materializa toda la fila no leída en
  Python. Funcional, pero un `UPDATE ... WHERE read_at IS NULL` con retorno de
  count sería una sola query.

### P3-8. Contadores de libros recomputados por evento

- `app/reviews/counters.py:34-58`: cada `rating_changed` recalcula `COUNT+AVG` de
  **todos** los ratings del libro. Idempotente y correcto, pero O(n) por evento.
  A escala, deltas incrementales o recomputo en batch con cola.

### Índices ya correctos

- `user_books (user_id, status)` (`ix_user_books_user_status`) cubre el filtro de
  librería por estado.
- `reviews (book_id, created_at DESC)` y parcial único activo `(user_id, book_id)`
  para re-review.
- `activities (actor_id, created_at DESC)` + parcial público.
- `pg_trgm`/`unaccent` + GIN en search/recommendations (migración
  `2026_08_06_1200-f6a7b8c9d0e1`).
- Read-model de stats sin tablas, derivado — OK en monobloque.

---

## 5. Bugs y carreras de consistencia

### P2-3. Likes concurrentes → 500

- `app/posts/service.py:287-301` (`like_post`), `311-325` (`like_comment`) y
  `app/reviews/service.py:210-229` (`like_review`): hay UNIQUE
  (`uq_post_likes...`/`uq_review_likes_user_review`), el check es
  get→create→commit **sin capturar IntegrityError**. Un doble-tap concurrente
  lanza 500. `create_review` sí lo captura (`reviews/service.py:92-96`); replicar
  ese patrón (rollback + respuesta idempotente/409).

### P2-4. Creación concurrente de `UserBook` → 500

- `app/shelves/service.py:283-307` (`update_or_create_user_book`): get → create →
  commit sin `IntegrityError` ni upsert, pese a existir `uq_user_books_user_book`.
  Usar `INSERT ... ON CONFLICT (user_id, book_id) DO UPDATE` o capturar el error.

### P3-9. Posición de items de lista no atómica

- `app/lists/service.py:201-232` (`add_item`) con `get_next_position`
  (`lists/repository.py:111-114`): dos adds concurrentes pueden asignar la misma
  posición (no hay UNIQUE que lo impida). Bajo impacto, pero es una carrera real.

### P3-10. `update_review` muta el dict del llamador

- `app/reviews/service.py:111`: `fields.pop("score", None)` muta el diccionario
  pasado por el router. Funcional hoy, pero frágil si el llamador lo reutiliza.

### P3-11. Snapshot de visibilidad en actividad vs. visibilidad viva del post

- La actividad `POST` se crea con `activity_visibility` del actor
  (`posts/service.py:113-120`); el post guarda su propia `visibility`. Si el autor
  edita el post a PRIVATE→PUBLIC, la actividad (que gobierna el feed) no se
  actualiza. Coherente con ADR-4 (snapshot), pero es un desfase UX que conviene
  documentar o sincronizar en `update_post`.

---

## 6. DDD / SOLID

### Fortalezas

- Agregados bien elegidos: `UserBook`/`Shelf`/`ReadingProgress`,
  `Review`+`Rating`+`ReviewLike`, `List`+`ListItem`+`ListCollaborator`,
  `Post`+`Comment`+`Mention`, `Activity`, `Notification`.
- Repositorios sin lógica de negocio; servicios sin SQL crudo salvo excepciones
  puntuales y acotadas (línea de colaboradores en `lists/service.py:163-168`).
- Eventos de dominio desacoplados: los handlers de contadores y notificaciones
  corren en su propia sesión con `_session_factory` inyectable
  (`reviews/counters.py`, `notifications/handlers.py`) → tests reales sin acoplar.
- Polimorfismo sin FK (`reports.target_type/target_id`, `activities.object_*`,
  `notifications.object_*`) es una decisión pragmática y documentada.

### Debilidades

- **Duplicación de consultas sociales:** `get_block_relation`/`get_follow` están
  reimplementadas en `lists/repository.py:216-233`, `posts/repository.py:286-301`,
  `stats/repository.py` y `social/repository.py`. Consolidar en un repositorio
  compartido o un helper `viewer_relation(db, viewer, author)`.
- **`_activity_visibility` duplicada:** `posts/service.py:421-428`,
  `lists/service.py:403-410` y `social/service.py:72-77`. Extraer a un helper.
- **Capas rotas puntualmente:** `ProfileService._is_following`
  (`profiles/service.py:116-125`) consulta la sesión directamente en vez del repo.
- **`target_type` es `String(30)` libre** (`social/models.py:188-190`) mientras
  `object_type` es enum: valores a mano ("USER", "POST", "LIST") propensos a typo.
  Un enum de targets válidos lo elimina.
- **Dos taxonomías casi iguales:** `ObjectType` (actividad/notificaciones) vs
  `ReportTarget` (reportes). Unificar o documentar la frontera.
- **Verbos sin uso:** `ObjectType.RATING/BOOK/GOAL/USER_BOOK` no tienen verbos que
  los publiquen (solo POST/COMMENT hoy). Futuro OK, pero indica actividad parcial.

---

## 7. Redundancia y limpieza

- `ProfilePreference.default_review_visibility` (`profiles/models.py:85`) solo se
  devuelve en `/me/preferences`; la visibilidad real la manda
  `PrivacySetting.reviews_visibility`. Dos fuentes de verdad → eliminar una.
- `Shelf.is_private` (`shelves/models.py:77`) se setea y se devuelve, pero ningún
  endpoint lo lee para autorizar (no hay vista pública de estanterías custom).
  Campo muerto o falta su enforcement.
- `privacy.show_reading_progress` sin enforcement (ver P2-2).
- **`app/clients/` vs `app/adapters/`:** ambas capas exponen las mismas
  integraciones (availability/search base + z3950, ebiblio, todostuslibros,
  google, open_library). Consolidar; verificar qué rama es código vivo.
- **`app/crud/`, `app/tasks/`, `app/services/`:** capa de catálogo anterior,
  solapada con los nuevos repos. Auditar imports y eliminar código muerto
  (ya hubo un commit "eliminados imports muertos").
- `scripts/make_data.py` es solo dev — mantener pero no documentar como API.
- `app/models` como paraguas de SQLModel: aceptable.

---

## 8. Plan de tests ampliado (prioridad)

1. **Regresión P1-1 (crítico):** review PRIVATE/FOLLOWERS de un usuario no aparece
   en `GET /books/{id}/reviews` para anónimo ni para otros usuarios.
2. **FOLLOWERS tier:** seguidor ve perfil/biblioteca/reviews FOLLOWERS; no
   seguidor no.
3. **Bloqueo en lecturas:** bloqueado no ve perfil/biblioteca/reviews públicos del
   bloqueador (y viceversa).
4. **Concurrencia:** doble like (post/comment/review) y doble creación de
   UserBook → idempotente/409, no 500.
5. **Privacidad:** `block_anonymous` y `show_reading_progress` en perfiles,
   biblioteca, reviews y stats.
6. **Notificaciones:** sin notificación desde usuarios bloqueados/muteados.
7. **Estados:** transiciones UserBook hacia atrás limpian fechas; progreso no
   sobrepasa `page_count`.

---

## 9. Refactors sugeridos (sin tocar catálogo ni auth)

1. **P1-1:** columna `visibility` snapshot en `reviews` + migración de backfill +
   filtrado en el listado por libro. (El único cambio de esquema propuesto; no
   toca `books`.)
2. **P1-2:** helper compartido de relaciones `(is_follower, is_blocked)` aplicado
   en profiles/shelves/reviews replicando el patrón de stats/posts/lists.
3. **Carreras:** capturar `IntegrityError` con rollback en likes y `user_books`;
   upsert `ON CONFLICT`.
4. **N+1:** `GROUP BY` en `list_shelves`.
5. **Notificaciones:** filtrar por block/mute en `handlers.py`.
6. **Limpieza:** eliminar `default_review_visibility` y `shelf.is_private` (o
   implementarlos), consolidar `clients`/`adapters` y repos sociales.
7. **Índices:** `notifications (recipient_id, created_at DESC)`.

Ninguno de estos cambios altera `books`, el seed de catálogo, el flujo de
registro/login/refresh, ni la semántica de tokens.
