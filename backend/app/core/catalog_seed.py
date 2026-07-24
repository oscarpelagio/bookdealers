import json
from pathlib import Path
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from app.models import Catalog
from app.core.db import async_engine 

async def seed_catalogs():
    """Lee el JSON de catálogos y hace un upsert en la base de datos."""
    json_path = Path(__file__).parent / "catalog_seed.json"
    
    if not json_path.exists():
        print(f"No se ha encontrado el archivo {json_path}")
        return

    print("Archivo JSON encontrado. Leyendo catálogos...")
    with open(json_path, "r", encoding="utf-8") as f:
        catalogs_data = json.load(f)

    async with AsyncSession(async_engine) as session:
        for cat_data in catalogs_data:
            statement = select(Catalog).where(Catalog.name == cat_data["name"])
            result = await session.exec(statement)
            existing_catalog = result.first()

            if existing_catalog:
                existing_catalog.service = cat_data["service"]
                existing_catalog.url = cat_data["url"]
                existing_catalog.port = cat_data.get("port")
                existing_catalog.base = cat_data.get("base")
                print(f"Actualizado catálogo existente: {cat_data['name']}")
            else:
                new_catalog = Catalog(**cat_data)
                session.add(new_catalog)
                print(f"Añadido NUEVO catálogo: {cat_data['name']}")
        
        await session.commit()
        print("Seeding de catálogos terminado con éxito")
