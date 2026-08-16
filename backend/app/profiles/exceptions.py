"""Errores de dominio del módulo profiles."""

from fastapi import status

from app.core.exceptions import DomainError


class ProfileNotFoundError(DomainError):
    status_code = status.HTTP_404_NOT_FOUND
    code = "profile_not_found"
    message = "Profile not found."


class ProfilePrivateError(DomainError):
    status_code = status.HTTP_403_FORBIDDEN
    code = "profile_private"
    message = "This profile is private."
