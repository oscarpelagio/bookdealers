"""create_central_blog_tables

Revision ID: f7b8c9d0e1f2
Revises: f6a8b2c4d6e0
Create Date: 2026-08-15 16:00:00

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
import sqlmodel

# revision identifiers, used by Alembic.
revision: str = 'f7b8c9d0e1f2'
down_revision: Union[str, Sequence[str], None] = 'f6a8b2c4d6e0'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        'central_blog_article',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('slug', sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column('url', sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column('tipo', sqlmodel.sql.sqltypes.AutoString(), nullable=True),
        sa.Column('titulo', sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column('subtitulo', sqlmodel.sql.sqltypes.AutoString(), nullable=True),
        sa.Column('intro', sqlmodel.sql.sqltypes.AutoString(), nullable=True),
        sa.Column('autor', sqlmodel.sql.sqltypes.AutoString(), nullable=True),
        sa.Column('fecha', sqlmodel.sql.sqltypes.AutoString(), nullable=True),
        sa.Column('cuerpo', sa.Text(), nullable=True),
        sa.Column('portada_url', sqlmodel.sql.sqltypes.AutoString(), nullable=True),
        sa.Column('status', sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column('fetched_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(
        op.f('ix_central_blog_article_slug'),
        'central_blog_article',
        ['slug'],
        unique=True,
    )
    op.create_table(
        'central_blog_article_book',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('article_id', sa.Integer(), nullable=False),
        sa.Column('posicion', sa.Integer(), nullable=False),
        sa.Column('titulo_normalizado', sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column('autor_normalizado', sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.ForeignKeyConstraint(['article_id'], ['central_blog_article.id']),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(
        op.f('ix_central_blog_article_book_article_id'),
        'central_blog_article_book',
        ['article_id'],
        unique=False,
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index(
        op.f('ix_central_blog_article_book_article_id'),
        table_name='central_blog_article_book',
    )
    op.drop_table('central_blog_article_book')
    op.drop_index(
        op.f('ix_central_blog_article_slug'),
        table_name='central_blog_article',
    )
    op.drop_table('central_blog_article')