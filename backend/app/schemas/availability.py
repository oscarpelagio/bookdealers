"""Esquemes de validació per a l'API."""

from sqlmodel import SQLModel, Field

from app.enums import EstablishmentTypeEnum

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
