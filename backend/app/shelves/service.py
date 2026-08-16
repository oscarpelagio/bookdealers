"""Lógica de dominio del módulo shelves.

Reglas (documento FASE 1 §1.5):
- Estanterías de estado: seed de 4 (to-read / currently-reading / read /
  abandoned).
  Su contenido se deriva de `user_books.status` (ADR-5); `shelf_items`
  solo existe en estanterías CUSTOM.
- `user_books` es la relación usuario↔libro. Fechas autoasignadas al
  cambiar de estado. Progreso con historial en `reading_progress`.
"""

from __future__ import annotations

import re
import unicodedata
import uuid
from datetime import date

from sqlalchemy.exc import IntegrityError
from sqlmodel.ext.asyncio.session import AsyncSession

from app.core.events import event_bus
from app.core.visibility import is_visible
from app.enums import ReadingStatus, ShelfKind, Visibility
from app.models import Book
from app.profiles.exceptions import ProfileNotFoundError
from app.profiles.repository import ProfileRepository
from app.shelves import events
from app.shelves.exceptions import (
    BookNotFoundError,
    CannotModifyStatusShelfError,
    LibraryPrivateError,
    ProgressExceedsBookError,
    ProgressRequiredError,
    ShelfKindNotCustomError,
    ShelfNotFoundError,
    ShelfSlugConflictError,
    StatusRequiredError,
    UserBookNotFoundError,
)
from app.shelves.models import Shelf, UserBook
from app.shelves.repository import ShelfRepository
from app.shelves.schemas import (
    BookBrief,
    ReadingProgressResponse,
    ShelfResponse,
    UserBookResponse,
)

# (estado, nombre, slug, posición) de las estanterías de estado seedadas.
DEFAULT_SHELVES = (
    (ReadingStatus.WANT_TO_READ, "To Read", "to-read", 0),
    (ReadingStatus.READING, "Currently Reading", "currently-reading", 1),
    (ReadingStatus.READ, "Read", "read", 2),
    (ReadingStatus.DNF, "Abandoned", "abandoned", 3),
)

_POSITION_TO_STATUS = {
    0: ReadingStatus.WANT_TO_READ,
    1: ReadingStatus.READING,
    2: ReadingStatus.READ,
    3: ReadingStatus.DNF,
}


def make_slug(name: str) -> str:
    """Slug ASCII para estanterías (translitera acentos)."""
    normalized = (
        unicodedata.normalize("NFKD", name).encode("ascii", "ignore").decode("ascii")
    )
    slug = re.sub(r"[^a-zA-Z0-9]+", "-", normalized).strip("-").lower()
    return slug or "shelf"


def _apply_status_dates(status: ReadingStatus, started_at, finished_at):
    """Devuelve (started_at, finished_at) según la transición de estado."""
    today = date.today()
    if status == ReadingStatus.WANT_TO_READ:
        return None, None
    if status == ReadingStatus.READING:
        return (started_at or today), None
    return (started_at or today), (finished_at or today)


def _shelf_response(shelf: Shelf, book_count: int) -> ShelfResponse:
    return ShelfResponse(
        id=str(shelf.id),
        name=shelf.name,
        slug=shelf.slug,
        kind=shelf.kind,
        is_default=shelf.is_default,
        is_private=shelf.is_private,
        position=shelf.position,
        description=shelf.description,
        book_count=book_count,
    )


def _book_brief(book: Book) -> BookBrief:
    return BookBrief(
        id=book.id,
        title=book.title,
        author=book.author,
        thumbnail=book.thumbnail,
        page_count=book.page_count,
        language=book.language,
        price=float(book.price) if book.price is not None else None,
    )


def _user_book_response(
    ub: UserBook, book: Book, *, show_progress: bool = True
) -> UserBookResponse:
    return UserBookResponse(
        id=str(ub.id),
        book_id=ub.book_id,
        status=ub.status,
        current_page=ub.current_page if show_progress else None,
        percent_read=(
            float(ub.percent_read)
            if show_progress and ub.percent_read is not None
            else None
        ),
        started_at=ub.started_at,
        finished_at=ub.finished_at,
        notes=ub.notes,
        created_at=ub.created_at,
        updated_at=ub.updated_at,
        book=_book_brief(book),
    )


