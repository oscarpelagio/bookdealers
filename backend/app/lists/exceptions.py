"""Errores de dominio del módulo lists (FASE 7)."""

from fastapi import status

from app.core.exceptions import DomainError


class ListNotFoundError(DomainError):
    status_code = status.HTTP_404_NOT_FOUND
    code = "list_not_found"
    message = "List not found."


class ListPrivateError(DomainError):
    status_code = status.HTTP_403_FORBIDDEN
    code = "list_private"
    message = "This list is not visible to you."


class ListForbiddenError(DomainError):
    status_code = status.HTTP_403_FORBIDDEN
    code = "list_forbidden"
    message = "You do not have permission to modify this list."


class ListItemAlreadyExistsError(DomainError):
    status_code = status.HTTP_409_CONFLICT
    code = "list_item_already_exists"
    message = "This book is already in the list."


class ListItemNotFoundError(DomainError):
    status_code = status.HTTP_404_NOT_FOUND
    code = "list_item_not_found"
    message = "This book is not in the list."


class CollaboratorNotFoundError(DomainError):
    status_code = status.HTTP_404_NOT_FOUND
    code = "collaborator_not_found"
    message = "This user is not a collaborator of the list."


class CollaboratorAlreadyExistsError(DomainError):
    status_code = status.HTTP_409_CONFLICT
    code = "collaborator_already_exists"
    message = "This user is already a collaborator of the list."


class CannotCollaborateSelfError(DomainError):
    status_code = status.HTTP_400_BAD_REQUEST
    code = "cannot_collaborate_self"
    message = "You cannot add yourself as a collaborator of your own list."
