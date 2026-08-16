"""add_book_id_to_central_blog_article_book

Revision ID: f9a0b1c2d3e4
Revises: f7b8c9d0e1f2
Create Date: 2026-08-15 17:00:00

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = 'f9a0b1c2d3e4'
down_revision: Union[str, Sequence[str], None] = 'f7b8c9d0e1f2'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column(
        'central_blog_article_book',
        sa.Column('book_id', sa.Integer(), nullable=True),
    )
    op.create_foreign_key(
        'fk_central_blog_article_book_book_id',
        'central_blog_article_book',
        'books',
        ['book_id'],
        ['id'],
    )
    op.create_index(
        op.f('ix_central_blog_article_book_book_id'),
        'central_blog_article_book',
        ['book_id'],
        unique=False,
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index(
        op.f('ix_central_blog_article_book_book_id'),
        table_name='central_blog_article_book',
    )
    op.drop_constraint(
        'fk_central_blog_article_book_book_id',
        'central_blog_article_book',
        type_='foreignkey',
    )
    op.drop_column('central_blog_article_book', 'book_id')