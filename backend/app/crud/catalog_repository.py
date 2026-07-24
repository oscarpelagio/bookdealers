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
