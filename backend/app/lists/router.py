"""Endpoints del módulo lists (routers finos, sin lógica).

Rutas:
- `/lists` (POST/GET) y `/lists/{id}` (GET/PATCH/DELETE).
- `/users/{handle}/lists` (listado público, privacy-aware).
- `/lists/{id}/items` (GET/POST) y `/lists/{id}/items/{book_id}` (DELETE).
- `/lists/{id}/collaborators` (GET/POST/PATCH/DELETE, solo owner).
"""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, Query

from app.auth.dependencies import get_current_user
from app.auth.models import User
from app.lists.dependencies import get_lists_service, get_optional_current_user
from app.lists.schemas import (
    ListCollaboratorAdd,
    ListCollaboratorUpdate,
    ListCreate,
    ListDetail,
    ListItemAdd,
    ListItemBrief,
    ListItemPage,
    ListPage,
    ListUpdate,
)
from app.lists.service import ListsService

router = APIRouter()


# ---------- List ----------


@router.post(
    "/lists",
    response_model=ListDetail,
    status_code=201,
    summary="Crear una lista curada",
)
async def create_list(
    payload: ListCreate,
    user: User = Depends(get_current_user),
    service: ListsService = Depends(get_lists_service),
) -> ListDetail:
    return await service.create_list(
        user,
        title=payload.title,
        description=payload.description,
        visibility=payload.visibility,
    )


@router.get(
    "/lists",
    response_model=ListPage,
    summary="Mis listas (paginado por cursor)",
)
async def list_my_lists(
    cursor: str | None = Query(default=None),
    limit: int = Query(default=20, ge=1, le=100),
    user: User = Depends(get_current_user),
    service: ListsService = Depends(get_lists_service),
) -> ListPage:
    return await service.list_my_lists(user, cursor=cursor, limit=limit)


@router.get(
    "/users/{handle}/lists",
    response_model=ListPage,
    summary="Listas públicas de un usuario (privacy-aware, paginado)",
)
async def list_user_lists(
    handle: str,
    cursor: str | None = Query(default=None),
    limit: int = Query(default=20, ge=1, le=100),
    viewer: User | None = Depends(get_optional_current_user),
    service: ListsService = Depends(get_lists_service),
) -> ListPage:
    return await service.list_user_lists(handle, viewer, cursor=cursor, limit=limit)


@router.get(
    "/lists/{list_id}",
    response_model=ListDetail,
    summary="Detalle de una lista (privacy-aware)",
)
async def get_list(
    list_id: uuid.UUID,
    viewer: User | None = Depends(get_optional_current_user),
    service: ListsService = Depends(get_lists_service),
) -> ListDetail:
    return await service.get_list(list_id, viewer)


@router.patch(
    "/lists/{list_id}",
    response_model=ListDetail,
    summary="Actualizar una lista (solo owner)",
)
async def update_list(
    list_id: uuid.UUID,
    payload: ListUpdate,
    user: User = Depends(get_current_user),
    service: ListsService = Depends(get_lists_service),
) -> ListDetail:
    return await service.update_list(
        user, list_id, fields=payload.model_dump(exclude_unset=True)
    )


@router.delete(
    "/lists/{list_id}",
    status_code=204,
    summary="Borrar una lista (solo owner, soft delete)",
)
async def delete_list(
    list_id: uuid.UUID,
    user: User = Depends(get_current_user),
    service: ListsService = Depends(get_lists_service),
) -> None:
    await service.delete_list(user, list_id)


# ---------- Items ----------


@router.get(
    "/lists/{list_id}/items",
    response_model=ListItemPage,
    summary="Items de una lista (paginado)",
)
async def list_items(
    list_id: uuid.UUID,
    cursor: str | None = Query(default=None),
    limit: int = Query(default=20, ge=1, le=100),
    viewer: User | None = Depends(get_optional_current_user),
    service: ListsService = Depends(get_lists_service),
) -> ListItemPage:
    return await service.list_items(list_id, viewer, cursor=cursor, limit=limit)


@router.post(
    "/lists/{list_id}/items",
    response_model=ListItemBrief,
    status_code=201,
    summary="Añadir un libro a la lista (owner o EDITOR)",
)
async def add_item(
    list_id: uuid.UUID,
    payload: ListItemAdd,
    user: User = Depends(get_current_user),
    service: ListsService = Depends(get_lists_service),
) -> ListItemBrief:
    return await service.add_item(
        user,
        list_id,
        book_id=payload.book_id,
        note=payload.note,
        position=payload.position,
    )


@router.delete(
    "/lists/{list_id}/items/{book_id}",
    status_code=204,
    summary="Quitar un libro de la lista (owner o EDITOR)",
)
async def remove_item(
    list_id: uuid.UUID,
    book_id: int,
    user: User = Depends(get_current_user),
    service: ListsService = Depends(get_lists_service),
) -> None:
    await service.remove_item(user, list_id, book_id)


# ---------- Collaborators ----------


@router.post(
    "/lists/{list_id}/collaborators",
    response_model=ListDetail,
    status_code=201,
    summary="Añadir un colaborador (solo owner)",
)
async def add_collaborator(
    list_id: uuid.UUID,
    payload: ListCollaboratorAdd,
    user: User = Depends(get_current_user),
    service: ListsService = Depends(get_lists_service),
) -> ListDetail:
    return await service.add_collaborator(
        user,
        list_id,
        collaborator_id=payload.user_id,
        role=payload.role,
        can_add_books=payload.can_add_books,
    )


@router.patch(
    "/lists/{list_id}/collaborators/{user_id}",
    response_model=ListDetail,
    summary="Actualizar el rol de un colaborador (solo owner)",
)
async def update_collaborator(
    list_id: uuid.UUID,
    user_id: uuid.UUID,
    payload: ListCollaboratorUpdate,
    user: User = Depends(get_current_user),
    service: ListsService = Depends(get_lists_service),
) -> ListDetail:
    return await service.update_collaborator(
        user,
        list_id,
        user_id,
        fields=payload.model_dump(exclude_unset=True),
    )


@router.delete(
    "/lists/{list_id}/collaborators/{user_id}",
    status_code=204,
    summary="Quitar un colaborador (solo owner)",
)
async def remove_collaborator(
    list_id: uuid.UUID,
    user_id: uuid.UUID,
    user: User = Depends(get_current_user),
    service: ListsService = Depends(get_lists_service),
) -> None:
    await service.remove_collaborator(user, list_id, user_id)
