"""Repositori per a operacions CRUD de llibres."""

from sqlmodel import select, insert
from sqlmodel.ext.asyncio.session import AsyncSession

from app.models import Book
from app.schemas import BookBase

class BookRepository:
    _PORTADESBD_HOST = "portadesbd.diba.cat"
    _COVER_FIELDS = ("thumbnail", "small_thumbnail")

    def __init__(self, db: AsyncSession):
        self.db = db

    async def insert_books(self, books: list[BookBase]) -> list[Book]:
        best_per_key = self._dedup_batch(books)
        saved_books_dict = {}
        
        for book_data in best_per_key.values():
            existing_book = await self.find_by_title_author(
                book_data.normal_title, 
                book_data.normal_author,
                book_data.language,
            )
            
            if existing_book:
                book = await self._merge(existing_book, book_data)
            else: 
                book = Book.model_validate(book_data)

            self.db.add(book)
            
            key = (book.normal_title, book.normal_author, book.language)
            saved_books_dict[key] = book

        await self.db.commit()
        saved_books = list(saved_books_dict.values())

        for book in saved_books:
            await self.db.refresh(book)

        return saved_books

    def _dedup_batch(self, books: list[BookBase]) -> dict[tuple[str, str, str], BookBase]:
        best_per_key: dict[tuple[str, str, str], BookBase] = {}
        for book_data in books:
            key = (book_data.normal_title, book_data.normal_author, book_data.language)
            current = best_per_key.get(key)
            if current is None:
                best_per_key[key] = book_data
            elif self._prefer_book(book_data, current):
                best_per_key[key] = book_data
        return best_per_key

    @staticmethod
    def _prefer_book(candidate: BookBase, current: BookBase) -> bool:
        """Entre candidats de la mateixa obra, prefereix el que té portada
        vàlida i, a igualtat, l'edició més recent."""
        current_has_cover = bool(current.thumbnail)
        candidate_has_cover = bool(candidate.thumbnail)
        if candidate_has_cover != current_has_cover:
            return candidate_has_cover
        if candidate.publisher_date and (
            not current.publisher_date or candidate.publisher_date > current.publisher_date
        ):
            return True
        return False
    
    async def insert_book(self, book: Book) -> Book:
        book_data = book.model_dump(exclude_unset=True)

        stmt = insert(Book).values(**book_data).on_conflict_do_nothing(
                index_elements=["normal_title", "normal_author", "language"]
            ).returning(Book)
            
        inserted_book = (await self.db.exec(stmt)).first() 

        if inserted_book:
            await self.db.commit()
            return inserted_book
            
        return await self.find_by_title_author(book.normal_title, book.normal_author, book.language)

    async def find_by_title_author(self, normal_title: str, normal_author: str, language: str) -> Book | None:
        """
        Cerca un llibre per títol, autor i idioma.
        """
        statement = select(Book).where(
            Book.normal_title == normal_title,
            Book.normal_author == normal_author,
            Book.language == language)
        result = await self.db.exec(statement)
        return result.first()
    
    async def _merge(self, db_book: Book, to_merge_book: BookBase) -> Book:
        incoming_data = to_merge_book.model_dump(exclude_unset=True)

        for field_name, new_value in incoming_data.items():
            if field_name == "id":
                continue

            current_value = getattr(db_book, field_name)

            if field_name == "holdings_count" and new_value is not None:
                # Métrica viva (unidades en catálogo): se sobrescribe con el dato
                # más reciente en lugar de rellenar solo si estaba vacío.
                setattr(db_book, field_name, new_value)
            elif current_value is None and new_value is not None:
                setattr(db_book, field_name, new_value)
            elif (
                field_name in self._COVER_FIELDS
                and new_value is not None
                and isinstance(current_value, str)
                and self._PORTADESBD_HOST in current_value
            ):
                # Una portada portadesbd guardada pot ser un placeholder; el
                # candidat entrant ja ha estat validat (None si és placeholder).
                setattr(db_book, field_name, new_value)
        return db_book

    async def get_by_id(self, book_id: int) -> Book | None:
        """Cerca un llibre pel seu ID."""
        return await self.db.get(Book, book_id)

    async def update_price(self, book_id: int, price) -> Book | None:
        """Actualitza el preu del llibre i retorna el llibre actualitzat."""
        book = await self.get_by_id(book_id)
        if book is None:
            return None
        book.price = price
        await self.db.commit()
        await self.db.refresh(book)
        return book

    async def get_all(self) -> list[Book]:
        """Obté tots els llibres."""
        statement = select(Book)
        result = await self.db.exec(statement)
        return result.all()

    async def get_by_isbn(self, isbn: str) -> Book | None:
        """Cerca un llibre pel seu ISBN."""
        statement = select(Book).where(Book.isbn == isbn)
        result = await self.db.exec(statement)
        return result.first()
