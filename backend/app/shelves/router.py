"""Endpoints del módulo shelves (routers finos, sin lógica).

Rutas:
- `/shelves` y `/shelves/{id}`: gestión de estanterías (propias).
- `/shelves/{id}/books...`: libros en una estantería CUSTOM.
- `/library/me...`: librería del usuario autenticado (user_books).
- `/library/{handle}`: librería pública (privacy-aware).
"""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, Query

from app.auth.dependencies import get_current_user
from app.auth.models import User
from app.enums import ReadingStatus
from app.profiles.dependencies import get_optional_current_user
from app.shelves.dependencies import get_shelf_service
from app.shelves.schemas import (
    BookBrief,
    ProgressUpdate,
    ReadingProgressResponse,
    ShelfCreate,
    ShelfResponse,
    ShelfUpdate,
    UserBookResponse,
    UserBookUpdate,
)
from app.shelves.service import ShelfService

router = APIRouter()


@router.get(
    "/shelves",
    response_model=list[ShelfResponse],
    summary="Mis estanterías (incluye las 4 de estado)",
)
async def list_shelves(
    user: User = Depends(get_current_user),
    service: ShelfService = Depends(get_shelf_service),
) -> list[ShelfResponse]:
    return await service.list_shelves(user)


@router.post(
    "/shelves",
    response_model=ShelfResponse,
    status_code=201,
    summary="Crear una estantería personalizada",
)
async def create_shelf(
    payload: ShelfCreate,
    user: User = Depends(get_current_user),
    service: ShelfService = Depends(get_shelf_service),
) -> ShelfResponse:
    return await service.create_shelf(
        user,
        name=payload.name,
        description=payload.description,
        is_private=payload.is_private,
    )


@router.patch(
    "/shelves/{shelf_id}",
    response_model=ShelfResponse,
    summary="Actualizar una estantería",
)
async def update_shelf(
    shelf_id: uuid.UUID,
    payload: ShelfUpdate,
    user: User = Depends(get_current_user),
    service: ShelfService = Depends(get_shelf_service),
) -> ShelfResponse:
    return await service.update_shelf(
        user, shelf_id, fields=payload.model_dump(exclude_unset=True)
    )


@router.delete(
    "/shelves/{shelf_id}",
    status_code=204,
    summary="Borrar una estantería personalizada (las de estado no)",
)
async def delete_shelf(
    shelf_id: uuid.UUID,
    user: User = Depends(get_current_user),
    service: ShelfService = Depends(get_shelf_service),
) -> None:
    await service.delete_shelf(user, shelf_id)


@router.get(
    "/shelves/{shelf_id}/books",
    response_model=list[BookBrief],
    summary="Libros de una estantería CUSTOM",
)
async def list_shelf_books(
    shelf_id: uuid.UUID,
    user: User = Depends(get_current_user),
    service: ShelfService = Depends(get_shelf_service),
) -> list[BookBrief]:
    return await service.list_shelf_books(user, shelf_id)


@router.put(
    "/shelves/{shelf_id}/books/{book_id}",
    response_model=BookBrief,
    summary="Añadir un libro a una estantería CUSTOM",
)
async def add_book_to_shelf(
    shelf_id: uuid.UUID,
    book_id: int,
    user: User = Depends(get_current_user),
    service: ShelfService = Depends(get_shelf_service),
) -> BookBrief:
    return await service.add_book_to_shelf(user, shelf_id, book_id)


@router.delete(
    "/shelves/{shelf_id}/books/{book_id}",
    status_code=204,
    summary="Quitar un libro de una estantería CUSTOM",
)
async def remove_book_from_shelf(
    shelf_id: uuid.UUID,
    book_id: int,
    user: User = Depends(get_current_user),
    service: ShelfService = Depends(get_shelf_service),
) -> None:
    await service.remove_book_from_shelf(user, shelf_id, book_id)


# ---------- Library ----------


@router.get(
    "/library/me",
    response_model=list[UserBookResponse],
    summary="Mi librería (filtrable por estado)",
)
async def get_my_library(
    status: ReadingStatus | None = Query(default=None),
    user: User = Depends(get_current_user),
    service: ShelfService = Depends(get_shelf_service),
) -> list[UserBookResponse]:
    return await service.list_my_library(user, status)


@router.patch(
    "/library/me/{book_id}",
    response_model=UserBookResponse,
    summary="Añadir a mi librería o cambiar estado/notas de un libro",
)
async def update_or_create_user_book(
    book_id: int,
    payload: UserBookUpdate,
    user: User = Depends(get_current_user),
    service: ShelfService = Depends(get_shelf_service),
) -> UserBookResponse:
    return await service.update_or_create_user_book(
        user,
        book_id,
        status=payload.status,
        notes=payload.notes,
    )


@router.get(
    "/library/me/{book_id}",
    response_model=UserBookResponse,
    summary="Detalle de un libro de mi librería",
)
async def get_my_user_book(
    book_id: int,
    user: User = Depends(get_current_user),
    service: ShelfService = Depends(get_shelf_service),
) -> UserBookResponse:
    return await service.get_user_book_detail(user, book_id)


@router.delete(
    "/library/me/{book_id}",
    status_code=204,
    summary="Quitar un libro de mi librería",
)
async def delete_user_book(
    book_id: int,
    user: User = Depends(get_current_user),
    service: ShelfService = Depends(get_shelf_service),
) -> None:
    await service.delete_user_book(user, book_id)


@router.patch(
    "/library/me/{book_id}/progress",
    response_model=UserBookResponse,
    summary="Actualizar progreso de lectura (página/porcentaje)",
)
async def update_progress(
    book_id: int,
    payload: ProgressUpdate,
    user: User = Depends(get_current_user),
    service: ShelfService = Depends(get_shelf_service),
) -> UserBookResponse:
    return await service.update_progress(
        user,
        book_id,
        page=payload.page,
        percent=payload.percent_read,
        note=payload.note,
    )


@router.get(
    "/library/me/{book_id}/progress",
    response_model=list[ReadingProgressResponse],
    summary="Historial de progreso de un libro",
)
async def get_progress_history(
    book_id: int,
    user: User = Depends(get_current_user),
    service: ShelfService = Depends(get_shelf_service),
) -> list[ReadingProgressResponse]:
    return await service.get_progress_history(user, book_id)


@router.get(
    "/library/{handle}",
    response_model=list[UserBookResponse],
    summary="Librería pública de un usuario (privacy-aware)",
)
async def get_public_library(
    handle: str,
    status: ReadingStatus | None = Query(default=None),
    viewer: User | None = Depends(get_optional_current_user),
    service: ShelfService = Depends(get_shelf_service),
) -> list[UserBookResponse]:
    return await service.list_public_library(handle, viewer, status)
