"""Errores de dominio del módulo reviews."""

from fastapi import status

from app.core.exceptions import DomainError


class ReviewNotFoundError(DomainError):
    status_code = status.HTTP_404_NOT_FOUND
    code = "review_not_found"
    message = "Review not found."


class ReviewAlreadyExistsError(DomainError):
    status_code = status.HTTP_409_CONFLICT
    code = "review_already_exists"
    message = "You already reviewed this book."


class RatingRequiredError(DomainError):
    status_code = status.HTTP_422_UNPROCESSABLE_CONTENT
    code = "rating_required"
    message = "A score between 1 and 5 is required to write a review."


class UserBookRequiredError(DomainError):
    status_code = status.HTTP_422_UNPROCESSABLE_CONTENT
    code = "user_book_required"
    message = "Add this book to your library before writing a review."


class RatingOutOfRangeError(DomainError):
    status_code = status.HTTP_422_UNPROCESSABLE_CONTENT
    code = "rating_out_of_range"
    message = "Score must be between 1 and 5."


class CannotLikeOwnReviewError(DomainError):
    status_code = status.HTTP_400_BAD_REQUEST
    code = "cannot_like_own_review"
    message = "You cannot like your own review."


class ReviewPrivateError(DomainError):
    status_code = status.HTTP_403_FORBIDDEN
    code = "review_private"
    message = "This user's reviews are not visible to you."
