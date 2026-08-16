"""Seed de la librería de la cuenta admin (admin@example.com).

Llena los 4 estantes de estado (To Read / Currently Reading / Read /
Abandoned) buscando libros reales en Open Library y añadiéndolos como
`user_books` de admin con el estado correspondiente.

Uso (desde el contenedor del backend):
    docker compose exec back python scripts/seed_admin_library.py
"""

import asyncio
from difflib import SequenceMatcher

from sqlmodel import select

from app.adapters import OpenLibraryAdapter
from app.auth.models import User
from app.clients import OpenLibraryClient
from app.core.db import async_session
from app.crud import BookRepository, SearchRepository
from app.enums import ReadingStatus
from app.shelves.repository import ShelfRepository
from app.shelves.service import ShelfService
from app.services import OpenLibraryService

ADMIN_EMAIL = "admin@example.com"

# (título, autor, estado)
BOOKS = [
    # --- Read (leídos) ---
    ("Cien años de soledad", "Gabriel García Márquez", ReadingStatus.READ),
    ("1984", "George Orwell", ReadingStatus.READ),
    ("El Principito", "Antoine de Saint-Exupéry", ReadingStatus.READ),
    ("Orgullo y prejuicio", "Jane Austen", ReadingStatus.READ),
    ("La casa de los espíritus", "Isabel Allende", ReadingStatus.READ),
    # --- Currently Reading (leyendo) ---
    ("Fundación", "Isaac Asimov", ReadingStatus.READING),
    ("Sapiens. De animales a dioses", "Yuval Noah Harari", ReadingStatus.READING),
    ("It", "Stephen King", ReadingStatus.READING),
    ("La ridícula idea de no volver a verte", "Rosa Montero", ReadingStatus.READING),
    # --- To Read (por leer) ---
    ("La sombra del viento", "Carlos Ruiz Zafón", ReadingStatus.WANT_TO_READ),
    ("Dune", "Frank Herbert", ReadingStatus.WANT_TO_READ),
    ("El nombre del viento", "Patrick Rothfuss", ReadingStatus.WANT_TO_READ),
    ("Los juegos del hambre", "Suzanne Collins", ReadingStatus.WANT_TO_READ),
    ("El problema de los tres cuerpos", "Cixin Liu", ReadingStatus.WANT_TO_READ),
    # --- Abandoned (DNF) ---
    ("Ulises", "James Joyce", ReadingStatus.DNF),
    ("Moby Dick", "Herman Melville", ReadingStatus.DNF),
    ("Guerra y paz", "León Tolstói", ReadingStatus.DNF),
    ("El señor de los anillos", "J. R. R. Tolkien", ReadingStatus.DNF),
]

PREFERRED_LANGS = {"spa", "eng"}


async def find_admin(db) -> User:
    user = (await db.exec(select(User).where(User.email == ADMIN_EMAIL))).first()
    if user is None:
        raise SystemExit(f"No existe el usuario {ADMIN_EMAIL}")
    return user


async def _search_with_q(
    search_service, book_repo, client, adapter, title: str, author: str
):
    """Busca con el campo `q` de Open Library y persiste los resultados.

    El filtro estricto `title` de la API devuelve 0 para títulos compuestos;
    `q` hace matching libre. Inserta vía book_repository igual que
    `search_and_process`.
    """
    params = {"limit": 8, "q": f"{title} {author}".strip()}
    results = await client.fetch_books(params)
    books = adapter.response_adapter(results)
    return await book_repo.insert_books(books)


async def pick_book(search_service, book_repo, client, adapter, title: str, author: str):
    """Busca y devuelve el mejor resultado persistido.

    Prioriza, en orden: (1) thumbnail presente, (2) idioma en spa/eng,
    (3) similitud del título normalizado con la búsqueda. Si el filtro
    estricto no devuelve nada, reintenta con `q`.
    """
    results = await search_service.search_and_process(title, author, max_results=8)
    if not results:
        results = await _search_with_q(
            search_service, book_repo, client, adapter, title, author
        )
    if not results:
        return None

    target = title.lower().strip()

    def score(b):
        s = 0.0
        if b.thumbnail:
            s += 3.0
        if b.language in PREFERRED_LANGS:
            s += 2.0
        b_title = (b.title or "").lower()
        s += SequenceMatcher(None, target, b_title).ratio() * 5.0
        if b.author and author and author.lower().split()[0] in b.author.lower():
            s += 1.0
        return s

    return max(results, key=score)


async def main() -> None:
    async with async_session() as db:
        admin = await find_admin(db)
        shelf_service = ShelfService(ShelfRepository(db), db)
        # Asegura los 4 estantes de estado (idempotente).
        await shelf_service.list_shelves(admin)

        search_service = OpenLibraryService(
            book_repo=BookRepository(db),
            search_repo=SearchRepository(db),
            client=OpenLibraryClient(),
            adapter=OpenLibraryAdapter(),
        )
        client = OpenLibraryClient()
        adapter = OpenLibraryAdapter()
        book_repo = BookRepository(db)

        added, skipped, errors = [], [], []
        for title, author, status in BOOKS:
            try:
                book = await pick_book(
                    search_service, book_repo, client, adapter, title, author
                )
                if book is None:
                    skipped.append(f"{title} (sin resultados)")
                    continue
                resp = await shelf_service.update_or_create_user_book(
                    admin, book.id, status=status
                )
                added.append(f"[{status.value}] {resp.book.title}")
            except Exception as exc:  # noqa: BLE001
                errors.append(f"{title} -> {type(exc).__name__}: {exc}")

        print("\n=== AÑADIDOS ===")
        for line in added:
            print(" ", line)
        if skipped:
            print("\n=== SIN RESULTADOS ===")
            for line in skipped:
                print(" ", line)
        if errors:
            print("\n=== ERRORES ===")
            for line in errors:
                print(" ", line)
        print(f"\nTotal añadidos: {len(added)} | sin resultados: {len(skipped)} | errores: {len(errors)}")


if __name__ == "__main__":
    asyncio.run(main())
