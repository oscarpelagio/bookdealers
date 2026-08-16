"""Lógica de dominio del módulo posts (FASE 6).

Reglas (documento §2.17–2.21):
- Crear un post genera una entrada `POST` en el log de actividades (F4)
  con la visibilidad de la actividad del autor (snapshot, ADR-4), de modo
  que el feed (F5) lo muestra automáticamente.
- Los comentarios solo soportan 1 nivel de anidación (parent sin parent).
- El borrado de posts/comentarios es soft delete (ADR-8).
- Las menciones `@usuario` del body se persisten en `mentions` y emiten
  el evento `posts.mention_detected` (notificaciones en F8).
- La visibilidad de cada post sigue su propio campo `visibility`
  (ADR-4): el autor siempre ve, PRIVATE solo autor, FOLLOWERS autor+
  seguidores; un block (cualquier dirección) oculta el post.
"""

from __future__ import annotations

import re
import uuid

from sqlalchemy.exc import IntegrityError
from sqlmodel.ext.asyncio.session import AsyncSession

from app.auth.models import User
from app.core.events import event_bus
from app.core.pagination import decode_cursor, encode_cursor
from app.core.time import utcnow
from app.core.visibility import is_visible
from app.enums import (
    ActivityVerb,
    MentionTarget,
    ObjectType,
    PostType,
    Visibility,
)
from app.posts import events
from app.posts.exceptions import (
    BookShareRequiresBookError,
    CommentForbiddenError,
    CommentNotFoundError,
    NestedCommentsNotAllowedError,
    PostForbiddenError,
    PostNotFoundError,
    PostPrivateError,
    ReviewNotFoundError,
)
from app.posts.models import Comment, Post
from app.posts.repository import PostsRepository
from app.posts.schemas import (
    CommentLikeResponse,
    CommentPage,
    CommentResponse,
    PostBookBrief,
    PostLikeResponse,
    PostMediaBrief,
    PostPage,
    PostResponse,
)
from app.shelves.exceptions import BookNotFoundError
from app.social.exceptions import UserNotFoundError
from app.social.schemas import UserBrief

_MENTION_RE = re.compile(r"(?<![\w.])@([A-Za-z0-9_.]{3,30})")


def _extract_usernames(text: str) -> set[str]:
    return {m.group(1) for m in _MENTION_RE.finditer(text)}


