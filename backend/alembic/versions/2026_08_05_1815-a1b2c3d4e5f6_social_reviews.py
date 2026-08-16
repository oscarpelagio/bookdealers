"""social reviews: ratings, reviews, review_likes + contadores en books

Revision ID: a1b2c3d4e5f6
Revises: 9c8d7e6f5a4b
Create Date: 2026-08-05 18:15:00.000000

Añade el contexto REVIEWS / RATINGS (FASE 3) de forma aditiva:
- `ratings`, `reviews`, `review_likes`
- columnas denormalizadas en `books` (rating_avg/rating_count/review_count,
  ADR-9) + backfill de recálculo
- índice parcial de unicidad (user_id, book_id) sobre reviews ACTIVAS
  (permite re-review tras soft delete)

`book_id` referencia `books.id` (INT) con ON DELETE RESTRICT: no se toca
el catálogo.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy import text

# revision identifiers, used by Alembic.
revision: str = 'a1b2c3d4e5f6'
down_revision: Union[str, Sequence[str], None] = '9c8d7e6f5a4b'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # --- Contadores denormalizados en books (ADR-9), aditivo ---
    op.add_column('books', sa.Column('rating_avg', sa.Numeric(3, 2), nullable=True))
    op.add_column(
        'books',
        sa.Column('rating_count', sa.Integer(), nullable=False, server_default='0'),
    )
    op.add_column(
        'books',
        sa.Column('review_count', sa.Integer(), nullable=False, server_default='0'),
    )

    # --- ratings ---
    op.create_table(
        'ratings',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('user_id', sa.UUID(), nullable=False),
        sa.Column('book_id', sa.Integer(), nullable=False),
        sa.Column('score', sa.SmallInteger(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint('score BETWEEN 1 AND 5', name='ck_ratings_score_range'),
        sa.ForeignKeyConstraint(['book_id'], ['books.id'], ondelete='RESTRICT'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('user_id', 'book_id', name='uq_ratings_user_book'),
    )
    op.create_index('ix_ratings_book_id', 'ratings', ['book_id'], unique=False)
    op.create_index('ix_ratings_user_id', 'ratings', ['user_id'], unique=False)

    # --- reviews ---
    op.create_table(
        'reviews',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('user_id', sa.UUID(), nullable=False),
        sa.Column('book_id', sa.Integer(), nullable=False),
        sa.Column('title', sa.String(length=200), nullable=True),
        sa.Column('body', sa.Text(), nullable=True),
        sa.Column('rating_id', sa.UUID(), nullable=True),
        sa.Column('language', sa.String(length=10), nullable=True),
        sa.Column('spoiler', sa.Boolean(), nullable=False),
        sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['book_id'], ['books.id'], ondelete='RESTRICT'),
        sa.ForeignKeyConstraint(['rating_id'], ['ratings.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(
        'ix_reviews_book_created',
        'reviews',
        ['book_id', sa.text('created_at DESC')],
        unique=False,
    )
    op.create_index('ix_reviews_user_id', 'reviews', ['user_id'], unique=False)
    op.create_index(
        'ix_reviews_rating_id', 'reviews', ['rating_id'], unique=True
    )
    op.create_index(
        'ix_reviews_active_user_book',
        'reviews',
        ['user_id', 'book_id'],
        unique=True,
        postgresql_where=text('deleted_at IS NULL'),
    )

    # --- review_likes ---
    op.create_table(
        'review_likes',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('user_id', sa.UUID(), nullable=False),
        sa.Column('review_id', sa.UUID(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['review_id'], ['reviews.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('user_id', 'review_id', name='uq_review_likes_user_review'),
    )
    op.create_index(
        'ix_review_likes_review_id', 'review_likes', ['review_id'], unique=False
    )
    op.create_index(
        'ix_review_likes_user_id', 'review_likes', ['user_id'], unique=False
    )

    # --- Backfill de contadores (no hay reviews previas; patrón de recálculo) ---
    op.execute(
        """
        UPDATE books b SET
            rating_count = COALESCE(
                (SELECT count(*) FROM ratings r WHERE r.book_id = b.id), 0),
            rating_avg = (
                SELECT round(avg(r.score)::numeric, 2)
                FROM ratings r WHERE r.book_id = b.id),
            review_count = COALESCE(
                (SELECT count(*) FROM reviews rv
                 WHERE rv.book_id = b.id AND rv.deleted_at IS NULL), 0)
        """
    )
    # Los defaults viven en el modelo (Python side); se quita el server_default.
    op.alter_column('books', 'rating_count', server_default=None)
    op.alter_column('books', 'review_count', server_default=None)


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index('ix_review_likes_user_id', table_name='review_likes')
    op.drop_index('ix_review_likes_review_id', table_name='review_likes')
    op.drop_table('review_likes')
    op.drop_index('ix_reviews_active_user_book', table_name='reviews')
    op.drop_index('ix_reviews_rating_id', table_name='reviews')
    op.drop_index('ix_reviews_user_id', table_name='reviews')
    op.drop_index('ix_reviews_book_created', table_name='reviews')
    op.drop_table('reviews')
    op.drop_index('ix_ratings_user_id', table_name='ratings')
    op.drop_index('ix_ratings_book_id', table_name='ratings')
    op.drop_table('ratings')
    op.drop_column('books', 'review_count')
    op.drop_column('books', 'rating_count')
    op.drop_column('books', 'rating_avg')
