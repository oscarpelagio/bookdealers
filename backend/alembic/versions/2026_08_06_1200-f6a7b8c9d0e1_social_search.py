"""search social: índices pg_trgm y FTS

Revision ID: f6a7b8c9d0e1
Revises: e5f6a7b8c9d0
Create Date: 2026-08-06 12:00:00.000000

Búsqueda social (FASE 10): índices de rendimiento para los queries
`search_users` / `search_books` / `search_posts`. Aditivo, sin tablas:
- Extensión `pg_trgm` + índices GIN trigram sobre `users.username`,
  `profiles.display_name`, `books.normal_title` y `books.normal_author`.
- Extensión `unaccent` (búsqueda insensible a tildes).

La búsqueda funciona igualmente sin estos índices (ILIKE), son solo perf.
"""
from typing import Sequence, Union

from alembic import op

# revision identifiers, used by Alembic.
revision: str = 'f6a7b8c9d0e1'
down_revision: Union[str, Sequence[str], None] = 'e5f6a7b8c9d0'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.execute('CREATE EXTENSION IF NOT EXISTS pg_trgm')
    op.execute('CREATE EXTENSION IF NOT EXISTS unaccent')
    op.create_index(
        'ix_users_username_trgm', 'users', ['username'],
        unique=False, postgresql_using='gin',
        postgresql_ops={'username': 'gin_trgm_ops'},
    )
    op.create_index(
        'ix_profiles_display_name_trgm', 'profiles', ['display_name'],
        unique=False, postgresql_using='gin',
        postgresql_ops={'display_name': 'gin_trgm_ops'},
    )
    op.create_index(
        'ix_books_normal_title_trgm', 'books', ['normal_title'],
        unique=False, postgresql_using='gin',
        postgresql_ops={'normal_title': 'gin_trgm_ops'},
    )
    op.create_index(
        'ix_books_normal_author_trgm', 'books', ['normal_author'],
        unique=False, postgresql_using='gin',
        postgresql_ops={'normal_author': 'gin_trgm_ops'},
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index('ix_books_normal_author_trgm', table_name='books')
    op.drop_index('ix_books_normal_title_trgm', table_name='books')
    op.drop_index('ix_profiles_display_name_trgm', table_name='profiles')
    op.drop_index('ix_users_username_trgm', table_name='users')
    op.execute('DROP EXTENSION IF EXISTS unaccent')
    op.execute('DROP EXTENSION IF EXISTS pg_trgm')
