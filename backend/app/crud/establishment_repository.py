from sqlalchemy import insert
from sqlmodel.ext.asyncio.session import AsyncSession

from app.models import Establishment
    
class EstablishmentRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def insert_establishment(self, items: list[Establishment]): 
        values_to_insert = [{"name": name, "type": "library"} for name in items]
        
        statement = insert(Establishment).values(
            values_to_insert
            ).on_conflict_do_nothing(
            index_elements=["name"]
        )
        await self.db.exec(statement)
        await self.db.commit()
