"""Endpoints del módulo favorites (router fino, sin lógica).

Rutas bajo `/me`:
- `/me/catalogs`: catálogos que usa el usuario (CRUD).
- `/me/favorites`: establecimientos favoritos (CRUD).
- `/me/home`: estantes para la pantalla de inicio.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status

from app.auth.dependencies import get_current_user
from app.auth.models import User
from app.enums import EstablishmentTypeEnum
from app.favorites.dependencies import get_favorites_service
from app.favorites.schemas import (
    CatalogResponse,
    EstablishmentResponse,
    HomeResponse,
    LibrariesResponse,
)
from app.favorites.service import FavoritesService
from app.shelves.schemas import BookBrief

router = APIRouter()


@router.get(
    "/me/catalogs",
    response_model=list[CatalogResponse],
    summary="Catálogos que usa mi usuario",
)
async def list_my_catalogs(
    user: User = Depends(get_current_user),
    service: FavoritesService = Depends(get_favorites_service),
) -> list[CatalogResponse]:
    return await service.list_catalogs(user)


@router.post(
    "/me/catalogs/{catalog_id}",
    response_model=CatalogResponse,
    status_code=201,
    summary="Añadir un catálogo a mi usuario",
)
async def add_my_catalog(
    catalog_id: int,
    user: User = Depends(get_current_user),
    service: FavoritesService = Depends(get_favorites_service),
) -> CatalogResponse:
    try:
        return await service.add_catalog(user, catalog_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.delete(
    "/me/catalogs/{catalog_id}",
    status_code=204,
    summary="Quitar un catálogo de mi usuario",
)
async def remove_my_catalog(
    catalog_id: int,
    user: User = Depends(get_current_user),
    service: FavoritesService = Depends(get_favorites_service),
) -> None:
    await service.remove_catalog(user, catalog_id)


@router.get(
    "/me/favorites",
    response_model=list[EstablishmentResponse],
    summary="Mis establecimientos favoritos (bibliotecas y librerías)",
)
async def list_my_favorites(
    type: EstablishmentTypeEnum | None = None,
    user: User = Depends(get_current_user),
    service: FavoritesService = Depends(get_favorites_service),
) -> list[EstablishmentResponse]:
    return await service.list_favorites(user, type=type)


@router.get(
    "/me/establishments",
    response_model=list[EstablishmentResponse],
    summary="Todos los establecimientos del tipo dado, con su estado de favorito",
)
async def list_my_establishments(
    type: EstablishmentTypeEnum | None = None,
    user: User = Depends(get_current_user),
    service: FavoritesService = Depends(get_favorites_service),
) -> list[EstablishmentResponse]:
    return await service.list_establishments(user, type=type)


@router.post(
    "/me/favorites/{establishment_id}",
    response_model=EstablishmentResponse,
    status_code=201,
    summary="Marcar un establecimiento como favorito",
)
async def add_my_favorite(
    establishment_id: int,
    user: User = Depends(get_current_user),
    service: FavoritesService = Depends(get_favorites_service),
) -> EstablishmentResponse:
    try:
        return await service.add_favorite(user, establishment_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.delete(
    "/me/favorites/{establishment_id}",
    status_code=204,
    summary="Quitar un establecimiento de mis favoritos",
)
async def remove_my_favorite(
    establishment_id: int,
    user: User = Depends(get_current_user),
    service: FavoritesService = Depends(get_favorites_service),
) -> None:
    await service.remove_favorite(user, establishment_id)


@router.get(
    "/me/home",
    response_model=HomeResponse,
    summary="Estantes de la pantalla de inicio",
)
async def get_my_home(
    user: User = Depends(get_current_user),
    service: FavoritesService = Depends(get_favorites_service),
) -> HomeResponse:
    return await service.get_home(user)


@router.get(
    "/me/libraries",
    response_model=LibrariesResponse,
    summary="Mis bibliotecas favoritas con sus libros disponibles",
)
async def get_my_libraries(
    user: User = Depends(get_current_user),
    service: FavoritesService = Depends(get_favorites_service),
) -> LibrariesResponse:
    return await service.get_libraries(user)


@router.post(
    "/me/search-history/{book_id}",
    status_code=204,
    summary="Registrar un click sobre un libro de búsqueda",
)
async def record_search_history_click(
    book_id: int,
    user: User = Depends(get_current_user),
    service: FavoritesService = Depends(get_favorites_service),
) -> None:
    await service.record_search_click(user, book_id)


@router.get(
    "/me/search-history/recent",
    response_model=list[BookBrief],
    summary="Búsquedas recientes (últimos libros clicados, máx. 5)",
)
async def get_recent_search_history(
    user: User = Depends(get_current_user),
    service: FavoritesService = Depends(get_favorites_service),
) -> list[BookBrief]:
    return await service.list_recent_searches(user)


@router.delete(
    "/me/search-history",
    status_code=204,
    summary="Borrar el historial de búsquedas del usuario",
)
async def clear_search_history(
    user: User = Depends(get_current_user),
    service: FavoritesService = Depends(get_favorites_service),
) -> None:
    await service.clear_search_history(user)
