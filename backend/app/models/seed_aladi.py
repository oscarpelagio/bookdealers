"""Model per a la taula `seed_aladi`: volcat complet de biblioteques DIBA/Aladí
(`assets/biblioteques_diba.json`). El camp `dades` guarda l'element sencer en
JSONB perquè tots els camps siguin recuperables sense perdre cap informació."""

from datetime import datetime

from sqlalchemy import Column, DateTime, Float, String
from sqlalchemy.dialects.postgresql import JSONB
from sqlmodel import Field, SQLModel

from app.core.time import utcnow


class SeedAladi(SQLModel, table=True):
    """Una biblioteca del catàleg Aladí, tal com surt al volcat DIBA."""

    __tablename__ = "seed_aladi"

    id: int = Field(primary_key=True)
    punt_id: str = Field(
        sa_column=Column(String, nullable=False, unique=True)
    )
    nom: str | None = Field(default=None, sa_column=Column(String))
    municipi: str | None = Field(default=None, sa_column=Column(String))
    adreca: str | None = Field(default=None, sa_column=Column(String))
    codi_postal: str | None = Field(default=None, sa_column=Column(String))
    lat: float | None = Field(default=None, sa_column=Column(Float))
    lon: float | None = Field(default=None, sa_column=Column(Float))
    id_establishment: int | None = Field(
        default=None, foreign_key="establishments.id", index=True
    )
    dades: dict = Field(sa_column=Column(JSONB, nullable=False))
    created_at: datetime = Field(
        sa_column=Column(DateTime(timezone=True), nullable=False, default=utcnow)
    )
    updated_at: datetime = Field(
        sa_column=Column(DateTime(timezone=True), nullable=False, default=utcnow)
    )