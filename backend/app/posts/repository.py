"""Repositorio de persistencia del módulo posts.

Solo operaciones de base de datos; sin lógica de negocio.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import func
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from app.auth.models import User
from app.enums import (
    ActivityVerb,
    MentionTarget,
    ObjectType,
    Visibility,
)
from app.models import Book
from app.posts.models import (
    Comment,
    CommentLike,
    Mention,
    Post,
    PostLike,
    PostMedia,
)
from app.reviews.models import Review
from app.social.models import Activity, Block, Follow

if TYPE_CHECKING:
    CursorAfter = tuple[datetime, uuid.UUID] | None
else:
    CursorAfter = object


class PostsRepository:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    # ---------- Catálogo / usuarios ----------

    async def get_book(self, book_id: int) -> Book | None:
        return await self.db.get(Book, book_id)

    async def get_review(self, review_id: uuid.UUID) -> Review | None:
        return await self.db.get(Review, review_id)

    async def get_user(self, user_id: uuid.UUID) -> User | None:
        return await self.db.get(User, user_id)

    async def get_user_by_handle(self, handle: str) -> User | None:
        stmt = select(User).where(User.username == handle)
        return (await self.db.exec(stmt)).first()

    async def get_users_by_ids(self, ids: list[uuid.UUID]) -> list[User]:
        if not ids:
            return []
        stmt = select(User).where(User.id.in_(ids))
        return (await self.db.exec(stmt)).all()

    async def get_users_by_usernames(self, usernames: list[str]) -> list[User]:
        if not usernames:
            return []
        stmt = select(User).where(User.username.in_(usernames))
        return (await self.db.exec(stmt)).all()

    # ---------- Post ----------

    async def create_post(
        self,
        *,
        author_id: uuid.UUID,
        type,
        body: str,
        book_id: int | None,
        review_id: uuid.UUID | None,
        visibility: Visibility,
    ) -> Post:
        post = Post(
            author_id=author_id,
            type=type,
            body=body,
            book_id=book_id,
            review_id=review_id,
            visibility=visibility,
        )
        self.db.add(post)
        await self.db.flush()
        return post

    async def get_post(self, post_id: uuid.UUID) -> Post | None:
        return await self.db.get(Post, post_id)

    async def soft_delete(self, post: Post, deleted_at: datetime) -> None:
        post.deleted_at = deleted_at
        post.updated_at = datetime.now()

    async def list_posts_by_author(
        self,
        author_id: uuid.UUID,
        *,
        allowed: list[Visibility] | None,
        limit: int,
        after: CursorAfter,
    ) -> list[Post]:
        """Posts activos del autor.

        `allowed` es `None` (todas) o la lista de visibilidades aceptadas.
        Si la lista está vacía no se devuelve nada (bloqueado/privado).
        """
        if allowed == []:
            return []
        stmt = select(Post).where(
            Post.author_id == author_id, Post.deleted_at.is_(None)
        )
        if allowed is not None:
            stmt = stmt.where(Post.visibility.in_(allowed))
        if after is not None:
            created_at, row_id = after
            stmt = stmt.where((Post.created_at, Post.id) < (created_at, row_id))
        stmt = stmt.order_by(Post.created_at.desc(), Post.id.desc()).limit(limit)
        return (await self.db.exec(stmt)).all()

    # ---------- PostMedia ----------

    async def create_media_items(
        self, post_id: uuid.UUID, items: list[tuple]
    ) -> list[PostMedia]:
        created: list[PostMedia] = []
        for media_type, url, position in items:
            media = PostMedia(
                post_id=post_id, media_type=media_type, url=url, position=position
            )
            self.db.add(media)
            created.append(media)
        await self.db.flush()
        return created

    async def get_media_by_post_ids(
        self, post_ids: list[uuid.UUID]
    ) -> dict[uuid.UUID, list[PostMedia]]:
        if not post_ids:
            return {}
        stmt = (
            select(PostMedia)
            .where(PostMedia.post_id.in_(post_ids))
            .order_by(PostMedia.position.asc())
        )
        rows = (await self.db.exec(stmt)).all()
        result: dict[uuid.UUID, list[PostMedia]] = {}
        for media in rows:
            result.setdefault(media.post_id, []).append(media)
        return result

    # ---------- Comment ----------

    async def create_comment(
        self,
        *,
        post_id: uuid.UUID,
        parent_id: uuid.UUID | None,
        author_id: uuid.UUID,
        body: str,
    ) -> Comment:
        comment = Comment(
            post_id=post_id, parent_id=parent_id, author_id=author_id, body=body
        )
        self.db.add(comment)
        await self.db.flush()
        return comment

    async def get_comment(self, comment_id: uuid.UUID) -> Comment | None:
        return await self.db.get(Comment, comment_id)

    async def soft_delete_comment(self, comment: Comment, deleted_at: datetime) -> None:
        comment.deleted_at = deleted_at

    async def list_comments(
        self, post_id: uuid.UUID, *, limit: int, after: CursorAfter
    ) -> list[Comment]:
        """Comentarios del post en orden cronológico (ascendente)."""
        stmt = select(Comment).where(
            Comment.post_id == post_id, Comment.deleted_at.is_(None)
        )
        if after is not None:
            created_at, row_id = after
            stmt = stmt.where((Comment.created_at, Comment.id) > (created_at, row_id))
        stmt = stmt.order_by(Comment.created_at.asc(), Comment.id.asc()).limit(limit)
        return (await self.db.exec(stmt)).all()

    # ---------- Likes ----------

    async def get_post_like(
        self, user_id: uuid.UUID, post_id: uuid.UUID
    ) -> PostLike | None:
        stmt = select(PostLike).where(
            PostLike.user_id == user_id, PostLike.post_id == post_id
        )
        return (await self.db.exec(stmt)).first()

    async def create_post_like(self, user_id: uuid.UUID, post_id: uuid.UUID) -> PostLike:
        like = PostLike(user_id=user_id, post_id=post_id)
        self.db.add(like)
        return like

    async def delete_post_like(self, like: PostLike) -> None:
        await self.db.delete(like)

    async def get_comment_like(
        self, user_id: uuid.UUID, comment_id: uuid.UUID
    ) -> CommentLike | None:
        stmt = select(CommentLike).where(
            CommentLike.user_id == user_id, CommentLike.comment_id == comment_id
        )
        return (await self.db.exec(stmt)).first()

    async def create_comment_like(
        self, user_id: uuid.UUID, comment_id: uuid.UUID
    ) -> CommentLike:
        like = CommentLike(user_id=user_id, comment_id=comment_id)
        self.db.add(like)
        return like

    async def delete_comment_like(self, like: CommentLike) -> None:
        await self.db.delete(like)

    # ---------- Activity (log F4) ----------

    async def create_activity(
        self,
        *,
        actor_id: uuid.UUID,
        verb: ActivityVerb,
        object_type: ObjectType | None = None,
        object_id: uuid.UUID | None = None,
        target_type: str | None = None,
        target_id: uuid.UUID | None = None,
        visibility: Visibility,
    ) -> Activity:
        activity = Activity(
            actor_id=actor_id,
            verb=verb,
            object_type=object_type,
            object_id=object_id,
            target_type=target_type,
            target_id=target_id,
            visibility=visibility,
        )
        self.db.add(activity)
        return activity

    # ---------- Mentions ----------

    async def create_mention(
        self,
        *,
        content_type: MentionTarget,
        content_id: uuid.UUID,
        mentioned_user_id: uuid.UUID,
    ) -> Mention:
        mention = Mention(
            content_type=content_type,
            content_id=content_id,
            mentioned_user_id=mentioned_user_id,
        )
        self.db.add(mention)
        return mention

    async def delete_mentions_by_content(
        self, content_type: MentionTarget, content_id: uuid.UUID
    ) -> None:
        stmt = select(Mention).where(
            Mention.content_type == content_type, Mention.content_id == content_id
        )
        mentions = (await self.db.exec(stmt)).all()
        for mention in mentions:
            await self.db.delete(mention)

    # ---------- Relaciones sociales para visibilidad ----------

    async def get_follow(self, follower_id: uuid.UUID, followee_id: uuid.UUID) -> Follow | None:
        stmt = select(Follow).where(
            Follow.follower_id == follower_id, Follow.followee_id == followee_id
        )
        return (await self.db.exec(stmt)).first()

    async def get_block_relation(self, a: uuid.UUID, b: uuid.UUID) -> Block | None:
        from sqlalchemy import or_

        stmt = select(Block).where(
            or_(
                (Block.blocker_id == a) & (Block.blocked_id == b),
                (Block.blocker_id == b) & (Block.blocked_id == a),
            )
        )
        return (await self.db.exec(stmt)).first()

    # ---------- Agregación para respuestas (evita N+1) ----------

    async def get_profiles_by_user_ids(self, ids: list[uuid.UUID]) -> list:
        from app.profiles.models import Profile

        if not ids:
            return []
        stmt = select(Profile).where(Profile.user_id.in_(ids))
        return (await self.db.exec(stmt)).all()

    async def get_books_by_ids(self, ids: list[int]) -> list[Book]:
        if not ids:
            return []
        stmt = select(Book).where(Book.id.in_(ids))
        return (await self.db.exec(stmt)).all()

    async def count_likes_by_post_ids(
        self, post_ids: list[uuid.UUID]
    ) -> dict[uuid.UUID, int]:
        if not post_ids:
            return {}
        stmt = (
            select(PostLike.post_id, func.count(PostLike.id))
            .where(PostLike.post_id.in_(post_ids))
            .group_by(PostLike.post_id)
        )
        rows = (await self.db.exec(stmt)).all()
        return {post_id: count for post_id, count in rows}

    async def count_comment_likes_by_comment_ids(
        self, comment_ids: list[uuid.UUID]
    ) -> dict[uuid.UUID, int]:
        if not comment_ids:
            return {}
        stmt = (
            select(CommentLike.comment_id, func.count(CommentLike.id))
            .where(CommentLike.comment_id.in_(comment_ids))
            .group_by(CommentLike.comment_id)
        )
        rows = (await self.db.exec(stmt)).all()
        return {comment_id: count for comment_id, count in rows}

    async def count_comments_by_post_ids(
        self, post_ids: list[uuid.UUID]
    ) -> dict[uuid.UUID, int]:
        if not post_ids:
            return {}
        stmt = (
            select(Comment.post_id, func.count(Comment.id))
            .where(Comment.post_id.in_(post_ids), Comment.deleted_at.is_(None))
            .group_by(Comment.post_id)
        )
        rows = (await self.db.exec(stmt)).all()
        return {post_id: count for post_id, count in rows}

    async def get_post_like_ids_for_user(
        self, user_id: uuid.UUID, post_ids: list[uuid.UUID]
    ) -> set[uuid.UUID]:
        if not post_ids:
            return set()
        stmt = select(PostLike.post_id).where(
            PostLike.user_id == user_id, PostLike.post_id.in_(post_ids)
        )
        return {row for row in (await self.db.exec(stmt)).all()}

    async def get_comment_like_ids_for_user(
        self, user_id: uuid.UUID, comment_ids: list[uuid.UUID]
    ) -> set[uuid.UUID]:
        if not comment_ids:
            return set()
        stmt = select(CommentLike.comment_id).where(
            CommentLike.user_id == user_id, CommentLike.comment_id.in_(comment_ids)
        )
        return {row for row in (await self.db.exec(stmt)).all()}
