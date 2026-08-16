"""Models del context POSTS & ENGAGEMENT (FASE 6).

Diseño (documento de arquitectura §2.17–2.21):
- `Post`: publicación con tipo (TEXT/B00K_SHARE/MEDIA), body, `book_id`
  FK a catálogo con ON DELETE RESTRICT, `review_id` FK a reviews SET NULL,
  `visibility` (PUBLIC/FOLLOWERS/PRIVATE) y soft delete (ADR-8).
- `PostMedia`: attachments de un post (imagen/vídeo/audio) ordenados.
- `PostLike`: like de un post, UNIQUE (user, post).
- `Comment`: comentario anidado 1 solo nivel: `parent_id` solo puede
  apuntar a un comentario raíz del mismo post (sin nietos).
- `CommentLike`: like de un comentario, UNIQUE (user, comment).
- `Mention`: mención detectada en el body de un post/comentario
  (content polimórfico sin FK), UNIQUE (content_type, content_id, user).

El borrado de contenido público es soft delete (ADR-8): `deleted_at`.
El cascade duro de las FK (CASCADE) solo aplica cuando el padre se borra
físicamente (p. ej. borrado irreversible de un usuario).
"""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import (
    Column,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy import Enum as SAEnum
from sqlalchemy import text
from sqlalchemy.dialects.postgresql import UUID as PgUUID
from sqlmodel import Field, SQLModel

from app.core.time import utcnow
from app.enums import MediaType, MentionTarget, PostType, Visibility


def _datetime(required: bool = True):
    return Column(DateTime(timezone=True), nullable=not required, default=utcnow)


def _uuid_pk():
    return Column(PgUUID(as_uuid=True), primary_key=True)


def _user_fk(name: str, *, ondelete: str = "CASCADE") -> Column:
    return Column(
        PgUUID(as_uuid=True),
        ForeignKey("users.id", ondelete=ondelete),
        nullable=False,
    )


class Post(SQLModel, table=True):
    """Publicación en el timeline."""

    __tablename__ = "posts"
    __table_args__ = (
        Index(
            "ix_posts_author_created",
            "author_id",
            text("created_at DESC"),
        ),
        Index("ix_posts_book_id", "book_id"),
        Index("ix_posts_review_id", "review_id"),
    )

    id: uuid.UUID = Field(default_factory=uuid.uuid4, sa_column=_uuid_pk())
    author_id: uuid.UUID = Field(sa_column=_user_fk("author_id"))
    type: PostType = Field(
        default=PostType.TEXT,
        sa_column=Column(SAEnum(PostType, name="post_type"), nullable=False),
    )
    body: str = Field(sa_column=Column(Text, nullable=False))
    book_id: int | None = Field(
        default=None,
        sa_column=Column(
            Integer, ForeignKey("books.id", ondelete="RESTRICT"), nullable=True
        ),
    )
    review_id: uuid.UUID | None = Field(
        default=None,
        sa_column=Column(
            PgUUID(as_uuid=True),
            ForeignKey("reviews.id", ondelete="SET NULL"),
            nullable=True,
        ),
    )
    visibility: Visibility = Field(
        default=Visibility.PUBLIC,
        sa_column=Column(SAEnum(Visibility, name="visibility"), nullable=False),
    )
    deleted_at: datetime | None = Field(
        default=None, sa_column=Column(DateTime(timezone=True), nullable=True)
    )
    created_at: datetime = Field(sa_column=_datetime(required=True))
    updated_at: datetime = Field(sa_column=_datetime(required=True))


class PostMedia(SQLModel, table=True):
    """Multimedia adjunta a un post."""

    __tablename__ = "post_media"
    __table_args__ = (
        Index("ix_post_media_post", "post_id", "position"),
        UniqueConstraint("post_id", "position", name="uq_post_media_post_position"),
    )

    id: uuid.UUID = Field(default_factory=uuid.uuid4, sa_column=_uuid_pk())
    post_id: uuid.UUID = Field(
        sa_column=Column(
            PgUUID(as_uuid=True),
            ForeignKey("posts.id", ondelete="CASCADE"),
            nullable=False,
        )
    )
    media_type: MediaType = Field(
        sa_column=Column(SAEnum(MediaType, name="media_type"), nullable=False)
    )
    url: str = Field(sa_column=Column(String(500), nullable=False))
    position: int = Field(sa_column=Column(Integer, nullable=False))
    created_at: datetime = Field(sa_column=_datetime(required=True))


class PostLike(SQLModel, table=True):
    """Like de un post (UNIQUE user+post → likes idempotentes)."""

    __tablename__ = "post_likes"
    __table_args__ = (
        UniqueConstraint("user_id", "post_id", name="uq_post_likes_user_post"),
        Index("ix_post_likes_post", "post_id"),
        Index("ix_post_likes_user", "user_id"),
    )

    id: uuid.UUID = Field(default_factory=uuid.uuid4, sa_column=_uuid_pk())
    user_id: uuid.UUID = Field(sa_column=_user_fk("user_id"))
    post_id: uuid.UUID = Field(
        sa_column=Column(
            PgUUID(as_uuid=True),
            ForeignKey("posts.id", ondelete="CASCADE"),
            nullable=False,
        )
    )
    created_at: datetime = Field(sa_column=_datetime(required=True))


class Comment(SQLModel, table=True):
    """Comentario sobre un post, con anidado de 1 nivel (parent_id)."""

    __tablename__ = "comments"
    __table_args__ = (
        Index("ix_comments_post_created", "post_id", text("created_at ASC")),
        Index("ix_comments_parent", "parent_id"),
    )

    id: uuid.UUID = Field(default_factory=uuid.uuid4, sa_column=_uuid_pk())
    post_id: uuid.UUID = Field(
        sa_column=Column(
            PgUUID(as_uuid=True),
            ForeignKey("posts.id", ondelete="CASCADE"),
            nullable=False,
        )
    )
    parent_id: uuid.UUID | None = Field(
        default=None,
        sa_column=Column(
            PgUUID(as_uuid=True),
            ForeignKey("comments.id", ondelete="SET NULL"),
            nullable=True,
        ),
    )
    author_id: uuid.UUID = Field(sa_column=_user_fk("author_id"))
    body: str = Field(sa_column=Column(Text, nullable=False))
    deleted_at: datetime | None = Field(
        default=None, sa_column=Column(DateTime(timezone=True), nullable=True)
    )
    created_at: datetime = Field(sa_column=_datetime(required=True))


class CommentLike(SQLModel, table=True):
    """Like de un comentario (UNIQUE user+comment → likes idempotentes)."""

    __tablename__ = "comment_likes"
    __table_args__ = (
        UniqueConstraint("user_id", "comment_id", name="uq_comment_likes_user_comment"),
        Index("ix_comment_likes_comment", "comment_id"),
        Index("ix_comment_likes_user", "user_id"),
    )

    id: uuid.UUID = Field(default_factory=uuid.uuid4, sa_column=_uuid_pk())
    user_id: uuid.UUID = Field(sa_column=_user_fk("user_id"))
    comment_id: uuid.UUID = Field(
        sa_column=Column(
            PgUUID(as_uuid=True),
            ForeignKey("comments.id", ondelete="CASCADE"),
            nullable=False,
        )
    )
    created_at: datetime = Field(sa_column=_datetime(required=True))


class Mention(SQLModel, table=True):
    """Mención detectada en el body de un post/comentario.

    `content_type`/`content_id` son polimórficos (sin FK): apuntan al post
    o comentario que menciona. El UNIQUE impide duplicar la misma mención
    en el mismo contenido.
    """

    __tablename__ = "mentions"
    __table_args__ = (
        UniqueConstraint(
            "content_type",
            "content_id",
            "mentioned_user_id",
            name="uq_mentions_content_user",
        ),
        Index("ix_mentions_mentioned", "mentioned_user_id"),
        Index("ix_mentions_content", "content_type", "content_id"),
    )

    id: uuid.UUID = Field(default_factory=uuid.uuid4, sa_column=_uuid_pk())
    content_type: MentionTarget = Field(
        sa_column=Column(SAEnum(MentionTarget, name="mention_target"), nullable=False)
    )
    content_id: uuid.UUID = Field(sa_column=Column(PgUUID(as_uuid=True), nullable=False))
    mentioned_user_id: uuid.UUID = Field(
        sa_column=_user_fk("mentioned_user_id")
    )
    created_at: datetime = Field(sa_column=_datetime(required=True))