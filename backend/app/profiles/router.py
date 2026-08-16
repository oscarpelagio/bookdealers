"""Endpoints del módulo profiles (routers finos, sin lógica).

Orden importante: las rutas `/me/*` se registran ANTES que `/{handle}`
para que FastAPI no las capture con el path param.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends

from app.auth.dependencies import get_current_user
from app.auth.models import User
from app.profiles.dependencies import (
    get_optional_current_user,
    get_profile_service,
)
from app.profiles.schemas import (
    PreferenceResponse,
    PreferenceUpdate,
    PrivacyResponse,
    PrivacyUpdate,
    ProfileMeResponse,
    ProfilePublicResponse,
    ProfileUpdate,
    ReadingGoalCreate,
    ReadingGoalResponse,
)
from app.profiles.service import ProfileService

router = APIRouter()


def _public_response(user: User, profile, is_following: bool) -> ProfilePublicResponse:
    return ProfilePublicResponse(
        id=str(profile.id),
        username=user.username,
        display_name=profile.display_name or user.full_name,
        bio=profile.bio,
        location=profile.location,
        website=profile.website,
        avatar_url=profile.avatar_url,
        cover_url=profile.cover_url,
        joined_at=user.created_at,
        is_following=is_following,
    )


def _preference_response(pref) -> PreferenceResponse:
    return PreferenceResponse(
        language=pref.language,
        default_review_visibility=pref.default_review_visibility,
        reading_tracking_enabled=pref.reading_tracking_enabled,
        content_languages=pref.content_languages,
    )


def _privacy_response(privacy) -> PrivacyResponse:
    return PrivacyResponse(
        profile_visibility=privacy.profile_visibility,
        library_visibility=privacy.library_visibility,
        reviews_visibility=privacy.reviews_visibility,
        lists_visibility=privacy.lists_visibility,
        activity_visibility=privacy.activity_visibility,
        allow_follows=privacy.allow_follows,
        show_reading_progress=privacy.show_reading_progress,
        block_anonymous=privacy.block_anonymous,
    )


def _goal_response(goal) -> ReadingGoalResponse:
    return ReadingGoalResponse(
        id=str(goal.id),
        year=goal.year,
        books_goal=goal.books_goal,
        pages_goal=goal.pages_goal,
        created_at=goal.created_at,
        updated_at=goal.updated_at,
    )


def _me_response(user: User, profile, pref, privacy) -> ProfileMeResponse:
    base = _public_response(user, profile, is_following=False).model_dump()
    return ProfileMeResponse(
        **base,
        preferences=_preference_response(pref),
        privacy=_privacy_response(privacy),
    )


@router.get(
    "/me",
    response_model=ProfileMeResponse,
    summary="Mi perfil público (con preferencias y privacidad)",
)
async def get_me(
    user: User = Depends(get_current_user),
    service: ProfileService = Depends(get_profile_service),
) -> ProfileMeResponse:
    profile, pref, privacy = await service.get_own_profile(user)
    return _me_response(user, profile, pref, privacy)


@router.patch(
    "/me",
    response_model=ProfilePublicResponse,
    summary="Editar mi perfil",
)
async def update_me(
    payload: ProfileUpdate,
    user: User = Depends(get_current_user),
    service: ProfileService = Depends(get_profile_service),
) -> ProfilePublicResponse:
    profile = await service.update_own(
        user, fields=payload.model_dump(exclude_unset=True)
    )
    return _public_response(user, profile, is_following=False)


@router.get(
    "/me/privacy",
    response_model=PrivacyResponse,
    summary="Ver configuración de privacidad",
)
async def get_privacy(
    user: User = Depends(get_current_user),
    service: ProfileService = Depends(get_profile_service),
) -> PrivacyResponse:
    _, _, privacy = await service.get_own_profile(user)
    return _privacy_response(privacy)


@router.patch(
    "/me/privacy",
    response_model=PrivacyResponse,
    summary="Actualizar configuración de privacidad",
)
async def update_privacy(
    payload: PrivacyUpdate,
    user: User = Depends(get_current_user),
    service: ProfileService = Depends(get_profile_service),
) -> PrivacyResponse:
    privacy = await service.update_privacy(
        user, fields=payload.model_dump(exclude_unset=True)
    )
    return _privacy_response(privacy)


@router.get(
    "/me/preferences",
    response_model=PreferenceResponse,
    summary="Ver preferencias",
)
async def get_preferences(
    user: User = Depends(get_current_user),
    service: ProfileService = Depends(get_profile_service),
) -> PreferenceResponse:
    _, pref, _ = await service.get_own_profile(user)
    return _preference_response(pref)


@router.patch(
    "/me/preferences",
    response_model=PreferenceResponse,
    summary="Actualizar preferencias",
)
async def update_preferences(
    payload: PreferenceUpdate,
    user: User = Depends(get_current_user),
    service: ProfileService = Depends(get_profile_service),
) -> PreferenceResponse:
    pref = await service.update_preferences(
        user, fields=payload.model_dump(exclude_unset=True)
    )
    return _preference_response(pref)


@router.get(
    "/me/goals/{year}",
    response_model=ReadingGoalResponse | None,
    summary="Objetivo de lectura de un año",
)
async def get_goal(
    year: int,
    user: User = Depends(get_current_user),
    service: ProfileService = Depends(get_profile_service),
) -> ReadingGoalResponse | None:
    goal = await service.get_goal(user, year)
    if goal is None:
        return None
    return _goal_response(goal)


@router.put(
    "/me/goals/{year}",
    response_model=ReadingGoalResponse,
    summary="Crear o actualizar objetivo de lectura de un año",
)
async def upsert_goal(
    year: int,
    payload: ReadingGoalCreate,
    user: User = Depends(get_current_user),
    service: ProfileService = Depends(get_profile_service),
) -> ReadingGoalResponse:
    goal = await service.upsert_goal(
        user,
        year,
        books_goal=payload.books_goal,
        pages_goal=payload.pages_goal,
    )
    return _goal_response(goal)


@router.delete(
    "/me/goals/{year}",
    status_code=204,
    summary="Borrar objetivo de lectura de un año",
)
async def delete_goal(
    year: int,
    user: User = Depends(get_current_user),
    service: ProfileService = Depends(get_profile_service),
) -> None:
    await service.delete_goal(user, year)


@router.get(
    "/{handle}",
    response_model=ProfilePublicResponse,
    summary="Perfil público de un usuario",
)
async def get_public_profile(
    handle: str,
    viewer: User | None = Depends(get_optional_current_user),
    service: ProfileService = Depends(get_profile_service),
) -> ProfilePublicResponse:
    target_user, profile, is_following = await service.get_public(
        handle, viewer=viewer
    )
    return _public_response(target_user, profile, is_following)
