"""Endpoints del módulo social (routers finos, sin lógica).

Rutas (todas bajo `/users/{handle}/...` para el grafo social, salvo el
reporte global):
- `POST/DELETE /users/{handle}/follow` · `GET /users/{handle}/is-following`
- `GET /users/{handle}/followers` · `GET /users/{handle}/following`
- `POST/DELETE /users/{handle}/block` · `/mute`
- `GET /users/{handle}/activity` (stream público, privacy-aware)
- `POST /reports` (moderación)
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query

from app.auth.dependencies import get_current_user
from app.auth.models import User
from app.social.dependencies import (
    get_optional_current_user,
    get_social_service,
)
from app.social.schemas import (
    ActivityPage,
    FollowResponse,
    FollowStatusResponse,
    ReportCreate,
    ReportResponse,
    UserPage,
)
from app.social.service import SocialService

router = APIRouter()


@router.post(
    "/users/{handle}/follow",
    response_model=FollowResponse,
    status_code=201,
    summary="Seguir a un usuario",
)
async def follow_user(
    handle: str,
    user: User = Depends(get_current_user),
    service: SocialService = Depends(get_social_service),
) -> FollowResponse:
    return await service.follow(user, handle)


@router.delete(
    "/users/{handle}/follow",
    status_code=204,
    summary="Dejar de seguir a un usuario",
)
async def unfollow_user(
    handle: str,
    user: User = Depends(get_current_user),
    service: SocialService = Depends(get_social_service),
) -> None:
    await service.unfollow(user, handle)


@router.get(
    "/users/{handle}/is-following",
    response_model=FollowStatusResponse,
    summary="¿Sigo a este usuario?",
)
async def is_following(
    handle: str,
    user: User = Depends(get_current_user),
    service: SocialService = Depends(get_social_service),
) -> FollowStatusResponse:
    return FollowStatusResponse(is_following=await service.is_following(user, handle))


@router.get(
    "/users/{handle}/followers",
    response_model=UserPage,
    summary="Lista de seguidores de un usuario (paginado por cursor)",
)
async def list_followers(
    handle: str,
    cursor: str | None = Query(default=None),
    limit: int = Query(default=20, ge=1, le=100),
    viewer: User | None = Depends(get_optional_current_user),
    service: SocialService = Depends(get_social_service),
) -> UserPage:
    return await service.followers(handle, viewer, cursor=cursor, limit=limit)


@router.get(
    "/users/{handle}/following",
    response_model=UserPage,
    summary="Usuarios a los que sigue (paginado por cursor)",
)
async def list_following(
    handle: str,
    cursor: str | None = Query(default=None),
    limit: int = Query(default=20, ge=1, le=100),
    viewer: User | None = Depends(get_optional_current_user),
    service: SocialService = Depends(get_social_service),
) -> UserPage:
    return await service.following(handle, viewer, cursor=cursor, limit=limit)


@router.post(
    "/users/{handle}/block",
    status_code=204,
    summary="Bloquear a un usuario (borra follows a dos sentidos)",
)
async def block_user(
    handle: str,
    user: User = Depends(get_current_user),
    service: SocialService = Depends(get_social_service),
) -> None:
    await service.block(user, handle)


@router.delete(
    "/users/{handle}/block",
    status_code=204,
    summary="Desbloquear a un usuario",
)
async def unblock_user(
    handle: str,
    user: User = Depends(get_current_user),
    service: SocialService = Depends(get_social_service),
) -> None:
    await service.unblock(user, handle)


@router.post(
    "/users/{handle}/mute",
    status_code=204,
    summary="Silenciar a un usuario (solo feed, F5)",
)
async def mute_user(
    handle: str,
    user: User = Depends(get_current_user),
    service: SocialService = Depends(get_social_service),
) -> None:
    await service.mute(user, handle)


@router.delete(
    "/users/{handle}/mute",
    status_code=204,
    summary="Dejar de silenciar a un usuario",
)
async def unmute_user(
    handle: str,
    user: User = Depends(get_current_user),
    service: SocialService = Depends(get_social_service),
) -> None:
    await service.unmute(user, handle)


@router.get(
    "/users/{handle}/activity",
    response_model=ActivityPage,
    summary="Stream público de actividad de un usuario (privacy-aware)",
)
async def list_user_activity(
    handle: str,
    cursor: str | None = Query(default=None),
    limit: int = Query(default=20, ge=1, le=100),
    viewer: User | None = Depends(get_optional_current_user),
    service: SocialService = Depends(get_social_service),
) -> ActivityPage:
    return await service.user_activity(handle, viewer, cursor=cursor, limit=limit)


@router.post(
    "/reports",
    response_model=ReportResponse,
    status_code=201,
    summary="Reportar un contenido (target polimórfico)",
)
async def create_report(
    payload: ReportCreate,
    user: User = Depends(get_current_user),
    service: SocialService = Depends(get_social_service),
) -> ReportResponse:
    return await service.create_report(
        user,
        target_type=payload.target_type,
        target_id=payload.target_id,
        reason=payload.reason,
        details=payload.details,
    )