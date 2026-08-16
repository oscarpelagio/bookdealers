"""Errores de dominio del módulo posts (FASE 6)."""

from fastapi import status

from app.core.exceptions import DomainError


class PostNotFoundError(DomainError):
    status_code = status.HTTP_404_NOT_FOUND
    code = "post_not_found"
    message = "Post not found."


class PostPrivateError(DomainError):
    status_code = status.HTTP_403_FORBIDDEN
    code = "post_private"
    message = "This post is not visible to you."


class PostForbiddenError(DomainError):
    status_code = status.HTTP_403_FORBIDDEN
    code = "post_forbidden"
    message = "You do not have permission to modify this post."


class BookShareRequiresBookError(DomainError):
    status_code = status.HTTP_422_UNPROCESSABLE_CONTENT
    code = "book_share_requires_book"
    message = "A BOOK_SHARE post must include a book_id."


class ReviewNotFoundError(DomainError):
    status_code = status.HTTP_404_NOT_FOUND
    code = "review_not_found"
    message = "Review not found."


class CommentNotFoundError(DomainError):
    status_code = status.HTTP_404_NOT_FOUND
    code = "comment_not_found"
    message = "Comment not found."


class CommentForbiddenError(DomainError):
    status_code = status.HTTP_403_FORBIDDEN
    code = "comment_forbidden"
    message = "You do not have permission to delete this comment."


class NestedCommentsNotAllowedError(DomainError):
    status_code = status.HTTP_422_UNPROCESSABLE_CONTENT
    code = "nested_comments_not_allowed"
    message = "Comments only support a single level of nesting."
