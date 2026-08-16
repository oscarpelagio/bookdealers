"""Seed de favoritos y catálogos del usuario admin.

Assigna a l'admin (admin@example.com):
- Catàlegs que usa: `aladi` (z3950) i `catalunya` (ebiblio).
- 7 biblioteques favorites del catàleg aladi a L'Hospitalet de Llobregat.
- 2 llibreries favorites (todostuslibros) a Barcelona (La Central i
  Finestres), eliminant les llibreries de l'Hospitalet que hi havia.

Idempotent: si el favorit/catàleg ja existeix no el duplica.

Uso (desde el contenedor del backend):
    docker compose exec back python scripts/seed_admin_favorites.py
"""

import asyncio

from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from app.auth.models import User
from app.core.db import async_session
from app.enums import EstablishmentTypeEnum
from app.favorites.models import UserCatalog, UserFavoriteEstablishment
from app.models import Catalog, Establishment

ADMIN_EMAIL = "admin@example.com"

# (catalog_name, service) que usará el admin.
ADMIN_CATALOGS = [
    ("aladi", "z3950"),
    ("catalunya", "ebiblio"),
]

# Nombres de bibliotecas físicas del catálogo aladi en L'Hospitalet de Llobregat.
FAVORITE_LIBRARIES = [
    "HOSPITALET DE LLOB.Bellvitge",
    "HOSPITALET DE LLOB.Can Sumarro",
    "HOSPITALET DE LLOB.J. Janés",
    "HOSPITALET DE LLOB.La Bòbila",
    "HOSPITALET DE LLOB.La Florida",
    "HOSPITALET DE LLOB.Plaça d'Europa",
    "HOSPITALET DE LLOB.Tecla Sala",
]

# Librerías favoritas (todostuslibros) en Barcelona.
FAVORITE_BOOKSHOPS = [
    "La Central calle Mallorca",
    "Llibreria Finestres",
]

# Librerías de l'Hospitalet que dejan de ser favoritas (se eliminan).
REMOVE_BOOKSHOPS = [
    "Espai Llavors",
    "Perutxo Llibres",
]


async def find_admin(db: AsyncSession) -> User:
    user = (await db.exec(select(User).where(User.email == ADMIN_EMAIL))).first()
    if user is None:
        raise SystemExit(f"No existe el usuario {ADMIN_EMAIL}")
    return user


async def seed_user_catalogs(db: AsyncSession, admin: User) -> None:
    for catalog_name, service in ADMIN_CATALOGS:
        catalog = (
            await db.exec(
                select(Catalog).where(
                    Catalog.name == catalog_name, Catalog.service == service
                )
            )
        ).first()
        if catalog is None:
            print(f"⚠ No existe el catálogo {catalog_name} ({service}), se omite")
            continue
        existing = (
            await db.exec(
                select(UserCatalog).where(
                    UserCatalog.user_id == admin.id,
                    UserCatalog.catalog_id == catalog.id,
                )
            )
        ).first()
        if existing:
            print(f"✓ Catálogo ya asignado: {catalog_name} ({service})")
            continue
        db.add(UserCatalog(user_id=admin.id, catalog_id=catalog.id))
        print(f"➕ Catálogo asignado: {catalog_name} ({service})")


async def seed_favorite_establishments(db: AsyncSession, admin: User, names: list[str], est_type: str) -> None:
    """Añade establecimientos favoritos por nombre y tipo (idempotente)."""
    for name in names:
        establishment = (
            await db.exec(
                select(Establishment).where(
                    Establishment.name == name,
                    Establishment.type == est_type,
                )
            )
        ).first()
        if establishment is None:
            print(f"⚠ No existe el establecimiento: {name} ({est_type})")
            continue
        existing = (
            await db.exec(
                select(UserFavoriteEstablishment).where(
                    UserFavoriteEstablishment.user_id == admin.id,
                    UserFavoriteEstablishment.establishment_id == establishment.id,
                )
            )
        ).first()
        if existing:
            print(f"✓ Favorito ya existe: {name} ({est_type})")
            continue
        db.add(
            UserFavoriteEstablishment(
                user_id=admin.id, establishment_id=establishment.id
            )
        )
        print(f"➕ Favorito: {name} ({est_type}) id={establishment.id}")


async def remove_favorite_establishments(db: AsyncSession, admin: User, names: list[str], est_type: str) -> None:
    """Elimina establecimientos favoritos por nombre y tipo (idempotente)."""
    for name in names:
        establishment = (
            await db.exec(
                select(Establishment).where(
                    Establishment.name == name,
                    Establishment.type == est_type,
                )
            )
        ).first()
        if establishment is None:
            print(f"⚠ No existe el establecimiento: {name} ({est_type})")
            continue
        fav = (
            await db.exec(
                select(UserFavoriteEstablishment).where(
                    UserFavoriteEstablishment.user_id == admin.id,
                    UserFavoriteEstablishment.establishment_id == establishment.id,
                )
            )
        ).first()
        if fav is None:
            print(f"✓ No era favorito: {name} ({est_type})")
            continue
        await db.delete(fav)
        print(f"➖ Favorito eliminado: {name} ({est_type}) id={establishment.id}")


async def main() -> None:
    async with async_session() as db:
        admin = await find_admin(db)
        await seed_user_catalogs(db, admin)
        await seed_favorite_establishments(db, admin, FAVORITE_LIBRARIES, EstablishmentTypeEnum.LIBRARY.value)
        await seed_favorite_establishments(db, admin, FAVORITE_BOOKSHOPS, EstablishmentTypeEnum.BOOK_SHOP.value)
        await remove_favorite_establishments(db, admin, REMOVE_BOOKSHOPS, EstablishmentTypeEnum.BOOK_SHOP.value)
        await db.commit()
        print("Seed de favoritos terminado.")


if __name__ == "__main__":
    asyncio.run(main())
