"""Esquemas de validación del módulo posts."""

from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import Field
from sqlmodel import SQLModel

from app.enums import MediaType, PostType, Visibility
from app.social.schemas import UserBrief


class PostMediaCreate(SQLModel):
    """Adjunto multimedia al crear un post."""

    media_type: MediaType
    url: str = Field(max_length=500)
    position: int = Field(ge=0)


class PostCreate(SQLModel):
    """Cuerpo para crear un post."""

    type: PostType = PostType.TEXT
    body: str = Field(min_length=1, max_length=10000)
    book_id: int | None = None
    review_id: uuid.UUID | None = None
    visibility: Visibility = Visibility.PUBLIC
    media: list[PostMediaCreate] | None = None


class PostUpdate(SQLModel):
    """Cuerpo para actualizar un post existente."""

    type: PostType | None = None
    body: str | None = Field(default=None, min_length=1, max_length=10000)
    visibility: Visibility | None = None


class PostMediaBrief(SQLModel):
    """Multimedia de un post en las respuestas."""

    id: str
    media_type: MediaType
    url: str
    position: int


class PostBookBrief(SQLModel):
    """Datos mínimos del libro de un BOOK_SHARE."""

    id: int
    title: str
    author: str
    thumbnail: str | None = None


class PostResponse(SQLModel):
    """Post con autor, libro, media y conteos."""

    id: str
    type: PostType
    body: str
    visibility: Visibility
    book: PostBookBrief | None = None
    review_id: str | None = None
    media: list[PostMediaBrief] = []
    like_count: int = 0
    comment_count: int = 0
    is_liked: bool = False
    created_at: datetime
    updated_at: datetime
    author: UserBrief


class PostPage(SQLModel):
    """Página de posts (cursor pagination)."""

    items: list[PostResponse]
    next: str | None = None


class CommentCreate(SQLModel):
    """Cuerpo para crear un comentario (parent opcional, 1 nivel)."""

    body: str = Field(min_length=1, max_length=5000)
    parent_id: uuid.UUID | None = None


class CommentResponse(SQLModel):
    """Comentario con autor y conteo de likes."""

    id: str
    post_id: str
    parent_id: str | None = None
    body: str
    like_count: int = 0
    is_liked: bool = False
    created_at: datetime
    author: UserBrief


class CommentPage(SQLModel):
    """Página de comentarios (cursor pagination, orden cronológico)."""

    items: list[CommentResponse]
    next: str | None = None


class PostLikeResponse(SQLModel):
    id: str
    post_id: str
    created_at: datetime


class CommentLikeResponse(SQLModel):
    id: str
    comment_id: str
    created_at: datetime
