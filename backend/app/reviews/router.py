"""Endpoints del módulo reviews (routers finos, sin lógica).

Rutas:
- `/reviews/{book_id}`: review propia de un libro (POST/GET/PATCH/DELETE).
- `/reviews/{review_id}` y `/reviews/{review_id}/like`: review pública + likes.
- `/me/reviews`: mis reviews (paginado).
- `/books/{id}/reviews` y `/users/{handle}/reviews`: públicas (paginado).

Los parámetros `book_id` (int) se registran antes que `review_id` (UUID)
para evitar ambigüedad de ruta.
"""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, Query

from app.auth.dependencies import get_current_user
from app.auth.models import User
from app.profiles.dependencies import get_optional_current_user
from app.reviews.dependencies import get_review_service
from app.reviews.schemas import (
    MyReviewResponse,
    ReviewCreate,
    ReviewLikeResponse,
    ReviewPage,
    ReviewResponse,
    ReviewUpdate,
)
from app.reviews.service import ReviewService

router = APIRouter()


# ---------- Review propia por libro (book_id int) ----------


@router.post(
    "/reviews/{book_id:int}",
    response_model=ReviewResponse,
    status_code=201,
    summary="Publicar una review (con rating 1..5) de un libro",
)
async def create_review(
    book_id: int,
    payload: ReviewCreate,
    user: User = Depends(get_current_user),
    service: ReviewService = Depends(get_review_service),
) -> ReviewResponse:
    return await service.create_review(
        user,
        book_id,
        score=payload.score,
        title=payload.title,
        body=payload.body,
        spoiler=payload.spoiler,
        language=payload.language,
    )


@router.get(
    "/reviews/{book_id:int}",
    response_model=MyReviewResponse | None,
    summary="Mi review de un libro (null si no existe)",
)
async def get_my_review(
    book_id: int,
    user: User = Depends(get_current_user),
    service: ReviewService = Depends(get_review_service),
) -> MyReviewResponse | None:
    return await service.my_review_response(user, book_id)


@router.patch(
    "/reviews/{book_id:int}",
    response_model=ReviewResponse,
    summary="Actualizar mi review de un libro",
)
async def update_review(
    book_id: int,
    payload: ReviewUpdate,
    user: User = Depends(get_current_user),
    service: ReviewService = Depends(get_review_service),
) -> ReviewResponse:
    return await service.update_review(
        user, book_id, fields=payload.model_dump(exclude_unset=True)
    )


@router.delete(
    "/reviews/{book_id:int}",
    status_code=204,
    summary="Borrar mi review (soft delete; el rating sobrevive)",
)
async def delete_review(
    book_id: int,
    user: User = Depends(get_current_user),
    service: ReviewService = Depends(get_review_service),
) -> None:
    await service.delete_review(user, book_id)


# ---------- Review pública por id (review_id UUID) ----------


@router.get(
    "/reviews/{review_id:uuid}",
    response_model=ReviewResponse,
    summary="Detalle público de una review (privacy-aware)",
)
async def get_public_review(
    review_id: uuid.UUID,
    viewer: User | None = Depends(get_optional_current_user),
    service: ReviewService = Depends(get_review_service),
) -> ReviewResponse:
    return await service.get_public_review(review_id, viewer)


@router.post(
    "/reviews/{review_id:uuid}/like",
    response_model=ReviewLikeResponse,
    status_code=201,
    summary="Dar like a una review",
)
async def like_review(
    review_id: uuid.UUID,
    user: User = Depends(get_current_user),
    service: ReviewService = Depends(get_review_service),
) -> ReviewLikeResponse:
    return await service.like_review(user, review_id)


@router.delete(
    "/reviews/{review_id:uuid}/like",
    status_code=204,
    summary="Quitar like a una review",
)
async def unlike_review(
    review_id: uuid.UUID,
    user: User = Depends(get_current_user),
    service: ReviewService = Depends(get_review_service),
) -> None:
    await service.unlike_review(user, review_id)


# ---------- Listados ----------


@router.get(
    "/me/reviews",
    response_model=ReviewPage,
    summary="Mis reviews (paginado por cursor)",
)
async def list_my_reviews(
    cursor: str | None = Query(default=None),
    limit: int = Query(default=20, ge=1, le=100),
    user: User = Depends(get_current_user),
    service: ReviewService = Depends(get_review_service),
) -> ReviewPage:
    return await service.list_my_reviews(user, cursor=cursor, limit=limit)


@router.get(
    "/books/{book_id}/reviews",
    response_model=ReviewPage,
    summary="Reviews públicas de un libro (paginado)",
)
async def list_book_reviews(
    book_id: int,
    cursor: str | None = Query(default=None),
    limit: int = Query(default=20, ge=1, le=100),
    viewer: User | None = Depends(get_optional_current_user),
    service: ReviewService = Depends(get_review_service),
) -> ReviewPage:
    return await service.list_book_reviews(
        book_id, viewer, cursor=cursor, limit=limit
    )


@router.get(
    "/users/{handle}/reviews",
    response_model=ReviewPage,
    summary="Reviews públicas de un usuario (privacy-aware)",
)
async def list_user_reviews(
    handle: str,
    cursor: str | None = Query(default=None),
    limit: int = Query(default=20, ge=1, le=100),
    viewer: User | None = Depends(get_optional_current_user),
    service: ReviewService = Depends(get_review_service),
) -> ReviewPage:
    return await service.list_user_reviews(
        handle, viewer, cursor=cursor, limit=limit
    )
