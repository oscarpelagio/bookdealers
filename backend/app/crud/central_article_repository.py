"""Repositori dels articles i llibres del blog de La Central."""

import re
from datetime import datetime

from sqlalchemy.dialects.postgresql import insert
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from app.adapters import LaCentralArticle, LaCentralBook
from app.models import CentralBlogArticle, CentralBlogArticleBook
from app.utils import NormalizationUtils


_PARENTHESES_RE = re.compile(r"\([^)]*\)")


def _clean_author(author: str) -> str:
    """Elimina anotacions parentètiques ('(Ilustrador/a)', '(Copernicus, ...)')."""
    return _PARENTHESES_RE.sub("", author).strip()


class CentralArticleRepository:
    """Operacions CRUD sobre `central_blog_article` i `central_blog_article_book`."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def upsert_cards(self, cards) -> int:
        """Insereix les tarjetes del llistat (ON CONFLICT DO NOTHING per slug)."""
        if not cards:
            return 0
        rows = [
            {
                "slug": c.slug,
                "url": c.url,
                "tipo": c.tipo,
                "titulo": c.titulo,
                "subtitulo": c.subtitulo,
                "intro": c.intro,
                "autor": c.autor,
                "fecha": None,
                "cuerpo": None,
                "portada_url": None,
                "status": "pending",
                "fetched_at": None,
            }
            for c in cards
        ]
        stmt = (
            insert(CentralBlogArticle)
            .values(rows)
            .on_conflict_do_nothing(index_elements=["slug"])
        )
        result = await self.db.execute(stmt)
        await self.db.commit()
        return max(result.rowcount or 0, 0)

    async def pending_articles(self) -> list[CentralBlogArticle]:
        result = await self.db.exec(
            select(CentralBlogArticle).where(CentralBlogArticle.status == "pending")
        )
        return list(result)

    async def rescrape_status(self) -> str:
        """Canvia tots els articles a 'pending' (per arescrapejar-ho tot)."""
        art_list = (
            await self.db.exec(select(CentralBlogArticle))
        ).all()
        for art in art_list:
            art.status = "pending"
            art.fetched_at = None
        await self.db.commit()
        return f"{len(art_list)} articles marcats com a pending"

    async def save_article(self, article: LaCentralArticle, libros: list[LaCentralBook]) -> int:
        """Guarda el contingut complet d'un article (upsert per slug) i els seus llibres.

        Torna el nombre de llibres guardats per a l'article.
        """
        now = datetime.utcnow()
        existing = (
            await self.db.exec(
                select(CentralBlogArticle).where(CentralBlogArticle.slug == article.slug)
            )
        ).first()

        if existing is None:
            row = CentralBlogArticle(
                slug=article.slug,
                url=article.url,
                tipo=article.tipo,
                titulo=article.titulo,
                subtitulo=article.subtitulo,
                intro=article.intro,
                autor=article.autor,
                fecha=article.fecha,
                cuerpo=article.cuerpo,
                portada_url=article.portada_url,
                status="done",
                fetched_at=now,
            )
            self.db.add(row)
            await self.db.flush()
            article_id = row.id
        else:
            article_id = existing.id
            for attr in ("tipo", "titulo", "subtitulo", "intro", "autor", "fecha",
                         "cuerpo", "portada_url"):
                setattr(existing, attr, getattr(article, attr))
            existing.status = "done"
            existing.fetched_at = now
            await self.db.flush()

        # Esborra els llibres vells de l'article i insereix els nous.
        old = await self.db.exec(
            select(CentralBlogArticleBook).where(
                CentralBlogArticleBook.article_id == article_id
            )
        )
        for book in old:
            await self.db.delete(book)

        book_rows = [
            {
                "article_id": article_id,
                "posicion": b.posicion,
                "titulo_normalizado": NormalizationUtils.normalize_text(b.titulo),
                "autor_normalizado": NormalizationUtils.normalize_text(
                    NormalizationUtils.author_name_first(_clean_author(b.autor))
                ),
            }
            for b in libros
        ]
        if book_rows:
            self.db.add_all(
                CentralBlogArticleBook(**row) for row in book_rows
            )
        await self.db.commit()
        return len(book_rows)

    async def count(self) -> tuple[int, int]:
        """(articles totals, articles fets)."""
        total = len((await self.db.exec(select(CentralBlogArticle))).all())
        done = len(
            (
                await self.db.exec(
                    select(CentralBlogArticle).where(CentralBlogArticle.status == "done")
                )
            ).all()
        )
        return total, done

    async def get_by_slug(self, slug: str) -> CentralBlogArticle | None:
        """Cerca un article pel seu slug."""
        result = await self.db.exec(
            select(CentralBlogArticle).where(CentralBlogArticle.slug == slug)
        )
        return result.first()

    async def books_in_article(self, article_id: int) -> list[CentralBlogArticleBook]:
        """Entrades (llibres) d'un article ordenades per posició."""
        result = await self.db.exec(
            select(CentralBlogArticleBook)
            .where(CentralBlogArticleBook.article_id == article_id)
            .order_by(CentralBlogArticleBook.posicion)
        )
        return list(result)

    async def set_book_id(self, entry_id: int, book_id: int) -> None:
        """Guarda el llibre del catàleg resolt per a una entrada."""
        entry = await self.db.get(CentralBlogArticleBook, entry_id)
        if entry is not None:
            entry.book_id = book_id
            await self.db.commit()

    async def book_appears_in(
        self,
        normal_title: str,
        normal_author: str,
    ) -> list[tuple[CentralBlogArticle, int]]:
        """Posts del blog on apareix un llibre (per títol + autor normalitzats).

        Retorna una llista de (article, posicio del llibre) ordenada per data
        descendent (posts més recents primer).
        """
        if not normal_title or not normal_author:
            return []
        stmt = (
            select(CentralBlogArticle, CentralBlogArticleBook.posicion)
            .join(
                CentralBlogArticleBook,
                CentralBlogArticleBook.article_id == CentralBlogArticle.id,
            )
            .where(
                CentralBlogArticleBook.titulo_normalizado == normal_title,
                CentralBlogArticleBook.autor_normalizado == normal_author,
            )
            .order_by(CentralBlogArticle.fecha.desc().nullslast(), CentralBlogArticle.id.desc())
        )
        result = await self.db.exec(stmt)
        return list(result)

    async def articles_by_author(
        self,
        normal_author: str,
    ) -> list[tuple[CentralBlogArticle, int]]:
        """Posts del blog on apareix ALGUN llibre d'un autor (per autor normalitzat).

        Retorna (article, posicio del primer llibre trobat de l'autor) ordenat
        per data descendent. Un mateix article només surt una vegada.
        """
        if not normal_author:
            return []
        rows = (
            await self.db.exec(
                select(
                    CentralBlogArticle,
                    CentralBlogArticleBook.posicion,
                )
                .join(
                    CentralBlogArticleBook,
                    CentralBlogArticleBook.article_id == CentralBlogArticle.id,
                )
                .where(CentralBlogArticleBook.autor_normalizado == normal_author)
                .order_by(
                    CentralBlogArticle.fecha.desc().nullslast(),
                    CentralBlogArticle.id.desc(),
                )
            )
        ).all()
        articles: dict[int, tuple[CentralBlogArticle, int]] = {}
        for article, posicion in rows:
            if article.id not in articles:
                articles[article.id] = (article, posicion)
        return list(articles.values())