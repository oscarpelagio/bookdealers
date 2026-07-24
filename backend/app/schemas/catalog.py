from sqlmodel import SQLModel

class CatalogBase(SQLModel):
    service: str
    name: str
    url: str
    port: int | None
    base: str | None
