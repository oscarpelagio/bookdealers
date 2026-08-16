"""Lógica de dominio del módulo lists (FASE 7).

Reglas (documento §2.3 y FASE 7):
- Solo la owner cambia título/descripción/visibilidad y gestiona
  colaboradores. EDITOR añade/elimina items; VIEWER solo ve (salvo que
  `can_add_books` lo permita para añadir).
- `slug` se deriva del título y es único por owner (UNIQUE owner_id+slug);
  al borrar la lista (soft delete) se libera el slug para re-crearla.
- Crear una lista genera actividad `LIST_CREATED` (snapshot de la
  visibilidad del actor, ADR-4) → entra en el feed (F5).
- La visibilidad de cada lista (PUBLIC/FOLLOWERS/PRIVATE) sigue ADR-4;
  los colaboradores siempre pueden ver la lista (y el owner siempre).
"""

from __future__ import annotations

import re
import unicodedata
import uuid

from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from app.auth.models import User
from app.core.events import event_bus
from app.core.pagination import decode_cursor, encode_cursor
from app.core.time import utcnow
from app.core.visibility import is_visible
from app.enums import ActivityVerb, CollaboratorRole, Visibility
from app.lists import events
from app.lists.exceptions import (
    CannotCollaborateSelfError,
    CollaboratorAlreadyExistsError,
    CollaboratorNotFoundError,
    ListForbiddenError,
    ListItemAlreadyExistsError,
    ListItemNotFoundError,
    ListNotFoundError,
    ListPrivateError,
)
from app.lists.models import List as ListModel
from app.lists.repository import ListsRepository
from app.lists.schemas import (
    BookBrief,
    ListCollaboratorBrief,
    ListDetail,
    ListItemBrief,
    ListItemPage,
    ListPage,
    ListSummary,
)
from app.shelves.exceptions import BookNotFoundError
from app.social.exceptions import UserNotFoundError
from app.social.schemas import UserBrief


def _slugify(text: str) -> str:
    normalized = (
        unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode("ascii")
    )
    slug = re.sub(r"[^\w]+", "-", normalized).strip("-").lower()
    return slug[:150] or "lista"


