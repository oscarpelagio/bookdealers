"""social shelves: shelves, user_books, shelf_items, reading_progress

Revision ID: 9c8d7e6f5a4b
Revises: 5f7a9c2d4e1b
Create Date: 2026-08-05 17:20:00.000000

Añade el contexto SHELVES / LIBRARY (FASE 2) de forma aditiva:
- `shelves`, `user_books`, `shelf_items`, `reading_progress`
- enums `shelf_kind`, `reading_status`
- seed de las 3 estanterías de estado para los usuarios existentes

`user_books.book_id` y `shelf_items.book_id` referencian `books.id`
(INT) con ON DELETE RESTRICT: no se toca el catálogo.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = '9c8d7e6f5a4b'
down_revision: Union[str, Sequence[str], None] = '5f7a9c2d4e1b'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


_SHELF_KIND = ('STATUS', 'CUSTOM')
_READING_STATUS = ('WANT_TO_READ', 'READING', 'READ', 'DNF')


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        'shelves',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('user_id', sa.UUID(), nullable=False),
        sa.Column('name', sa.String(length=80), nullable=False),
        sa.Column('slug', sa.String(length=80), nullable=False),
        sa.Column('kind', sa.Enum(*_SHELF_KIND, name='shelf_kind'), nullable=False),
        sa.Column('is_default', sa.Boolean(), nullable=False),
        sa.Column('is_private', sa.Boolean(), nullable=False),
        sa.Column('position', sa.Integer(), nullable=False),
        sa.Column('description', sa.String(length=200), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('user_id', 'slug', name='uq_shelves_user_slug'),
    )
    op.create_index('ix_shelves_user_id', 'shelves', ['user_id'], unique=False)
    op.create_index('ix_shelves_user_kind', 'shelves', ['user_id', 'kind'], unique=False)

    op.create_table(
        'user_books',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('user_id', sa.UUID(), nullable=False),
        sa.Column('book_id', sa.Integer(), nullable=False),
        sa.Column(
            'status',
            sa.Enum(*_READING_STATUS, name='reading_status'),
            nullable=False,
        ),
        sa.Column('current_page', sa.Integer(), nullable=True),
        sa.Column('percent_read', sa.Numeric(5, 2), nullable=True),
        sa.Column('started_at', sa.Date(), nullable=True),
        sa.Column('finished_at', sa.Date(), nullable=True),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            'percent_read IS NULL OR (percent_read >= 0 AND percent_read <= 100)',
            name='ck_user_books_percent_range',
        ),
        sa.ForeignKeyConstraint(['book_id'], ['books.id'], ondelete='RESTRICT'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('user_id', 'book_id', name='uq_user_books_user_book'),
    )
    op.create_index('ix_user_books_user_id', 'user_books', ['user_id'], unique=False)
    op.create_index('ix_user_books_book_id', 'user_books', ['book_id'], unique=False)
    op.create_index(
        'ix_user_books_user_status', 'user_books', ['user_id', 'status'], unique=False
    )

    op.create_table(
        'shelf_items',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('user_id', sa.UUID(), nullable=False),
        sa.Column('shelf_id', sa.UUID(), nullable=False),
        sa.Column('book_id', sa.Integer(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['book_id'], ['books.id'], ondelete='RESTRICT'),
        sa.ForeignKeyConstraint(['shelf_id'], ['shelves.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint(
            'user_id', 'shelf_id', 'book_id', name='uq_shelf_items_user_shelf_book'
        ),
    )
    op.create_index('ix_shelf_items_user_id', 'shelf_items', ['user_id'], unique=False)
    op.create_index('ix_shelf_items_shelf_id', 'shelf_items', ['shelf_id'], unique=False)
    op.create_index('ix_shelf_items_book_id', 'shelf_items', ['book_id'], unique=False)
    op.create_index(
        'ix_shelf_items_user_book', 'shelf_items', ['user_id', 'book_id'], unique=False
    )

    op.create_table(
        'reading_progress',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('user_book_id', sa.UUID(), nullable=False),
        sa.Column('page', sa.Integer(), nullable=True),
        sa.Column('percent_read', sa.Numeric(5, 2), nullable=True),
        sa.Column('note', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            'percent_read IS NULL OR (percent_read >= 0 AND percent_read <= 100)',
            name='ck_reading_progress_percent_range',
        ),
        sa.ForeignKeyConstraint(['user_book_id'], ['user_books.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(
        'ix_reading_progress_user_book_id',
        'reading_progress',
        ['user_book_id'],
        unique=False,
    )

    # Seed de las 3 estanterías de estado para los usuarios existentes.
    for name, slug, position in (
        ('To Read', 'to-read', 0),
        ('Currently Reading', 'currently-reading', 1),
        ('Read', 'read', 2),
    ):
        op.execute(
            f"""
            INSERT INTO shelves (id, user_id, name, slug, kind, is_default,
                is_private, position, created_at, updated_at)
            SELECT gen_random_uuid(), u.id, '{name}', '{slug}', 'STATUS', TRUE,
                FALSE, {position}, u.created_at, u.updated_at
            FROM users u
            ON CONFLICT (user_id, slug) DO NOTHING
            """
        )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index('ix_reading_progress_user_book_id', table_name='reading_progress')
    op.drop_table('reading_progress')
    op.drop_index('ix_shelf_items_user_book', table_name='shelf_items')
    op.drop_index('ix_shelf_items_book_id', table_name='shelf_items')
    op.drop_index('ix_shelf_items_shelf_id', table_name='shelf_items')
    op.drop_index('ix_shelf_items_user_id', table_name='shelf_items')
    op.drop_table('shelf_items')
    op.drop_index('ix_user_books_user_status', table_name='user_books')
    op.drop_index('ix_user_books_book_id', table_name='user_books')
    op.drop_index('ix_user_books_user_id', table_name='user_books')
    op.drop_table('user_books')
    op.drop_index('ix_shelves_user_kind', table_name='shelves')
    op.drop_index('ix_shelves_user_id', table_name='shelves')
    op.drop_table('shelves')
    op.execute('DROP TYPE IF EXISTS reading_status')
    op.execute('DROP TYPE IF EXISTS shelf_kind')