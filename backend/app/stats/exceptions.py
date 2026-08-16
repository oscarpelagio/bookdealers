"""Errores de dominio del módulo stats (FASE 9)."""

from fastapi import status

from app.core.exceptions import DomainError


class StatsPrivateError(DomainError):
    status_code = status.HTTP_403_FORBIDDEN
    code = "stats_private"
    message = "This user's reading stats are not visible to you."


class UserStatsNotFoundError(DomainError):
    status_code = status.HTTP_404_NOT_FOUND
    code = "stats_user_not_found"
    message = "User not found."