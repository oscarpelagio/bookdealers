"""Esquemes de validació per a l'API."""

from sqlmodel import SQLModel, Field
from pydantic import field_validator

from app.enums import EstablishmentTypeEnum, AvailabilityStatusEnum

class AvailabilityBase(SQLModel):
    establishment_type: EstablishmentTypeEnum         
    establishment_name: str
    establishment_street: str | None = None
    establishment_postal_code: str | None = None
    establishment_city: str | None = None
    establishment_province: str | None = None
    catalog_id: int                    
    book_id: int
    book_language: str              
    book_status: str                               # <- status_enum
    queue: int | None = None
    link: str

    @field_validator("book_status", mode="before")
    @classmethod
    def _normalize_status(cls, value: object) -> object:
        """Normalitza l'estat a nom majúscula (AVAILABLE, BORROW...) per
       què la resposta sigui consistent vingui de l'adapter o de la base."""
        if isinstance(value, AvailabilityStatusEnum):
            return value.name
        if isinstance(value, str):
            return value.upper()
        return value
