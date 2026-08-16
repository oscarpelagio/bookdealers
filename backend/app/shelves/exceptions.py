"""Errores de dominio del módulo shelves."""

from fastapi import status

from app.core.exceptions import DomainError


class ShelfNotFoundError(DomainError):
    status_code = status.HTTP_404_NOT_FOUND
    code = "shelf_not_found"
    message = "Shelf not found."


class ShelfSlugConflictError(DomainError):
    status_code = status.HTTP_409_CONFLICT
    code = "shelf_name_conflict"
    message = "You already have a shelf with that name."


class ShelfKindNotCustomError(DomainError):
    status_code = status.HTTP_400_BAD_REQUEST
    code = "shelf_not_custom"
    message = "This operation is only valid on custom shelves."


class CannotModifyStatusShelfError(DomainError):
    status_code = status.HTTP_400_BAD_REQUEST
    code = "cannot_modify_status_shelf"
    message = "Status shelves only accept a description change."


class BookNotFoundError(DomainError):
    status_code = status.HTTP_404_NOT_FOUND
    code = "book_not_found"
    message = "Book not found."


class UserBookNotFoundError(DomainError):
    status_code = status.HTTP_404_NOT_FOUND
    code = "user_book_not_found"
    message = "This book is not in your library."


class StatusRequiredError(DomainError):
    status_code = status.HTTP_422_UNPROCESSABLE_CONTENT
    code = "status_required"
    message = "A reading status is required to add a book to your library."


class ProgressRequiredError(DomainError):
    status_code = status.HTTP_422_UNPROCESSABLE_CONTENT
    code = "progress_required"
    message = "Provide page or percent_read."


class ProgressExceedsBookError(DomainError):
    status_code = status.HTTP_422_UNPROCESSABLE_CONTENT
    code = "progress_exceeds_book"
    message = "The page cannot exceed the book page count."


class LibraryPrivateError(DomainError):
    status_code = status.HTTP_403_FORBIDDEN
    code = "library_private"
    message = "This user's library is private."