class PostsService:
    def __init__(self, repo: PostsRepository, db: AsyncSession) -> None:
        self.repo = repo
        self.db = db

    # ---------- Posts ----------

    async def create_post(
        self,
        user: User,
        *,
        type: PostType,
        body: str,
        book_id: int | None,
        review_id: uuid.UUID | None,
        visibility: Visibility,
        media: list | None,
    ) -> PostResponse:
        if type == PostType.BOOK_SHARE and book_id is None:
            raise BookShareRequiresBookError()
        if book_id is not None and await self.repo.get_book(book_id) is None:
            raise BookNotFoundError()
        if review_id is not None and await self.repo.get_review(review_id) is None:
            raise ReviewNotFoundError()

        post = await self.repo.create_post(
            author_id=user.id,
            type=type,
            body=body,
            book_id=book_id,
            review_id=review_id,
            visibility=visibility,
        )

        if media:
            items = [
                (m.media_type, m.url, m.position)
                for m in sorted(media, key=lambda m: m.position)
            ]
            await self.repo.create_media_items(post.id, items)

        await self._register_mentions(
            content_type=MentionTarget.POST, content_id=post.id, text=body, actor_id=user.id
        )
        activity_visibility = await self._activity_visibility(user.id)
        await self.repo.create_activity(
            actor_id=user.id,
            verb=ActivityVerb.POST,
            object_type=ObjectType.POST,
            object_id=post.id,
            visibility=activity_visibility,
        )

        await self.db.commit()
        await self.db.refresh(post)
        await event_bus.publish(events.post_created(str(post.id), str(user.id)))
        await self._publish_mention_events(MentionTarget.POST, post.id)
        return await self._post_response(post, user)

    async def get_post(self, post_id: uuid.UUID, viewer) -> PostResponse:
        post = await self._visible_post(post_id, viewer)
        return await self._post_response(post, viewer)

    async def update_post(
        self, user: User, post_id: uuid.UUID, *, fields: dict
    ) -> PostResponse:
        post = await self.repo.get_post(post_id)
        if post is None or post.deleted_at is not None:
            raise PostNotFoundError()
        if post.author_id != user.id:
            raise PostForbiddenError()

        if "type" in fields and fields["type"] == PostType.BOOK_SHARE and post.book_id is None:
            raise BookShareRequiresBookError()
        for field in ("type", "body", "visibility"):
            if field in fields:
                setattr(post, field, fields[field])
        post.updated_at = utcnow()

        if "body" in fields:
            await self.repo.delete_mentions_by_content(
                MentionTarget.POST, post.id
            )
            await self._register_mentions(
                content_type=MentionTarget.POST,
                content_id=post.id,
                text=post.body,
                actor_id=user.id,
            )

        await self.db.commit()
        await self.db.refresh(post)
        await event_bus.publish(events.post_updated(str(post.id), str(user.id)))
        if "body" in fields:
            await self._publish_mention_events(MentionTarget.POST, post.id)
        return await self._post_response(post, user)

    async def delete_post(self, user: User, post_id: uuid.UUID) -> None:
        post = await self.repo.get_post(post_id)
        if post is None or post.deleted_at is not None:
            raise PostNotFoundError()
        if post.author_id != user.id:
            raise PostForbiddenError()

        await self.repo.soft_delete(post, utcnow())
        await self.db.commit()
        await event_bus.publish(events.post_deleted(str(post.id), str(user.id)))

    async def list_user_posts(
        self, handle: str, viewer, *, cursor: str | None, limit: int
    ) -> PostPage:
        author = await self.repo.get_user_by_handle(handle)
        if author is None or not author.is_active or author.deleted_at is not None:
            raise UserNotFoundError()

        viewer_id = viewer.id if viewer else None
        allowed: list[Visibility] | None
        if viewer_id is not None and viewer_id == author.id:
            allowed = None
        elif viewer_id is not None and (
            await self.repo.get_block_relation(viewer_id, author.id)
        ) is not None:
            allowed = []
        else:
            allowed = [Visibility.PUBLIC]
            if viewer_id is not None and (
                await self.repo.get_follow(viewer_id, author.id)
            ) is not None:
                allowed.append(Visibility.FOLLOWERS)

        after = decode_cursor(cursor)
        posts = await self.repo.list_posts_by_author(
            author.id, allowed=allowed, limit=limit + 1, after=after
        )
        return await self._paginate_posts(posts, viewer, limit)

    # ---------- Comments ----------

    async def create_comment(
        self, user: User, post_id: uuid.UUID, *, body: str, parent_id: uuid.UUID | None
    ) -> CommentResponse:
        await self._visible_post(post_id, user)
        parent = None
        if parent_id is not None:
            parent = await self.repo.get_comment(parent_id)
            if parent is None or parent.deleted_at is not None:
                raise CommentNotFoundError()
            if parent.post_id != post_id:
                raise CommentNotFoundError()
            if parent.parent_id is not None:
                raise NestedCommentsNotAllowedError()

        comment = await self.repo.create_comment(
            post_id=post_id,
            parent_id=parent_id,
            author_id=user.id,
            body=body,
        )
        await self._register_mentions(
            content_type=MentionTarget.COMMENT,
            content_id=comment.id,
            text=body,
            actor_id=user.id,
        )
        activity_visibility = await self._activity_visibility(user.id)
        await self.repo.create_activity(
            actor_id=user.id,
            verb=ActivityVerb.COMMENTED,
            object_type=ObjectType.COMMENT,
            object_id=comment.id,
            target_type="POST",
            target_id=post_id,
            visibility=activity_visibility,
        )

        await self.db.commit()
        await self.db.refresh(comment)
        await event_bus.publish(
            events.comment_created(str(comment.id), str(post_id), str(user.id))
        )
        await self._publish_mention_events(MentionTarget.COMMENT, comment.id)
        return await self._comment_response(comment, user)

    async def list_comments(
        self, post_id: uuid.UUID, viewer, *, cursor: str | None, limit: int
    ) -> CommentPage:
        await self._visible_post(post_id, viewer)
        after = decode_cursor(cursor)
        comments = await self.repo.list_comments(
            post_id, limit=limit + 1, after=after
        )
        has_more = len(comments) > limit
        page = comments[:limit]
        next_cursor = None
        if has_more and page:
            last = page[-1]
            next_cursor = encode_cursor(last.created_at, last.id)
        items = await self._comment_responses(page, viewer)
        return CommentPage(items=items, next=next_cursor)

    async def delete_comment(self, user: User, post_id: uuid.UUID, comment_id: uuid.UUID) -> None:
        comment = await self.repo.get_comment(comment_id)
        if comment is None or comment.deleted_at is not None:
            raise CommentNotFoundError()
        if comment.post_id != post_id:
            raise CommentNotFoundError()
        post = await self.repo.get_post(post_id)
        if comment.author_id != user.id and (
            post is None or post.author_id != user.id
        ):
            raise CommentForbiddenError()

        await self.repo.soft_delete_comment(comment, utcnow())
        await self.db.commit()
        await event_bus.publish(events.comment_deleted(str(comment_id), str(post_id)))

    # ---------- Likes ----------

    async def like_post(self, user: User, post_id: uuid.UUID) -> PostLikeResponse:
        await self._visible_post(post_id, user)
        like = await self.repo.get_post_like(user.id, post_id)
        created = False
        if like is None:
            like = await self.repo.create_post_like(user.id, post_id)
            created = True
            try:
                await self.db.commit()
            except IntegrityError:
                # Carrera: otro request creó el like. Idempotente, no 500.
                await self.db.rollback()
                like = await self.repo.get_post_like(user.id, post_id)
                created = False
                if like is None:
                    raise
            await self.db.refresh(like)
            if created:
                await event_bus.publish(events.post_liked(str(post_id), str(user.id)))
        return PostLikeResponse(
            id=str(like.id),
            post_id=str(post_id),
            created_at=like.created_at,
        )

    async def unlike_post(self, user: User, post_id: uuid.UUID) -> None:
        like = await self.repo.get_post_like(user.id, post_id)
        if like is None:
            return
        await self.repo.delete_post_like(like)
        await self.db.commit()
        await event_bus.publish(events.post_unliked(str(post_id), str(user.id)))

    async def like_comment(self, user: User, comment_id: uuid.UUID) -> CommentLikeResponse:
        comment = await self._visible_comment(comment_id, user)
        like = await self.repo.get_comment_like(user.id, comment_id)
        created = False
        if like is None:
            like = await self.repo.create_comment_like(user.id, comment_id)
            created = True
            try:
                await self.db.commit()
            except IntegrityError:
                # Carrera: otro request creó el like. Idempotente, no 500.
                await self.db.rollback()
                like = await self.repo.get_comment_like(user.id, comment_id)
                created = False
                if like is None:
                    raise
            await self.db.refresh(like)
            if created:
                await event_bus.publish(events.comment_liked(str(comment_id), str(user.id)))
        return CommentLikeResponse(
            id=str(like.id),
            comment_id=str(comment_id),
            created_at=like.created_at,
        )

    async def unlike_comment(self, user: User, comment_id: uuid.UUID) -> None:
        like = await self.repo.get_comment_like(user.id, comment_id)
        if like is None:
            return
        await self.repo.delete_comment_like(like)
        await self.db.commit()
        await event_bus.publish(events.comment_unliked(str(comment_id), str(user.id)))

    # ---------- Visibilidad ----------

    async def _visible_post(self, post_id: uuid.UUID, viewer) -> Post:
        post = await self.repo.get_post(post_id)
        if post is None or post.deleted_at is not None:
            raise PostNotFoundError()
        author = await self.repo.get_user(post.author_id)
        if author is None or not author.is_active or author.deleted_at is not None:
            raise PostNotFoundError()
        if viewer is not None and viewer.id == post.author_id:
            return post

        viewer_id = viewer.id if viewer else None
        is_blocked = False
        if viewer_id is not None:
            is_blocked = (
                await self.repo.get_block_relation(viewer_id, post.author_id)
            ) is not None
        if is_blocked:
            raise PostNotFoundError()

        is_follower = False
        if viewer_id is not None:
            is_follower = (
                await self.repo.get_follow(viewer_id, post.author_id)
            ) is not None
        visible = is_visible(
            post.visibility,
            viewer_id=viewer_id,
            author_id=post.author_id,
            is_follower=is_follower,
            is_blocked=False,
            author_active=author.is_active and author.deleted_at is None,
        )
        if not visible:
            raise PostPrivateError()
        return post

    async def _visible_comment(self, comment_id: uuid.UUID, viewer) -> Comment:
        comment = await self.repo.get_comment(comment_id)
        if comment is None or comment.deleted_at is not None:
            raise CommentNotFoundError()
        await self._visible_post(comment.post_id, viewer)
        return comment

    # ---------- Mentions ----------

    async def _register_mentions(
        self,
        *,
        content_type: MentionTarget,
        content_id: uuid.UUID,
        text: str,
        actor_id: uuid.UUID,
    ) -> None:
        usernames = _extract_usernames(text)
        if not usernames:
            return
        users = await self.repo.get_users_by_usernames(list(usernames))
        for user in users:
            if user.id == actor_id:
                continue
            await self.repo.create_mention(
                content_type=content_type,
                content_id=content_id,
                mentioned_user_id=user.id,
            )

    async def _publish_mention_events(
        self, content_type: MentionTarget, content_id: uuid.UUID
    ) -> None:
        from app.posts.models import Mention

        from sqlmodel import select

        stmt = select(Mention).where(
            Mention.content_type == content_type, Mention.content_id == content_id
        )
        mentions = (await self.db.exec(stmt)).all()
        for mention in mentions:
            await event_bus.publish(
                events.mention_detected(
                    content_type.value, str(content_id), str(mention.mentioned_user_id)
                )
            )

    async def _activity_visibility(self, user_id: uuid.UUID) -> Visibility:
        from app.profiles.models import PrivacySetting

        from sqlmodel import select

        stmt = select(PrivacySetting).where(PrivacySetting.user_id == user_id)
        privacy = (await self.db.exec(stmt)).first()
        return privacy.activity_visibility if privacy else Visibility.PUBLIC

    # ---------- Respuestas ----------

    async def _paginate_posts(
        self, posts: list[Post], viewer, limit: int
    ) -> PostPage:
        has_more = len(posts) > limit
        page = posts[:limit]
        next_cursor = None
        if has_more and page:
            last = page[-1]
            next_cursor = encode_cursor(last.created_at, last.id)
        items = await self._post_responses(page, viewer)
        return PostPage(items=items, next=next_cursor)

    async def _post_response(self, post: Post, viewer) -> PostResponse:
        items = await self._post_responses([post], viewer)
        return items[0]

    async def _post_responses(self, posts: list[Post], viewer) -> list[PostResponse]:
        if not posts:
            return []

        author_ids = list({p.author_id for p in posts})
        book_ids = [p.book_id for p in posts if p.book_id]
        post_ids = [p.id for p in posts]

        users = {u.id: u for u in await self.repo.get_users_by_ids(author_ids)}
        profiles = {
            p.user_id: p for p in await self.repo.get_profiles_by_user_ids(author_ids)
        }
        books = {b.id: b for b in await self.repo.get_books_by_ids(book_ids)}
        media_map = await self.repo.get_media_by_post_ids(post_ids)
        like_counts = await self.repo.count_likes_by_post_ids(post_ids)
        comment_counts = await self.repo.count_comments_by_post_ids(post_ids)

        viewer_id = viewer.id if viewer else None
        liked_ids: set[uuid.UUID] = set()
        if viewer_id is not None:
            liked_ids = await self.repo.get_post_like_ids_for_user(viewer_id, post_ids)

        result: list[PostResponse] = []
        for post in posts:
            author = users.get(post.author_id)
            if author is None:
                continue
            profile = profiles.get(post.author_id)
            book = books.get(post.book_id) if post.book_id else None
            result.append(
                PostResponse(
                    id=str(post.id),
                    type=post.type,
                    body=post.body,
                    visibility=post.visibility,
                    book=PostBookBrief(
                        id=book.id,
                        title=book.title,
                        author=book.author,
                        thumbnail=book.thumbnail,
                    ) if book else None,
                    review_id=str(post.review_id) if post.review_id else None,
                    media=[
                        PostMediaBrief(
                            id=str(m.id),
                            media_type=m.media_type,
                            url=m.url,
                            position=m.position,
                        )
                        for m in media_map.get(post.id, [])
                    ],
                    like_count=like_counts.get(post.id, 0),
                    comment_count=comment_counts.get(post.id, 0),
                    is_liked=post.id in liked_ids,
                    created_at=post.created_at,
                    updated_at=post.updated_at,
                    author=UserBrief(
                        id=str(author.id),
                        username=author.username,
                        display_name=profile.display_name if profile else None,
                        avatar_url=profile.avatar_url if profile else None,
                    ),
                )
            )
        return result

    async def _comment_response(self, comment: Comment, viewer) -> CommentResponse:
        items = await self._comment_responses([comment], viewer)
        return items[0]

    async def _comment_responses(
        self, comments: list[Comment], viewer
    ) -> list[CommentResponse]:
        if not comments:
            return []

        author_ids = list({c.author_id for c in comments})
        comment_ids = [c.id for c in comments]

        users = {u.id: u for u in await self.repo.get_users_by_ids(author_ids)}
        profiles = {
            p.user_id: p for p in await self.repo.get_profiles_by_user_ids(author_ids)
        }
        like_counts = await self.repo.count_comment_likes_by_comment_ids(comment_ids)

        viewer_id = viewer.id if viewer else None
        liked_ids: set[uuid.UUID] = set()
        if viewer_id is not None:
            liked_ids = await self.repo.get_comment_like_ids_for_user(
                viewer_id, comment_ids
            )

        result: list[CommentResponse] = []
        for comment in comments:
            author = users.get(comment.author_id)
            if author is None:
                continue
            profile = profiles.get(comment.author_id)
            result.append(
                CommentResponse(
                    id=str(comment.id),
                    post_id=str(comment.post_id),
                    parent_id=str(comment.parent_id) if comment.parent_id else None,
                    body=comment.body,
                    like_count=like_counts.get(comment.id, 0),
                    is_liked=comment.id in liked_ids,
                    created_at=comment.created_at,
                    author=UserBrief(
                        id=str(author.id),
                        username=author.username,
                        display_name=profile.display_name if profile else None,
                        avatar_url=profile.avatar_url if profile else None,
                    ),
                )
            )
        return result
