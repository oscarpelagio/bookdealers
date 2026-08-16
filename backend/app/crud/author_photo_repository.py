"""Repositori per a la cache de fotos d'autors."""

from datetime import datetime

from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from app.models import AuthorPhoto


class AuthorPhotoRepository:
    """Operacions CRUD sobre `author_photos`."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_photo(self, author_key: str) -> AuthorPhoto | None:
        statement = select(AuthorPhoto).where(AuthorPhoto.author_key == author_key)
        result = await self.db.exec(statement)
        return result.first()

    async def set_photo(
        self,
        author_key: str,
        photo_url: str | None,
        source: str | None,
        status: str,
    ) -> AuthorPhoto:
        photo = await self.get_photo(author_key)
        if photo is not None:
            photo.photo_url = photo_url
            photo.source = source
            photo.status = status
            photo.fetched_at = datetime.utcnow()
        else:
            photo = AuthorPhoto(
                author_key=author_key,
                photo_url=photo_url,
                source=source,
                status=status,
                fetched_at=datetime.utcnow(),
            )
            self.db.add(photo)
        await self.db.commit()
        await self.db.refresh(photo)
        return photo