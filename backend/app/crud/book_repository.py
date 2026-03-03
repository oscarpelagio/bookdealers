"""Repositori per a operacions CRUD de llibres."""

from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from app.models import Book
from app.schemas import BookBase

class BookRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def insert_books(self, books: list[BookBase]) -> list[Book]:
        saved_books_dict = {}
        
        for book_data in books:
            existing_book = await self.find_by_title_author(
                book_data.normal_title, 
                book_data.normal_author
            )
            
            if existing_book:
                # Modifica el objeto existente en memoria
                book = await self._merge(existing_book, book_data)
            else: 
                # Crea un objeto nuevo
                book = Book.model_validate(book_data)

            self.db.add(book)
            
            # Al guardarlo en el diccionario, si ya había un libro igual en este 
            # mismo lote, se sobrescribe con la versión más reciente/mergeada.
            key = (book.normal_title, book.normal_author)
            saved_books_dict[key] = book

        # Ahora hacemos commit para que se generen los IDs de los libros nuevos
        await self.db.commit()

        # Extraemos solo los valores (los libros únicos) del diccionario
        saved_books = list(saved_books_dict.values())

        for book in saved_books:
            await self.db.refresh(book)

        return saved_books
    
    
    async def insert_book(self, book: Book) -> Book:
        """
        Crea un llibre nou. Si ja existeix (títol+autor normalitzats), retorna l'existent.
        """
        # Comprova si el llibre ja existeix per títol+autor normalitzats
        existing_book = await self.find_by_title_author(
            book.normal_title, 
            book.normal_author
        )
        if existing_book:
            book = await self._merge(existing_book, book)
        
        else: 
            book = Book.model_validate(book)

        self.db.add(book)
        await self.db.commit()
        await self.db.refresh(book)
        return book

    async def find_by_title_author(self, normal_title: str, normal_author: str) -> Book | None:
        """
        Cerca un llibre per títol i autor amb normalització.
        """
        statement = select(Book).where(
            Book.normal_title == normal_title,
            Book.normal_author == normal_author)
        result = await self.db.exec(statement)
        return result.first()
    
    async def _merge(self, db_book: Book, to_merge_book: BookBase) -> Book:
        incoming_data = to_merge_book.model_dump(exclude_unset=True)

        for field_name, new_value in incoming_data.items():
            if field_name == "id":
                continue

            current_value = getattr(db_book, field_name)

            if current_value is None and new_value is not None:
                setattr(db_book, field_name, new_value)
        return db_book

    async def get_by_id(self, book_id: int) -> Book | None:
        """Cerca un llibre pel seu ID."""
        return await self.db.get(Book, book_id)

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
