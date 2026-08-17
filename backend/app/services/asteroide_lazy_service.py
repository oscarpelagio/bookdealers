"""Servei per resoldre autors de Libros del Asteroide de forma peresosa.

Quan un autor no està a `author_source`, es busca a l'índex lleuger
`asteroide_author_index` pel nom (match exacte per normalitzat, fallback
`thefuzz`) i es descarrega/parseja SOLS el seu perfil (`/autor/{slug}`),
persistint-lo amb `editorial='asteroide'`.

L'índex es precarrega (vegeu `scripts/scrape_asteroide_index.py`); la URL
de perfil es construeix amb el slug guardat.
"""

import logging

from thefuzz import fuzz

from app.adapters.asteroide_adapter import parse_profile
from app.clients import AsteroideClient
from app.crud import AsteroideIndexRepository, AuthorSourceRelatedRepository, AuthorSourceRepository
from app.models import AsteroideAuthorIndex, AuthorSource
from app.utils import NormalizationUtils

logger = logging.getLogger(__name__)

EDITORIAL = "asteroide"
FUZZY_THRESHOLD = 82


class AsteroideLazyService:

    def __init__(
        self,
        repo: AuthorSourceRepository,
        index_repo: AsteroideIndexRepository,
        client: AsteroideClient,
        related_repo: AuthorSourceRelatedRepository,
    ) -> None:
        self.repo = repo
        self.index_repo = index_repo
        self.client = client
        self.related_repo = related_repo

    async def resolve(self, author: str) -> AuthorSource | None:
        author = (author or "").strip()
        if not author:
            return None

        author_key = NormalizationUtils.normalize_text(
            NormalizationUtils.author_name_first(author)
        )
        if not author_key:
            return None

        cached = await self.repo.get(author_key, EDITORIAL)
        if cached is not None:
            return cached

        try:
            entry = await self._find_index(author)
            if entry is None:
                return None
            return await self._fetch_profile(author_key, entry)
        except Exception:
            logger.exception("Fallo resolviendo autor Asteroide '%s'", author)
            return None

    async def _find_index(self, author: str) -> AsteroideAuthorIndex | None:
        # 1) Match exacte per slug derivat del nom ("lucia solla sobral"
        #    -> "lucia-solla-sobral").
        for name_variant in {author, NormalizationUtils.author_name_first(author)}:
            slug = NormalizationUtils.normalize_text(name_variant).replace(" ", "-")
            if not slug:
                continue
            by_slug = await self.index_repo.by_slug(slug)
            if by_slug:
                return by_slug

        # 2) Match exacte per nom normalitzat.
        for name_variant in {author, NormalizationUtils.author_name_first(author)}:
            exact = await self.index_repo.by_normalized(
                NormalizationUtils.normalize_text(name_variant)
            )
            if exact:
                return exact[0]

        # 3) Fallback difús sobre tots els noms normalitzats.
        variants = {
            NormalizationUtils.normalize_text(author),
            NormalizationUtils.normalize_text(
                NormalizationUtils.author_name_first(author)
            ),
        }
        pool = await self.index_repo.all_view()
        if not pool:
            return None
        best: tuple[int, str | None] = (0, None)
        for variant in variants:
            for name_normalized, slug in pool:
                ratio = fuzz.token_set_ratio(variant, name_normalized)
                if ratio > best[0]:
                    best = (ratio, slug)
        if best[0] >= FUZZY_THRESHOLD and best[1]:
            return await self.index_repo.by_slug(best[1])
        return None

    async def _fetch_profile(
        self, author_key: str, entry: AsteroideAuthorIndex
    ) -> AuthorSource | None:
        try:
            profile = await self.client.get_profile(entry.slug)
        except Exception:
            logger.exception(
                "Fallo descargando perfil Asteroide '%s'", entry.slug
            )
            return None

        name = (profile.name or "").strip() or entry.name
        if not name:
            return None
        try:
            row = await self.repo.upsert(
                author_key=author_key,
                editorial=EDITORIAL,
                name=name,
                slug=entry.slug,
                description=profile.description,
                image_url=profile.image_url,
            )
            await self.related_repo.replace(author_key, EDITORIAL, None)
            return row
        except Exception:
            logger.exception("Fallo persistindo perfil Asteroide '%s'", author_key)
            return None