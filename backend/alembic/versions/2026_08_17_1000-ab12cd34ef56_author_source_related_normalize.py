"""normalize author_source related articles into 1-many table

Revision ID: ab12cd34ef56
Revises: fd0a1b2c3d4e
Create Date: 2026-08-17 10:00:00

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = 'ab12cd34ef56'
down_revision: Union[str, Sequence[str], None] = 'fd0a1b2c3d4e'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Normalitza `author_source.extra` (JSONB) a la taula 1:molts
    `author_source_related` i retira les taules staging antigues."""
    op.create_table(
        'author_source_related',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('author_key', sa.String(), nullable=False),
        sa.Column('editorial', sa.String(), nullable=False),
        sa.Column('posicion', sa.Integer(), nullable=False),
        sa.Column('tipo', sa.String(), nullable=True),
        sa.Column('titulo', sa.String(), nullable=True),
        sa.Column('url', sa.String(), nullable=True),
        sa.Column('fecha', sa.String(), nullable=True),
        sa.Column('descripcion', sa.String(), nullable=True),
        sa.Column('thumbnail', sa.String(), nullable=True),
        sa.Column('categoria', sa.String(), nullable=True),
        sa.ForeignKeyConstraint(
            ['author_key', 'editorial'],
            ['author_source.author_key', 'author_source.editorial'],
            name='fk_author_source_related_author_key_editorial',
            ondelete='CASCADE',
        ),
    )
    op.create_index(
        'ix_author_source_related_author_key',
        'author_source_related',
        ['author_key'],
    )

    # Rellena desde `extra` (solo arrays; null/JSON null se ignoran).
    bind = op.get_bind()
    bind.execute(
        sa.text(
            """
            INSERT INTO author_source_related
                (author_key, editorial, posicion, tipo, titulo, url, fecha,
                 descripcion, thumbnail, categoria)
            SELECT s.author_key, s.editorial, ord - 1,
                   item ->> 'tipo', item ->> 'titulo', item ->> 'url',
                   item ->> 'fecha', item ->> 'descripcion', item ->> 'thumbnail',
                   item ->> 'categoria'
            FROM author_source s,
                 LATERAL jsonb_array_elements(s.extra) WITH ORDINALITY AS t(item, ord)
            WHERE jsonb_typeof(s.extra) = 'array'
            """
        )
    )

    op.drop_column('author_source', 'extra')
    op.drop_table('authors_anagrama')
    op.drop_table('authors_blackie')


def downgrade() -> None:
    """Restaura `extra` a partir de `author_source_related` y las staging tables."""
    op.create_table(
        'authors_blackie',
        sa.Column('slug', sa.String(), nullable=False),
        sa.Column('name', sa.String(), nullable=False),
        sa.Column('description', sa.String(), nullable=True),
        sa.Column('image_url', sa.String(), nullable=True),
        sa.Column('fetched_at', sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint('slug'),
    )
    op.create_table(
        'authors_anagrama',
        sa.Column('slug', sa.String(), nullable=False),
        sa.Column('name', sa.String(), nullable=False),
        sa.Column('description', sa.String(), nullable=True),
        sa.Column('image_url', sa.String(), nullable=True),
        sa.Column('extra', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('fetched_at', sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint('slug'),
    )

    op.add_column(
        'author_source',
        sa.Column('extra', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
    )
    bind = op.get_bind()
    bind.execute(
        sa.text(
            """
            UPDATE author_source s
            SET extra = sub.items
            FROM (
                SELECT r.author_key, r.editorial,
                       jsonb_agg(
                           jsonb_build_object(
                               'tipo', r.tipo,
                               'titulo', r.titulo,
                               'url', r.url,
                               'fecha', r.fecha,
                               'descripcion', r.descripcion,
                               'thumbnail', r.thumbnail,
                               'categoria', r.categoria
                           )
                           ORDER BY r.posicion
                       ) AS items
                FROM author_source_related r
                GROUP BY r.author_key, r.editorial
            ) AS sub
            WHERE s.author_key = sub.author_key AND s.editorial = sub.editorial
            """
        )
    )

    op.drop_index('ix_author_source_related_author_key', table_name='author_source_related')
    op.drop_table('author_source_related')