class ShelfService:
    def __init__(self, repo: ShelfRepository, db: AsyncSession) -> None:
        self.repo = repo
        self.db = db

    # ---------- Shelf ----------

    async def _ensure_default_shelves(self, user) -> None:
        existing = await self.repo.list_by_user(user.id)
        existing_slugs = {s.slug for s in existing}
        to_create = False
        for _status, name, slug, pos in DEFAULT_SHELVES:
            if slug not in existing_slugs:
                await self.repo.create_shelf(
                    user_id=user.id,
                    name=name,
                    slug=slug,
                    kind=ShelfKind.STATUS,
                    position=pos,
                    is_default=True,
                )
                to_create = True
        if to_create:
            await self.db.commit()

    async def list_shelves(self, user) -> list[ShelfResponse]:
        await self._ensure_default_shelves(user)
        shelves = await self.repo.list_by_user(user.id)
        status_counts = await self.repo.count_by_statuses(user.id)
        custom_ids = [s.id for s in shelves if s.kind != ShelfKind.STATUS]
        item_counts = await self.repo.count_items_by_shelf_ids(custom_ids)
        result: list[ShelfResponse] = []
        for s in shelves:
            if s.kind == ShelfKind.STATUS:
                status = _POSITION_TO_STATUS.get(s.position)
                count = status_counts.get(status, 0) if status else 0
            else:
                count = item_counts.get(s.id, 0)
            result.append(_shelf_response(s, count))
        return result

    async def _own_shelf(self, user_id: uuid.UUID, shelf_id: uuid.UUID) -> Shelf:
        shelf = await self.repo.get_by_id(shelf_id)
        if shelf is None or shelf.user_id != user_id:
            raise ShelfNotFoundError()
        return shelf

    async def create_shelf(
        self, user, *, name: str, description=None, is_private=False
    ) -> ShelfResponse:
        await self._ensure_default_shelves(user)
        shelves = await self.repo.list_by_user(user.id)
        custom = [s for s in shelves if s.kind == ShelfKind.CUSTOM]
        base = make_slug(name)
        taken = {s.slug for s in shelves}
        slug = base
        i = 2
        while slug in taken:
            slug = f"{base}-{i}"
            i += 1
        shelf = await self.repo.create_shelf(
            user_id=user.id,
            name=name,
            slug=slug,
            kind=ShelfKind.CUSTOM,
            position=(max((s.position for s in custom), default=-1) + 1),
            is_private=is_private,
            description=description,
        )
        try:
            await self.db.commit()
        except IntegrityError:
            await self.db.rollback()
            raise ShelfSlugConflictError()
        await self.db.refresh(shelf)
        await event_bus.publish(events.shelf_created(user.id, shelf.id))
        return _shelf_response(shelf, 0)

    async def update_shelf(
        self, user, shelf_id: uuid.UUID, *, fields: dict
    ) -> ShelfResponse:
        shelf = await self._own_shelf(user.id, shelf_id)
        if shelf.kind == ShelfKind.STATUS:
            if any(k in fields for k in ("name", "is_private", "position")):
                raise CannotModifyStatusShelfError()
            allowed = {"description": fields.get("description")}
        else:
            allowed = {k: v for k, v in fields.items() if v is not None}
            if "name" in allowed:
                allowed["slug"] = await self._unique_slug(
                    user.id, make_slug(allowed["name"]), exclude=shelf.id
                )
        shelf = await self.repo.update_shelf(shelf, fields=allowed)
        await self.db.commit()
        await self.db.refresh(shelf)
        if shelf.kind == ShelfKind.STATUS:
            status = _POSITION_TO_STATUS.get(shelf.position)
            count = await self.repo.count_by_status(user.id, status) if status else 0
        else:
            count = await self.repo.count_items(shelf.id)
        return _shelf_response(shelf, count)

    async def delete_shelf(self, user, shelf_id: uuid.UUID) -> None:
        shelf = await self._own_shelf(user.id, shelf_id)
        if shelf.kind == ShelfKind.STATUS:
            raise ShelfKindNotCustomError()
        await self.repo.delete_shelf(shelf)
        await self.db.commit()
        await event_bus.publish(events.shelf_deleted(user.id, shelf.id))

    async def _unique_slug(
        self, user_id: uuid.UUID, base: str, *, exclude: uuid.UUID
    ) -> str:
        shelves = await self.repo.list_by_user(user_id)
        taken = {s.slug for s in shelves if s.id != exclude}
        slug = base
        i = 2
        while slug in taken:
            slug = f"{base}-{i}"
            i += 1
        return slug

    # ---------- Custom shelf books ----------

    async def list_shelf_books(self, user, shelf_id: uuid.UUID) -> list[BookBrief]:
        shelf = await self._own_shelf(user.id, shelf_id)
        if shelf.kind == ShelfKind.STATUS:
            raise ShelfKindNotCustomError()
        ids = await self.repo.list_item_book_ids(shelf.id)
        books = await self.repo.get_books_by_ids(ids)
        return [books[i] for i in ids if i in books]

    async def add_book_to_shelf(
        self, user, shelf_id: uuid.UUID, book_id: int
    ) -> BookBrief:
        shelf = await self._own_shelf(user.id, shelf_id)
        if shelf.kind == ShelfKind.STATUS:
            raise ShelfKindNotCustomError()
        book = await self.repo.get_book(book_id)
        if book is None:
            raise BookNotFoundError()
        if await self.repo.get_item(user.id, shelf.id, book_id) is not None:
            return _book_brief(book)  # idempotente
        await self.repo.create_item(user.id, shelf.id, book_id)
        try:
            await self.db.commit()
        except IntegrityError:
            await self.db.rollback()
        return _book_brief(book)

    async def remove_book_from_shelf(
        self, user, shelf_id: uuid.UUID, book_id: int
    ) -> None:
        shelf = await self._own_shelf(user.id, shelf_id)
        if shelf.kind == ShelfKind.STATUS:
            raise ShelfKindNotCustomError()
        item = await self.repo.get_item(user.id, shelf.id, book_id)
        if item is not None:
            await self.repo.delete_item(item)
            await self.db.commit()

    # ---------- Library (user_books) ----------

    async def update_or_create_user_book(
        self, user, book_id: int, *, status=None, notes=None
    ) -> UserBookResponse:
        book = await self.repo.get_book(book_id)
        if book is None:
            raise BookNotFoundError()
        ub = await self.repo.get_user_book(user.id, book_id)
        if ub is None:
            if status is None:
                raise StatusRequiredError()
            started, finished = _apply_status_dates(status, None, None)
            created = await self.repo.create_user_book(
                user_id=user.id,
                book_id=book_id,
                status=status,
                started_at=started,
                finished_at=finished,
                notes=notes,
            )
            try:
                await self.db.commit()
            except IntegrityError:
                # Carrera: otro request creó el (user, book). Releer y seguir
                # con el update para no devolver 500.
                await self.db.rollback()
                ub = await self.repo.get_user_book(user.id, book_id)
                if ub is None:
                    raise
            else:
                await self.db.refresh(created)
                await event_bus.publish(
                    events.user_book_status_changed(user.id, book_id, status.value)
                )
                return _user_book_response(created, book)

        old = ub.status
        fields: dict = {}
        if status is not None:
            fields["status"] = status
            started, finished = _apply_status_dates(
                status, ub.started_at, ub.finished_at
            )
            fields["started_at"] = started
            fields["finished_at"] = finished
        if notes is not None:
            fields["notes"] = notes
        ub = await self.repo.update_user_book(ub, fields=fields)
        await self.db.commit()
        await self.db.refresh(ub)
        if status is not None and status != old:
            await event_bus.publish(
                events.user_book_status_changed(user.id, book_id, status.value)
            )
        return _user_book_response(ub, book)

    async def delete_user_book(self, user, book_id: int) -> None:
        ub = await self.repo.get_user_book(user.id, book_id)
        if ub is None:
            raise UserBookNotFoundError()
        await self.repo.delete_user_book(ub)
        await self.db.commit()
        await event_bus.publish(events.user_book_removed(user.id, book_id))

    async def get_user_book_detail(self, user, book_id: int) -> UserBookResponse:
        ub = await self.repo.get_user_book(user.id, book_id)
        if ub is None:
            raise UserBookNotFoundError()
        book = await self.repo.get_book(book_id)
        return _user_book_response(ub, book)

    async def update_progress(
        self, user, book_id: int, *, page=None, percent=None, note=None
    ) -> UserBookResponse:
        if page is None and percent is None:
            raise ProgressRequiredError()
        ub = await self.repo.get_user_book(user.id, book_id)
        if ub is None:
            raise UserBookNotFoundError()
        book = await self.repo.get_book(book_id)
        if page is not None and book.page_count is not None and page > book.page_count:
            raise ProgressExceedsBookError()
        fields: dict = {}
        if page is not None:
            fields["current_page"] = page
        if percent is not None:
            fields["percent_read"] = percent
        ub = await self.repo.update_user_book(ub, fields=fields)
        await self.repo.create_progress(ub.id, page=page, percent_read=percent, note=note)
        await self.db.commit()
        await self.db.refresh(ub)
        await event_bus.publish(
            events.reading_progress_updated(user.id, book_id, page=page, percent=percent)
        )
        return _user_book_response(ub, book)

    async def get_progress_history(
        self, user, book_id: int
    ) -> list[ReadingProgressResponse]:
        ub = await self.repo.get_user_book(user.id, book_id)
        if ub is None:
            raise UserBookNotFoundError()
        rows = await self.repo.list_progress(ub.id)
        return [
            ReadingProgressResponse(
                id=str(r.id),
                page=r.page,
                percent_read=float(r.percent_read) if r.percent_read is not None else None,
                note=r.note,
                created_at=r.created_at,
            )
            for r in rows
        ]

    async def list_my_library(self, user, status) -> list[UserBookResponse]:
        rows = await self.repo.list_user_books(user.id, status)
        return await self._responses(rows)

    async def list_public_library(
        self, handle: str, viewer, status
    ) -> list[UserBookResponse]:
        pr = ProfileRepository(self.db)
        target = await pr.get_user_by_handle(handle)
        if target is None:
            raise ProfileNotFoundError()
        privacy = await pr.get_privacy(target.id)
        section = privacy.library_visibility if privacy else Visibility.PUBLIC
        show_progress = privacy.show_reading_progress if privacy else True

        viewer_id = viewer.id if viewer else None
        is_following = False
        is_blocked = False
        if viewer_id is None:
            if privacy is not None and privacy.block_anonymous:
                raise LibraryPrivateError()
        else:
            is_following = (
                await self.repo.get_follow(viewer_id, target.id)
            ) is not None
            is_blocked = (
                await self.repo.get_block_relation(viewer_id, target.id)
            ) is not None
        visible = is_visible(
            section,
            viewer_id=viewer_id,
            author_id=target.id,
            is_follower=is_following,
            is_blocked=is_blocked,
            author_active=target.is_active and target.deleted_at is None,
        )
        if not visible:
            raise LibraryPrivateError()
        rows = await self.repo.list_user_books(target.id, status)
        return await self._responses(rows, show_progress=show_progress)

    async def _responses(
        self, rows: list[UserBook], *, show_progress: bool = True
    ) -> list[UserBookResponse]:
        books = await self.repo.get_books_by_ids([r.book_id for r in rows])
        return [
            _user_book_response(r, books[r.book_id], show_progress=show_progress)
            for r in rows
            if r.book_id in books
        ]
