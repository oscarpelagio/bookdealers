"""Servei de lookup unificat d'autors.

Estratègia:
1. Busca a la taula `author_source` pel nom normalitzat (variants).
2. Si l'autor està en diverses editorials, guanya la de `PREFERRED_SOURCES`.
3. Si no està en cap editorial, resol Penguin peresosament (el persisteix).
4. Si Penguin no ho té, resol Libros del Asteroide peresosament.
5. Si no hi ha res, `found=False` → el front cau a Wikimedia.
"""

from app.crud import AuthorSourceRelatedRepository, AuthorSourceRepository
from app.models import AuthorSource
from app.schemas import AuthorProfileLookup, PublisherRelatedItem
from app.services import AsteroideLazyService, PenguinLazyService
from app.utils import NormalizationUtils

# Ordre de preferència entre editorials quan un autor n'està en diverses.
# Ajustable: posa al davant la que vulguis que guanyi.
PREFERRED_SOURCES = ["anagrama", "penguin", "blackie", "transito", "asteroide"]


class AuthorProfileLookupService:

    def __init__(
        self,
        repo: AuthorSourceRepository,
        related_repo: AuthorSourceRelatedRepository,
        lazy: PenguinLazyService,
        asteroide_lazy: AsteroideLazyService,
    ) -> None:
        self.repo = repo
        self.related_repo = related_repo
        self.lazy = lazy
        self.asteroide_lazy = asteroide_lazy

    async def lookup(self, author: str) -> AuthorProfileLookup:
        author = (author or "").strip()
        if not author:
            return AuthorProfileLookup()

        variants = self._variants(author)
        for variant in variants:
            sources = await self.repo.sources_for(variant)
            if sources:
                return await self._to_lookup(self._pick(sources))

        row = await self.lazy.resolve(author)
        if row is not None:
            return await self._to_lookup(row)

        row = await self.asteroide_lazy.resolve(author)
        if row is not None:
            return await self._to_lookup(row)

        return AuthorProfileLookup()

    @staticmethod
    def _variants(author: str) -> set[str]:
        variants = {NormalizationUtils.normalize_text(author)}
        variants.add(
            NormalizationUtils.normalize_text(
                NormalizationUtils.author_name_first(author)
            )
        )
        return variants

    @staticmethod
    def _pick(sources: list[AuthorSource]) -> AuthorSource:
        for editorial in PREFERRED_SOURCES:
            for source in sources:
                if source.editorial == editorial:
                    return source
        return sources[0]

    async def _to_lookup(self, source: AuthorSource) -> AuthorProfileLookup:
        related = await self.related_repo.for_source(source.author_key, source.editorial)
        return AuthorProfileLookup(
            found=True,
            editorial=source.editorial,
            slug=source.slug,
            name=source.name,
            description=source.description,
            image_url=source.image_url,
            extra=(
                [
                    PublisherRelatedItem(
                        tipo=item.tipo,
                        titulo=item.titulo,
                        url=item.url,
                        fecha=item.fecha,
                        descripcion=item.descripcion,
                        thumbnail=item.thumbnail,
                        categoria=item.categoria,
                    )
                    for item in related
                ]
                if related
                else None
            ),
        )