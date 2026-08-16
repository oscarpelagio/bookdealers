"""notifications: notifications, notification_settings, push_queue

Revision ID: e5f6a7b8c9d0
Revises: d4e5f6a7b8c9
Create Date: 2026-08-05 20:40:00.000000

Añade el contexto NOTIFICATIONS (FASE 8) de forma aditiva:
- `notifications` (bandeja, actor SET NULL, object polimórfico sin FK)
- `notification_settings` (1:1 por usuario, excepciones JSONB)
- `push_queue` (cola técnica EMAIL/PUSH para un worker posterior)

No modifica ninguna tabla existente. Tipos enum nuevos
(`notification_type`, `channel`, `push_status`); `object_type` y
`visibility` ya existían (FASE 4 / FASE 1).
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = 'e5f6a7b8c9d0'
down_revision: Union[str, Sequence[str], None] = 'd4e5f6a7b8c9'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

_NOTIFICATION_TYPE = (
    'FOLLOW', 'REVIEW_LIKE', 'COMMENT', 'MENTION', 'POST_LIKE',
    'POST_ON_BOOK', 'GOAL', 'SYSTEM',
)
_CHANNEL = ('INBOX', 'EMAIL', 'PUSH')
_PUSH_STATUS = ('PENDING', 'SENT', 'FAILED', 'CANCELLED')


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        'notifications',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('recipient_id', sa.UUID(), nullable=False),
        sa.Column('actor_id', sa.UUID(), nullable=True),
        sa.Column('type', sa.Enum(*_NOTIFICATION_TYPE, name='notification_type'), nullable=False),
        sa.Column('object_type', postgresql.ENUM('POST', 'COMMENT', 'REVIEW', 'RATING', 'BOOK', 'GOAL', 'USER_BOOK', name='object_type', create_type=False), nullable=True),
        sa.Column('object_id', sa.UUID(), nullable=True),
        sa.Column('message', sa.Text(), nullable=True),
        sa.Column('read_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['actor_id'], ['users.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['recipient_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(
        'ix_notifications_recipient_read',
        'notifications',
        ['recipient_id', 'read_at'],
        unique=False,
    )
    op.create_index(
        'ix_notifications_recipient_unread',
        'notifications',
        ['recipient_id', sa.text('created_at DESC')],
        unique=False,
        postgresql_where=sa.text('read_at IS NULL'),
    )
    op.create_index(
        'ix_notifications_created',
        'notifications',
        [sa.text('created_at DESC')],
        unique=False,
    )

    op.create_table(
        'notification_settings',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('user_id', sa.UUID(), nullable=False),
        sa.Column('email_digest_enabled', sa.Boolean(), nullable=False),
        sa.Column('in_app_master', sa.Boolean(), nullable=False),
        sa.Column('exceptions', postgresql.JSONB(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('user_id', name='uq_notification_settings_user'),
    )
    op.create_index('ix_notification_settings_user', 'notification_settings', ['user_id'], unique=False)

    op.create_table(
        'push_queue',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('user_id', sa.UUID(), nullable=False),
        sa.Column('channel', sa.Enum(*_CHANNEL, name='channel'), nullable=False),
        sa.Column('payload', postgresql.JSONB(), nullable=False),
        sa.Column('status', sa.Enum(*_PUSH_STATUS, name='push_status'), nullable=False),
        sa.Column('attempts', sa.Integer(), nullable=False),
        sa.Column('next_attempt_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('sent_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(
        'ix_push_queue_status_next', 'push_queue', ['status', 'next_attempt_at'],
        unique=False,
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index('ix_push_queue_status_next', table_name='push_queue')
    op.drop_table('push_queue')
    op.execute('DROP TYPE IF EXISTS push_status')
    op.execute('DROP TYPE IF EXISTS channel')
    op.drop_index('ix_notification_settings_user', table_name='notification_settings')
    op.drop_table('notification_settings')
    op.drop_index('ix_notifications_created', table_name='notifications')
    op.drop_index('ix_notifications_recipient_unread', table_name='notifications')
    op.drop_index('ix_notifications_recipient_read', table_name='notifications')
    op.drop_table('notifications')
    op.execute('DROP TYPE IF EXISTS notification_type')
