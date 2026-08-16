from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from app.models import Catalog


class CatalogRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_catalog(self, catalog: str) -> Catalog:
        statement = select(Catalog).where(
        Catalog.name == catalog)
        result = await self.db.exec(statement)
        return result.first()

    async def get_catalog_by_service(self, service: str) -> Catalog | None:
        statement = select(Catalog).where(Catalog.service == service)
        result = await self.db.exec(statement)
        return result.first()