class ListsService:
    def __init__(self, repo: ListsRepository, db: AsyncSession) -> None:
        self.repo = repo
        self.db = db

    # ---------- List ----------

    async def create_list(
        self, user: User, *, title: str, description: str | None, visibility: Visibility
    ) -> ListDetail:
        slug = await self._unique_slug(user.id, title)
        list_model = await self.repo.create_list(
            owner_id=user.id,
            title=title,
            description=description,
            visibility=visibility,
            slug=slug,
        )
        activity_visibility = await self._activity_visibility(user.id)
        await self.repo.create_activity(
            actor_id=user.id,
            verb=ActivityVerb.LIST_CREATED,
            target_type="LIST",
            target_id=list_model.id,
            visibility=activity_visibility,
        )
        await self.db.commit()
        await self.db.refresh(list_model)
        await event_bus.publish(events.list_created(str(list_model.id), str(user.id)))
        return await self._detail_response(list_model, user)

    async def get_list(self, list_id: uuid.UUID, viewer) -> ListDetail:
        list_model = await self._visible_list(list_id, viewer)
        return await self._detail_response(list_model, viewer)

    async def update_list(
        self, user: User, list_id: uuid.UUID, *, fields: dict
    ) -> ListDetail:
        list_model = await self._visible_list(list_id, user)
        if list_model.owner_id != user.id:
            raise ListForbiddenError()

        for field in ("title", "description", "visibility"):
            if field in fields:
                setattr(list_model, field, fields[field])
        list_model.updated_at = utcnow()
        await self.db.commit()
        await self.db.refresh(list_model)
        await event_bus.publish(events.list_updated(str(list_model.id), str(user.id)))
        return await self._detail_response(list_model, user)

    async def delete_list(self, user: User, list_id: uuid.UUID) -> None:
        list_model = await self.repo.get_list(list_id)
        if list_model is None or list_model.deleted_at is not None:
            raise ListNotFoundError()
        if list_model.owner_id != user.id:
            raise ListForbiddenError()

        # Soft delete: se libera el slug para poder re-crear la lista.
        list_model.slug = f"{_slugify(list_model.title)}-del-{list_model.id.hex[:8]}"
        await self.repo.soft_delete(list_model, utcnow())
        await self.db.commit()
        await event_bus.publish(events.list_deleted(str(list_model.id), str(user.id)))

    async def list_my_lists(
        self, user: User, *, cursor: str | None, limit: int
    ) -> ListPage:
        after = decode_cursor(cursor)
        lists = await self.repo.list_owner_lists(
            user.id, limit=limit + 1, after=after
        )
        return await self._paginate_lists(lists, user, limit)

    async def list_user_lists(
        self, handle: str, viewer, *, cursor: str | None, limit: int
    ) -> ListPage:
        owner = await self.repo.get_user_by_handle(handle)
        if owner is None or not owner.is_active or owner.deleted_at is not None:
            raise UserNotFoundError()

        viewer_id = viewer.id if viewer else None
        allowed: list[Visibility] | None
        if viewer_id is not None and viewer_id == owner.id:
            allowed = None
        elif viewer_id is not None and (
            await self.repo.get_block_relation(viewer_id, owner.id)
        ) is not None:
            allowed = []
        else:
            allowed = [Visibility.PUBLIC]
            if viewer_id is not None and (
                await self.repo.get_follow(viewer_id, owner.id)
            ) is not None:
                allowed.append(Visibility.FOLLOWERS)

        # Las listas con colaboradores del espectador también entran.
        collab_list_ids: list[uuid.UUID] = []
        if viewer_id is not None:
            from app.lists.models import ListCollaborator

            stmt = select(ListCollaborator.list_id).where(
                ListCollaborator.user_id == viewer_id
            )
            collab_list_ids = [r for r in (await self.db.exec(stmt)).all()]

        after = decode_cursor(cursor)
        if allowed == []:
            lists: list[ListModel] = []
        else:
            stmt = select(ListModel).where(
                ListModel.owner_id == owner.id, ListModel.deleted_at.is_(None)
            )
            if allowed is not None:
                stmt = stmt.where(
                    (ListModel.visibility.in_(allowed))
                    | (ListModel.id.in_(collab_list_ids))
                )
            if after is not None:
                created_at, row_id = after
                stmt = stmt.where((ListModel.created_at, ListModel.id) < (created_at, row_id))
            stmt = stmt.order_by(ListModel.created_at.desc(), ListModel.id.desc()).limit(
                limit + 1
            )
            lists = (await self.db.exec(stmt)).all()

        has_more = len(lists) > limit
        page = lists[:limit]
        next_cursor = None
        if has_more and page:
            last = page[-1]
            next_cursor = encode_cursor(last.created_at, last.id)
        items = await self._summary_responses(page, viewer)
        return ListPage(items=items, next=next_cursor)

    # ---------- Items ----------

    async def add_item(
        self,
        user: User,
        list_id: uuid.UUID,
        *,
        book_id: int,
        note: str | None,
        position: int | None,
    ) -> ListItemBrief:
        list_model = await self._visible_list(list_id, user)
        await self._require_editor(list_model, user)

        if await self.repo.get_book(book_id) is None:
            raise BookNotFoundError()
        if await self.repo.get_item(list_id, book_id) is not None:
            raise ListItemAlreadyExistsError()

        if position is None:
            position = await self.repo.get_next_position(list_id)
        item = await self.repo.add_item(
            list_id=list_id,
            book_id=book_id,
            added_by=user.id,
            note=note,
            position=position,
        )
        await self.db.commit()
        await self.db.refresh(item)
        await event_bus.publish(
            events.list_item_added(str(list_id), book_id, str(user.id))
        )
        return await self._item_response(item, user)

    async def remove_item(
        self, user: User, list_id: uuid.UUID, book_id: int
    ) -> None:
        list_model = await self._visible_list(list_id, user)
        await self._require_editor(list_model, user)

        item = await self.repo.get_item(list_id, book_id)
        if item is None:
            raise ListItemNotFoundError()
        await self.repo.delete_item(item)
        await self.db.commit()
        await event_bus.publish(events.list_item_removed(str(list_id), book_id))

    async def list_items(
        self, list_id: uuid.UUID, viewer, *, cursor: str | None, limit: int
    ) -> ListItemPage:
        await self._visible_list(list_id, viewer)
        after = decode_cursor(cursor)
        items = await self.repo.list_items(list_id, limit=limit + 1, after=after)
        has_more = len(items) > limit
        page = items[:limit]
        next_cursor = None
        if has_more and page:
            last = page[-1]
            next_cursor = encode_cursor(last.created_at, last.id)
        result: list[ListItemBrief] = []
        if page:
            result = await self._item_responses(page, viewer)
        return ListItemPage(items=result, next=next_cursor)

    # ---------- Collaborators ----------

    async def add_collaborator(
        self,
        user: User,
        list_id: uuid.UUID,
        *,
        collaborator_id: uuid.UUID,
        role: CollaboratorRole,
        can_add_books: bool | None,
    ) -> ListDetail:
        list_model = await self._visible_list(list_id, user)
        if list_model.owner_id != user.id:
            raise ListForbiddenError()
        if collaborator_id == user.id:
            raise CannotCollaborateSelfError()

        collab_user = await self.repo.get_user(collaborator_id)
        if collab_user is None or not collab_user.is_active or collab_user.deleted_at is not None:
            raise UserNotFoundError()
        if await self.repo.get_collaborator(list_id, collaborator_id) is not None:
            raise CollaboratorAlreadyExistsError()

        resolved_can_add = (
            can_add_books
            if can_add_books is not None
            else role == CollaboratorRole.EDITOR
        )
        await self.repo.add_collaborator(
            list_id=list_id,
            user_id=collaborator_id,
            role=role,
            can_add_books=resolved_can_add,
        )
        await self.db.commit()
        await event_bus.publish(
            events.collaborator_added(str(list_id), str(collaborator_id))
        )
        return await self._detail_response(list_model, user)

    async def update_collaborator(
        self,
        user: User,
        list_id: uuid.UUID,
        collaborator_id: uuid.UUID,
        *,
        fields: dict,
    ) -> ListDetail:
        list_model = await self._visible_list(list_id, user)
        if list_model.owner_id != user.id:
            raise ListForbiddenError()

        collab = await self.repo.get_collaborator(list_id, collaborator_id)
        if collab is None:
            raise CollaboratorNotFoundError()
        if "role" in fields:
            collab.role = fields["role"]
        if "can_add_books" in fields:
            collab.can_add_books = fields["can_add_books"]
        await self.db.commit()
        await event_bus.publish(
            events.collaborator_updated(str(list_id), str(collaborator_id))
        )
        return await self._detail_response(list_model, user)

    async def remove_collaborator(
        self, user: User, list_id: uuid.UUID, collaborator_id: uuid.UUID
    ) -> None:
        list_model = await self._visible_list(list_id, user)
        if list_model.owner_id != user.id:
            raise ListForbiddenError()

        collab = await self.repo.get_collaborator(list_id, collaborator_id)
        if collab is None:
            raise CollaboratorNotFoundError()
        await self.repo.delete_collaborator(collab)
        await self.db.commit()
        await event_bus.publish(
            events.collaborator_removed(str(list_id), str(collaborator_id))
        )

    # ---------- Helpers de permisos ----------

    async def _visible_list(self, list_id: uuid.UUID, viewer) -> ListModel:
        list_model = await self.repo.get_list(list_id)
        if list_model is None or list_model.deleted_at is not None:
            raise ListNotFoundError()
        owner = await self.repo.get_user(list_model.owner_id)
        if owner is None or not owner.is_active or owner.deleted_at is not None:
            raise ListNotFoundError()

        viewer_id = viewer.id if viewer else None
        if viewer_id is not None:
            if viewer_id == list_model.owner_id:
                return list_model
            if (
                await self.repo.get_collaborator(list_id, viewer_id)
            ) is not None:
                return list_model
            if (
                await self.repo.get_block_relation(viewer_id, list_model.owner_id)
            ) is not None:
                raise ListNotFoundError()

        is_follower = False
        if viewer_id is not None:
            is_follower = (
                await self.repo.get_follow(viewer_id, list_model.owner_id)
            ) is not None
        visible = is_visible(
            list_model.visibility,
            viewer_id=viewer_id,
            author_id=list_model.owner_id,
            is_follower=is_follower,
            is_blocked=False,
            author_active=owner.is_active and owner.deleted_at is None,
        )
        if not visible:
            raise ListPrivateError()
        return list_model

    async def _require_editor(self, list_model: ListModel, user: User) -> None:
        if list_model.owner_id == user.id:
            return
        collab = await self.repo.get_collaborator(list_model.id, user.id)
        if collab is None:
            raise ListForbiddenError()
        if collab.role != CollaboratorRole.EDITOR and not collab.can_add_books:
            raise ListForbiddenError()

    async def _unique_slug(self, owner_id: uuid.UUID, title: str) -> str:
        base = _slugify(title)
        candidate = base
        counter = 2
        while await self.repo.slug_exists(owner_id, candidate):
            candidate = f"{base}-{counter}"
            counter += 1
        return candidate

    async def _activity_visibility(self, user_id: uuid.UUID) -> Visibility:
        from app.profiles.models import PrivacySetting

        from sqlmodel import select

        stmt = select(PrivacySetting).where(PrivacySetting.user_id == user_id)
        privacy = (await self.db.exec(stmt)).first()
        return privacy.activity_visibility if privacy else Visibility.PUBLIC

    # ---------- Respuestas ----------

    async def _paginate_lists(
        self, lists: list[ListModel], viewer, limit: int
    ) -> ListPage:
        has_more = len(lists) > limit
        page = lists[:limit]
        next_cursor = None
        if has_more and page:
            last = page[-1]
            next_cursor = encode_cursor(last.created_at, last.id)
        items = await self._summary_responses(page, viewer)
        return ListPage(items=items, next=next_cursor)

    async def _summary_responses(
        self, lists: list[ListModel], viewer
    ) -> list[ListSummary]:
        if not lists:
            return []

        owner_ids = list({l.owner_id for l in lists})
        list_ids = [l.id for l in lists]
        users = {u.id: u for u in await self.repo.get_users_by_ids(owner_ids)}
        profiles = {
            p.user_id: p for p in await self.repo.get_profiles_by_user_ids(owner_ids)
        }
        counts = await self.repo.count_items_by_list_ids(list_ids)

        result: list[ListSummary] = []
        for list_model in lists:
            owner = users.get(list_model.owner_id)
            if owner is None:
                continue
            profile = profiles.get(list_model.owner_id)
            result.append(
                ListSummary(
                    id=str(list_model.id),
                    title=list_model.title,
                    slug=list_model.slug,
                    description=list_model.description,
                    visibility=list_model.visibility,
                    item_count=counts.get(list_model.id, 0),
                    created_at=list_model.created_at,
                    updated_at=list_model.updated_at,
                    owner=UserBrief(
                        id=str(owner.id),
                        username=owner.username,
                        display_name=profile.display_name if profile else None,
                        avatar_url=profile.avatar_url if profile else None,
                    ),
                )
            )
        return result

    async def _detail_response(
        self, list_model: ListModel, viewer
    ) -> ListDetail:
        summaries = await self._summary_responses([list_model], viewer)
        base = summaries[0]
        collaborators = await self.repo.list_collaborators(list_model.id)
        collab_briefs = await self._collaborator_briefs(collaborators)

        viewer_id = viewer.id if viewer else None
        is_owner = viewer_id == list_model.owner_id
        is_collaborator = any(c.user_id == viewer_id for c in collaborators)
        can_edit = is_owner or any(
            c.user_id == viewer_id
            and (c.role == CollaboratorRole.EDITOR or c.can_add_books)
            for c in collaborators
        )

        return ListDetail(
            **base.model_dump(),
            collaborators=collab_briefs,
            is_owner=is_owner,
            is_collaborator=is_collaborator,
            can_edit=can_edit,
        )

    async def _collaborator_briefs(
        self, collaborators
    ) -> list[ListCollaboratorBrief]:
        if not collaborators:
            return []
        user_ids = [c.user_id for c in collaborators]
        users = {u.id: u for u in await self.repo.get_users_by_ids(user_ids)}
        profiles = {
            p.user_id: p for p in await self.repo.get_profiles_by_user_ids(user_ids)
        }
        result: list[ListCollaboratorBrief] = []
        for c in collaborators:
            user = users.get(c.user_id)
            if user is None:
                continue
            profile = profiles.get(c.user_id)
            result.append(
                ListCollaboratorBrief(
                    id=str(c.id),
                    user=UserBrief(
                        id=str(user.id),
                        username=user.username,
                        display_name=profile.display_name if profile else None,
                        avatar_url=profile.avatar_url if profile else None,
                    ),
                    role=c.role,
                    can_add_books=c.can_add_books,
                    created_at=c.created_at,
                )
            )
        return result

    async def _item_responses(
        self, items, viewer
    ) -> list[ListItemBrief]:
        if not items:
            return []

        book_ids = [i.book_id for i in items]
        added_by_ids = list({i.added_by for i in items})
        books = {b.id: b for b in await self.repo.get_books_by_ids(book_ids)}
        users = {u.id: u for u in await self.repo.get_users_by_ids(added_by_ids)}
        profiles = {
            p.user_id: p for p in await self.repo.get_profiles_by_user_ids(added_by_ids)
        }

        result: list[ListItemBrief] = []
        for item in items:
            book = books.get(item.book_id)
            if book is None:
                continue
            adder = users.get(item.added_by)
            profile = profiles.get(item.added_by) if adder else None
            result.append(
                ListItemBrief(
                    id=str(item.id),
                    book=BookBrief(
                        id=book.id,
                        title=book.title,
                        author=book.author,
                        thumbnail=book.thumbnail,
                    ),
                    note=item.note,
                    position=item.position,
                    added_by=UserBrief(
                        id=str(item.added_by),
                        username=adder.username if adder else "",
                        display_name=profile.display_name if profile else None,
                        avatar_url=profile.avatar_url if profile else None,
                    ),
                    created_at=item.created_at,
                )
            )
        return result

    async def _item_response(self, item, viewer) -> ListItemBrief:
        items = await self._item_responses([item], viewer)
        return items[0]
