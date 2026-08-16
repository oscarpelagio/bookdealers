"""Servei per resoldre autors de Penguin de forma peresosa (lazy).

Quan un autor no està a `author_source`, es busca a l'índex lleuger
`penguin_author_index` pel nom (match exacte per normalitzat, fallback
`thefuzz`) i es descarrega/parseja SOLS el seu perfil, persistint-lo amb
`editorial='penguin'`.

El cercador Elastico de Penguin no respon a bots (body buit), per això es
fa servir l'índex precarregat (vegeu `scripts/scrape_penguin_index.py`).
"""

import logging

from thefuzz import fuzz

from app.adapters.penguin_adapter import parse_profile
from app.clients import PenguinClient
from app.clients.anagrama_client import RateLimitedError
from app.crud import AuthorSourceRepository, PenguinIndexRepository
from app.models import AuthorSource, PenguinAuthorIndex
from app.utils import NormalizationUtils

logger = logging.getLogger(__name__)

EDITORIAL = "penguin"
FUZZY_THRESHOLD = 82


class PenguinLazyService:

    def __init__(
        self,
        repo: AuthorSourceRepository,
        index_repo: PenguinIndexRepository,
        client: PenguinClient,
    ) -> None:
        self.repo = repo
        self.index_repo = index_repo
        self.client = client

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
            logger.exception("Fallo resolviendo autor Penguin '%s'", author)
            return None

    async def _find_index(self, author: str) -> PenguinAuthorIndex | None:
        # 1) Match exacte per slug derivat del nom ("han kang" -> "han-kang").
        for name_variant in {author, NormalizationUtils.author_name_first(author)}:
            slug = NormalizationUtils.normalize_text(name_variant).replace(" ", "-")
            if not slug:
                continue
            by_slug = await self.index_repo.by_slug(slug)
            if by_slug:
                return by_slug[0]

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
        best_id: int | None = None
        best_ratio = 0
        for variant in variants:
            for name_normalized, author_id in pool:
                ratio = fuzz.token_set_ratio(variant, name_normalized)
                if ratio > best_ratio:
                    best_ratio = ratio
                    best_id = author_id
        if best_id is not None and best_ratio >= FUZZY_THRESHOLD:
            return await self.index_repo.get_by_id(best_id)
        return None

    async def _fetch_profile(
        self, author_key: str, entry: PenguinAuthorIndex
    ) -> AuthorSource | None:
        html = None
        try:
            html = await self.client.get_profile(entry.author_id, entry.slug)
        except RateLimitedError:
            logger.warning("Penguin rate-limited en '%s'", entry.name or entry.author_id)
        except Exception:
            logger.exception("Fallo descargando perfil Penguin '%s'", entry.author_id)
        if html is None:
            return None

        profile = parse_profile(html)
        name = (profile.name or "").strip() or entry.name
        if not name:
            return None
        slug = entry.slug or (await self._slug_of(profile.name, entry.author_id))
        try:
            return await self.repo.upsert(
                author_key=author_key,
                editorial=EDITORIAL,
                name=name,
                slug=slug,
                description=profile.description,
                image_url=profile.image_url,
                extra=profile.extra or None,
            )
        except Exception:
            logger.exception("Fallo persistindo perfil Penguin '%s'", author_key)
            return None

    async def _slug_of(self, name: str, author_id: int) -> str | None:
        slug = NormalizationUtils.normalize_text(name).replace(" ", "-")
        by_slug = await self.index_repo.by_slug(slug)
        for candidate in by_slug:
            if candidate.author_id == author_id:
                return candidate.slug
        return by_slug[0].slug if by_slug else slug or None