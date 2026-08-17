"""create_sourced_lists

Revision ID: bc12de34ef78
Revises: ab12cd34ef56
Create Date: 2026-08-17 11:00:00

Crea les taules genèriques `sourced_lists` i `sourced_list_books` i hi copia
les dades actuals de La Central (`central_blog_article` / `central_blog_article_book`)
amb `source='lacentral'`. Les taules antigues es conserven (deprecades) fins
que el front deixi d'usar-les.
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
import sqlmodel

# revision identifiers, used by Alembic.
revision: str = 'bc12de34ef78'
down_revision: Union[str, Sequence[str], None] = 'ab12cd34ef56'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        'sourced_lists',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('source', sqlmodel.sql.sqltypes.AutoString(), nullable=False),
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
        sa.Column('fetched_at', sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('source', 'slug', name='uq_sourced_lists_source_slug'),
    )
    op.create_index(
        op.f('ix_sourced_lists_slug'),
        'sourced_lists',
        ['slug'],
        unique=False,
    )
    op.create_table(
        'sourced_list_books',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('list_id', sa.Integer(), nullable=False),
        sa.Column('posicion', sa.Integer(), nullable=False),
        sa.Column('titulo_normalizado', sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column('autor_normalizado', sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column('book_id', sa.Integer(), nullable=True),
        sa.ForeignKeyConstraint(['book_id'], ['books.id']),
        sa.ForeignKeyConstraint(['list_id'], ['sourced_lists.id']),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(
        op.f('ix_sourced_list_books_list_id'),
        'sourced_list_books',
        ['list_id'],
        unique=False,
    )
    op.create_index(
        op.f('ix_sourced_list_books_book_id'),
        'sourced_list_books',
        ['book_id'],
        unique=False,
    )

    # Copia les dades actuals de La Central a les taules genèriques.
    op.execute(
        sa.text(
            """
            INSERT INTO sourced_lists
                (source, slug, url, tipo, titulo, subtitulo, intro, autor,
                 fecha, cuerpo, portada_url, status, fetched_at)
            SELECT
                'lacentral', slug, url, tipo, titulo, subtitulo, intro, autor,
                fecha, cuerpo, portada_url, status, fetched_at
            FROM central_blog_article
            """
        )
    )
    op.execute(
        sa.text(
            """
            INSERT INTO sourced_list_books
                (list_id, posicion, titulo_normalizado, autor_normalizado, book_id)
            SELECT
                src.id, cb.posicion, cb.titulo_normalizado, cb.autor_normalizado, cb.book_id
            FROM central_blog_article_book cb
            JOIN central_blog_article old ON old.id = cb.article_id
            JOIN sourced_lists src ON src.source = 'lacentral' AND src.slug = old.slug
            """
        )
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index(
        op.f('ix_sourced_list_books_book_id'),
        table_name='sourced_list_books',
    )
    op.drop_index(
        op.f('ix_sourced_list_books_list_id'),
        table_name='sourced_list_books',
    )
    op.drop_table('sourced_list_books')
    op.drop_index(
        op.f('ix_sourced_lists_slug'),
        table_name='sourced_lists',
    )
    op.drop_table('sourced_lists')