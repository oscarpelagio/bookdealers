"""Errores de dominio del módulo notifications (FASE 8)."""

from fastapi import status

from app.core.exceptions import DomainError


class NotificationNotFoundError(DomainError):
    status_code = status.HTTP_404_NOT_FOUND
    code = "notification_not_found"
    message = "Notification not found."


class InvalidNotificationSettingsError(DomainError):
    status_code = status.HTTP_422_UNPROCESSABLE_CONTENT
    code = "invalid_notification_settings"
    message = "Invalid notification settings."
