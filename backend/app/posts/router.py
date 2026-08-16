"""Endpoints del módulo posts (routers finos, sin lógica).

Rutas:
- `/posts` (POST) y `/posts/{id}` (GET/PATCH/DELETE).
- `/users/{handle}/posts` (listado público, privacy-aware).
- `/posts/{id}/comments` (GET/POST) y `/posts/{id}/comments/{cid}` (DELETE).
- `/posts/{id}/like` y `/comments/{id}/like` (POST/DELETE).
"""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, Query

from app.auth.dependencies import get_current_user
from app.auth.models import User
from app.posts.dependencies import get_optional_current_user, get_posts_service
from app.posts.schemas import (
    CommentCreate,
    CommentLikeResponse,
    CommentPage,
    CommentResponse,
    PostCreate,
    PostLikeResponse,
    PostPage,
    PostResponse,
    PostUpdate,
)
from app.posts.service import PostsService

router = APIRouter()


# ---------- Posts ----------


@router.post(
    "/posts",
    response_model=PostResponse,
    status_code=201,
    summary="Crear un post (TEXT/B00K_SHARE/MEDIA)",
)
async def create_post(
    payload: PostCreate,
    user: User = Depends(get_current_user),
    service: PostsService = Depends(get_posts_service),
) -> PostResponse:
    return await service.create_post(
        user,
        type=payload.type,
        body=payload.body,
        book_id=payload.book_id,
        review_id=payload.review_id,
        visibility=payload.visibility,
        media=payload.media,
    )


@router.get(
    "/posts/{post_id}",
    response_model=PostResponse,
    summary="Detalle de un post (privacy-aware)",
)
async def get_post(
    post_id: uuid.UUID,
    viewer: User | None = Depends(get_optional_current_user),
    service: PostsService = Depends(get_posts_service),
) -> PostResponse:
    return await service.get_post(post_id, viewer)


@router.patch(
    "/posts/{post_id}",
    response_model=PostResponse,
    summary="Actualizar un post propio",
)
async def update_post(
    post_id: uuid.UUID,
    payload: PostUpdate,
    user: User = Depends(get_current_user),
    service: PostsService = Depends(get_posts_service),
) -> PostResponse:
    return await service.update_post(
        user, post_id, fields=payload.model_dump(exclude_unset=True)
    )


@router.delete(
    "/posts/{post_id}",
    status_code=204,
    summary="Borrar un post propio (soft delete)",
)
async def delete_post(
    post_id: uuid.UUID,
    user: User = Depends(get_current_user),
    service: PostsService = Depends(get_posts_service),
) -> None:
    await service.delete_post(user, post_id)


@router.get(
    "/users/{handle}/posts",
    response_model=PostPage,
    summary="Posts de un usuario (privacy-aware, paginado)",
)
async def list_user_posts(
    handle: str,
    cursor: str | None = Query(default=None),
    limit: int = Query(default=20, ge=1, le=100),
    viewer: User | None = Depends(get_optional_current_user),
    service: PostsService = Depends(get_posts_service),
) -> PostPage:
    return await service.list_user_posts(handle, viewer, cursor=cursor, limit=limit)


# ---------- Comments ----------


@router.get(
    "/posts/{post_id}/comments",
    response_model=CommentPage,
    summary="Comentarios de un post (paginado, orden cronológico)",
)
async def list_comments(
    post_id: uuid.UUID,
    cursor: str | None = Query(default=None),
    limit: int = Query(default=20, ge=1, le=100),
    viewer: User | None = Depends(get_optional_current_user),
    service: PostsService = Depends(get_posts_service),
) -> CommentPage:
    return await service.list_comments(post_id, viewer, cursor=cursor, limit=limit)


@router.post(
    "/posts/{post_id}/comments",
    response_model=CommentResponse,
    status_code=201,
    summary="Comentar un post (anidado 1 nivel)",
)
async def create_comment(
    post_id: uuid.UUID,
    payload: CommentCreate,
    user: User = Depends(get_current_user),
    service: PostsService = Depends(get_posts_service),
) -> CommentResponse:
    return await service.create_comment(
        user, post_id, body=payload.body, parent_id=payload.parent_id
    )


@router.delete(
    "/posts/{post_id}/comments/{comment_id}",
    status_code=204,
    summary="Borrar un comentario (autor o autor del post)",
)
async def delete_comment(
    post_id: uuid.UUID,
    comment_id: uuid.UUID,
    user: User = Depends(get_current_user),
    service: PostsService = Depends(get_posts_service),
) -> None:
    await service.delete_comment(user, post_id, comment_id)


# ---------- Likes ----------


@router.post(
    "/posts/{post_id}/like",
    response_model=PostLikeResponse,
    status_code=201,
    summary="Dar like a un post",
)
async def like_post(
    post_id: uuid.UUID,
    user: User = Depends(get_current_user),
    service: PostsService = Depends(get_posts_service),
) -> PostLikeResponse:
    return await service.like_post(user, post_id)


@router.delete(
    "/posts/{post_id}/like",
    status_code=204,
    summary="Quitar like a un post",
)
async def unlike_post(
    post_id: uuid.UUID,
    user: User = Depends(get_current_user),
    service: PostsService = Depends(get_posts_service),
) -> None:
    await service.unlike_post(user, post_id)


@router.post(
    "/comments/{comment_id}/like",
    response_model=CommentLikeResponse,
    status_code=201,
    summary="Dar like a un comentario",
)
async def like_comment(
    comment_id: uuid.UUID,
    user: User = Depends(get_current_user),
    service: PostsService = Depends(get_posts_service),
) -> CommentLikeResponse:
    return await service.like_comment(user, comment_id)


@router.delete(
    "/comments/{comment_id}/like",
    status_code=204,
    summary="Quitar like a un comentario",
)
async def unlike_comment(
    comment_id: uuid.UUID,
    user: User = Depends(get_current_user),
    service: PostsService = Depends(get_posts_service),
) -> None:
    await service.unlike_comment(user, comment_id)
