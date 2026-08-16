"""Servei de cerca d'un autor a la taula `authors_anagrama`.

Busca per nom normalitzat (sense accents, ordre "apellido, nombre" o
"nombre apellido") i, si no hi ha coincidència exacta, fa fallback a
`thefuzz` (token_set_ratio). La taula només té ~1.600 files, així que
carregar-la sencera per cada lookup és barat i evita una columna indexada.
"""

from thefuzz import fuzz

from app.crud import AnagramaRepository
from app.models import AuthorAnagrama
from app.schemas import AnagramaRelatedItem, AuthorAnagramaLookup
from app.utils import NormalizationUtils

FUZZY_THRESHOLD = 82


class AnagramaLookupService:

    def __init__(self, repo: AnagramaRepository) -> None:
        self.repo = repo

    async def lookup(self, author: str) -> AuthorAnagramaLookup:
        author = (author or "").strip()
        if not author:
            return AuthorAnagramaLookup()

        authors = await self.repo.all()
        if not authors:
            return AuthorAnagramaLookup()

        variants = {NormalizationUtils.normalize_text(author)}
        if "," in author:
            variants.add(
                NormalizationUtils.normalize_text(
                    NormalizationUtils.author_name_first(author)
                )
            )

        index: dict[str, AuthorAnagrama] = {}
        for row in authors:
            index.setdefault(NormalizationUtils.normalize_text(row.name), row)
            index.setdefault(
                NormalizationUtils.normalize_text(
                    NormalizationUtils.author_name_first(row.name)
                ),
                row,
            )

        for variant in variants:
            if variant in index:
                return self._to_lookup(index[variant])

        best: AuthorAnagrama | None = None
        best_ratio = 0
        for variant in variants:
            for row in authors:
                ratio = fuzz.token_set_ratio(
                    variant, NormalizationUtils.normalize_text(row.name)
                )
                ratio = max(
                    ratio,
                    fuzz.token_set_ratio(
                        variant,
                        NormalizationUtils.normalize_text(
                            NormalizationUtils.author_name_first(row.name)
                        ),
                    ),
                )
                if ratio > best_ratio:
                    best_ratio = ratio
                    best = row

        if best is not None and best_ratio >= FUZZY_THRESHOLD:
            return self._to_lookup(best)
        return AuthorAnagramaLookup()

    @staticmethod
    def _to_lookup(author: AuthorAnagrama) -> AuthorAnagramaLookup:
        return AuthorAnagramaLookup(
            found=True,
            slug=author.slug,
            name=author.name,
            description=author.description,
            image_url=author.image_url,
            extra=(
                [AnagramaRelatedItem(**item) for item in author.extra]
                if author.extra
                else None
            ),
        )
