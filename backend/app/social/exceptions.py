"""Errores de dominio del módulo social (FASE 4)."""

from fastapi import status

from app.core.exceptions import DomainError


class CannotFollowSelfError(DomainError):
    status_code = status.HTTP_400_BAD_REQUEST
    code = "cannot_follow_self"
    message = "You cannot follow yourself."


class CannotBlockSelfError(DomainError):
    status_code = status.HTTP_400_BAD_REQUEST
    code = "cannot_block_self"
    message = "You cannot block yourself."


class CannotMuteSelfError(DomainError):
    status_code = status.HTTP_400_BAD_REQUEST
    code = "cannot_mute_self"
    message = "You cannot mute yourself."


class UserNotFoundError(DomainError):
    status_code = status.HTTP_404_NOT_FOUND
    code = "user_not_found"
    message = "User not found."


class AlreadyBlockedError(DomainError):
    status_code = status.HTTP_409_CONFLICT
    code = "already_blocked"
    message = "You already blocked this user."


class CannotFollowBlockedUserError(DomainError):
    status_code = status.HTTP_403_FORBIDDEN
    code = "cannot_follow_blocked"
    message = "You cannot follow a user involved in a block."


class FollowsNotAllowedError(DomainError):
    status_code = status.HTTP_403_FORBIDDEN
    code = "follows_not_allowed"
    message = "This user does not accept follows."


class ActivityNotFoundError(DomainError):
    status_code = status.HTTP_404_NOT_FOUND
    code = "activity_not_found"
    message = "Activity not found."