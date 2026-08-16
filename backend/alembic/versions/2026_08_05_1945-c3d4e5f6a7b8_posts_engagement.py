"""posts & engagement: posts, post_media, post_likes, comments, comment_likes, mentions

Revision ID: c3d4e5f6a7b8
Revises: b2c3d4e5f6a7
Create Date: 2026-08-05 19:45:00.000000

Añade el contexto POSTS & ENGAGEMENT (FASE 6) de forma aditiva:
- `posts` (publicaciones, book_id RESTRICT al catálogo, soft delete ADR-8)
- `post_media` (attachments), `post_likes` (UNIQUE user+post)
- `comments` (anidado 1 nivel), `comment_likes` (UNIQUE user+comment)
- `mentions` (mención en post/comentario, content polimórfico sin FK)

No modifica ninguna tabla existente. Tipos enum nuevos (`post_type`,
`media_type`, `mention_target`); `visibility` ya existía (FASE 1).
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = 'c3d4e5f6a7b8'
down_revision: Union[str, Sequence[str], None] = 'b2c3d4e5f6a7'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

_VISIBILITY = ('PUBLIC', 'FOLLOWERS', 'PRIVATE')
_POST_TYPE = ('TEXT', 'BOOK_SHARE', 'MEDIA')
_MEDIA_TYPE = ('IMAGE', 'VIDEO', 'AUDIO')
_MENTION_TARGET = ('POST', 'COMMENT')


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        'posts',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('author_id', sa.UUID(), nullable=False),
        sa.Column('type', sa.Enum(*_POST_TYPE, name='post_type'), nullable=False),
        sa.Column('body', sa.Text(), nullable=False),
        sa.Column('book_id', sa.Integer(), nullable=True),
        sa.Column('review_id', sa.UUID(), nullable=True),
        sa.Column('visibility', postgresql.ENUM(*_VISIBILITY, name='visibility', create_type=False), nullable=False),
        sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['author_id'], ['users.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['book_id'], ['books.id'], ondelete='RESTRICT'),
        sa.ForeignKeyConstraint(['review_id'], ['reviews.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(
        'ix_posts_author_created',
        'posts',
        ['author_id', sa.text('created_at DESC')],
        unique=False,
    )
    op.create_index('ix_posts_book_id', 'posts', ['book_id'], unique=False)
    op.create_index('ix_posts_review_id', 'posts', ['review_id'], unique=False)

    op.create_table(
        'post_media',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('post_id', sa.UUID(), nullable=False),
        sa.Column('media_type', sa.Enum(*_MEDIA_TYPE, name='media_type'), nullable=False),
        sa.Column('url', sa.String(length=500), nullable=False),
        sa.Column('position', sa.Integer(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['post_id'], ['posts.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('post_id', 'position', name='uq_post_media_post_position'),
    )
    op.create_index('ix_post_media_post', 'post_media', ['post_id', 'position'], unique=False)

    op.create_table(
        'post_likes',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('user_id', sa.UUID(), nullable=False),
        sa.Column('post_id', sa.UUID(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['post_id'], ['posts.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('user_id', 'post_id', name='uq_post_likes_user_post'),
    )
    op.create_index('ix_post_likes_post', 'post_likes', ['post_id'], unique=False)
    op.create_index('ix_post_likes_user', 'post_likes', ['user_id'], unique=False)

    op.create_table(
        'comments',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('post_id', sa.UUID(), nullable=False),
        sa.Column('parent_id', sa.UUID(), nullable=True),
        sa.Column('author_id', sa.UUID(), nullable=False),
        sa.Column('body', sa.Text(), nullable=False),
        sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['author_id'], ['users.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['parent_id'], ['comments.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['post_id'], ['posts.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(
        'ix_comments_post_created',
        'comments',
        ['post_id', sa.text('created_at ASC')],
        unique=False,
    )
    op.create_index('ix_comments_parent', 'comments', ['parent_id'], unique=False)

    op.create_table(
        'comment_likes',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('user_id', sa.UUID(), nullable=False),
        sa.Column('comment_id', sa.UUID(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['comment_id'], ['comments.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('user_id', 'comment_id', name='uq_comment_likes_user_comment'),
    )
    op.create_index('ix_comment_likes_comment', 'comment_likes', ['comment_id'], unique=False)
    op.create_index('ix_comment_likes_user', 'comment_likes', ['user_id'], unique=False)

    op.create_table(
        'mentions',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('content_type', sa.Enum(*_MENTION_TARGET, name='mention_target'), nullable=False),
        sa.Column('content_id', sa.UUID(), nullable=False),
        sa.Column('mentioned_user_id', sa.UUID(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['mentioned_user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint(
            'content_type', 'content_id', 'mentioned_user_id',
            name='uq_mentions_content_user',
        ),
    )
    op.create_index('ix_mentions_mentioned', 'mentions', ['mentioned_user_id'], unique=False)
    op.create_index(
        'ix_mentions_content', 'mentions', ['content_type', 'content_id'], unique=False
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index('ix_mentions_content', table_name='mentions')
    op.drop_index('ix_mentions_mentioned', table_name='mentions')
    op.drop_table('mentions')
    op.execute('DROP TYPE IF EXISTS mention_target')
    op.drop_index('ix_comment_likes_user', table_name='comment_likes')
    op.drop_index('ix_comment_likes_comment', table_name='comment_likes')
    op.drop_table('comment_likes')
    op.drop_index('ix_comments_parent', table_name='comments')
    op.drop_index('ix_comments_post_created', table_name='comments')
    op.drop_table('comments')
    op.drop_index('ix_post_likes_user', table_name='post_likes')
    op.drop_index('ix_post_likes_post', table_name='post_likes')
    op.drop_table('post_likes')
    op.drop_index('ix_post_media_post', table_name='post_media')
    op.drop_table('post_media')
    op.execute('DROP TYPE IF EXISTS media_type')
    op.drop_index('ix_posts_review_id', table_name='posts')
    op.drop_index('ix_posts_book_id', table_name='posts')
    op.drop_index('ix_posts_author_created', table_name='posts')
    op.drop_table('posts')
    op.execute('DROP TYPE IF EXISTS post_type')
