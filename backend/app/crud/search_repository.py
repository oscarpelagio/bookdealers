"""Repository for book CRUD operations."""

from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from app.models import Search, SearchRelation, Book
from app.utils import NormalizationUtils

class SearchRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def save_cache(self, search: str, books: list[Book]) :
        cache_statement = select(Search).where(Search.query == search)
        cache_result = await self.db.exec(cache_statement)
        existing = cache_result.first()
        if existing:
            return []
        cached_search = await self._insert_search_(search)
        cached_relation = []
        for book in books:
            relation = await self._insert_relation(book, cached_search)
            cached_relation.append(relation)
        return cached_relation
    
    async def check_cache(self, search: str, max_results: int = 10) -> list[Book] | None:
        normalized_query = NormalizationUtils.normalize_text(search)
        statement = select(Search).where(Search.query == normalized_query)
        result = await self.db.exec(statement)
        existing_search = result.first()
        if not existing_search:
            return None

        statement = select(SearchRelation).where(SearchRelation.id_search == existing_search.id).limit(max_results)
        relations = (await self.db.exec(statement)).all()

        if not relations:
            return None

        # 2. Extract IDs and fetch all books at once with IN_
        book_ids = [rel.id_book for rel in relations]
        books_statement = select(Book).where(Book.id.in_(book_ids))
        books = (await self.db.exec(books_statement)).all()
        return list(books)

    async def _insert_search_(self, query: str) -> Search:
        normalized_query = NormalizationUtils.normalize_text(query)
        
        statement = select(Search).where(Search.query == normalized_query)
        result = await self.db.exec(statement)
        existing_search = result.first()
        
        if existing_search:
            return existing_search
        new_search = Search(query=normalized_query)
        
        self.db.add(new_search)
        await self.db.commit()
        await self.db.refresh(new_search)
        return new_search

    async def _insert_relation(self, book: Book, search: Search) -> SearchRelation:
        relation = SearchRelation.model_validate({"id_book": book.id, "id_search": search.id})
        statement = select(SearchRelation).where(
            SearchRelation.id_book == relation.id_book, 
            SearchRelation.id_search == relation.id_search, 
        )
        result = await self.db.exec(statement)
        existing = result.first()
        if existing:
            return relation
        self.db.add(relation)
        await self.db.commit()
        await self.db.refresh(relation)
        return relation
