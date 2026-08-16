"""social graph: follows, blocks, mutes, reports, activities

Revision ID: b2c3d4e5f6a7
Revises: a1b2c3d4e5f6
Create Date: 2026-08-05 19:15:00.000000

Añade el contexto SOCIAL GRAPH (FASE 4) de forma aditiva:
- `follows`, `blocks`, `mutes` (relaciones entre usuarios, self-N:N)
- `reports` (moderación, target polimórfico sin FK)
- `activities` (log append-only de UX, visibility copiada del actor)

No modifica ninguna tabla existente. Los tipos enum nuevos
(`report_target`, `report_status`, `activity_verb`, `object_type`) se crean
aquí; `visibility` ya existía (FASE 1).
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = 'b2c3d4e5f6a7'
down_revision: Union[str, Sequence[str], None] = 'a1b2c3d4e5f6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

_VISIBILITY = ('PUBLIC', 'FOLLOWERS', 'PRIVATE')
_REPORT_TARGET = ('USER', 'POST', 'COMMENT', 'REVIEW', 'LIST')
_REPORT_STATUS = ('OPEN', 'REVIEWING', 'RESOLVED', 'DISMISSED')
_ACTIVITY_VERB = (
    'SHELF_UPDATED', 'RATING_ADDED', 'REVIEW_ADDED', 'FOLLOWED',
    'POST', 'COMMENTED', 'LIST_CREATED', 'GOAL_UPDATED', 'JOINED',
)
_OBJECT_TYPE = ('POST', 'COMMENT', 'REVIEW', 'RATING', 'BOOK', 'GOAL', 'USER_BOOK')


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        'follows',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('follower_id', sa.UUID(), nullable=False),
        sa.Column('followee_id', sa.UUID(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint('follower_id <> followee_id', name='ck_follows_no_self'),
        sa.ForeignKeyConstraint(['followee_id'], ['users.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['follower_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('follower_id', 'followee_id', name='uq_follows_follower_followee'),
    )
    op.create_index('ix_follows_followee', 'follows', ['followee_id'], unique=False)
    op.create_index('ix_follows_follower', 'follows', ['follower_id'], unique=False)

    op.create_table(
        'blocks',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('blocker_id', sa.UUID(), nullable=False),
        sa.Column('blocked_id', sa.UUID(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint('blocker_id <> blocked_id', name='ck_blocks_no_self'),
        sa.ForeignKeyConstraint(['blocked_id'], ['users.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['blocker_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('blocker_id', 'blocked_id', name='uq_blocks_blocker_blocked'),
    )
    op.create_index('ix_blocks_blocked', 'blocks', ['blocked_id'], unique=False)
    op.create_index('ix_blocks_blocker', 'blocks', ['blocker_id'], unique=False)

    op.create_table(
        'mutes',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('muter_id', sa.UUID(), nullable=False),
        sa.Column('mutee_id', sa.UUID(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint('muter_id <> mutee_id', name='ck_mutes_no_self'),
        sa.ForeignKeyConstraint(['mutee_id'], ['users.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['muter_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('muter_id', 'mutee_id', name='uq_mutes_muter_mutee'),
    )
    op.create_index('ix_mutes_mutee', 'mutes', ['mutee_id'], unique=False)
    op.create_index('ix_mutes_muter', 'mutes', ['muter_id'], unique=False)

    op.create_table(
        'reports',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('reporter_id', sa.UUID(), nullable=False),
        sa.Column('target_type', sa.Enum(*_REPORT_TARGET, name='report_target'), nullable=False),
        sa.Column('target_id', sa.UUID(), nullable=False),
        sa.Column('reason', sa.String(length=200), nullable=False),
        sa.Column('details', sa.Text(), nullable=True),
        sa.Column('status', sa.Enum(*_REPORT_STATUS, name='report_status'), nullable=False),
        sa.Column('resolved_by', sa.UUID(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('resolved_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['reporter_id'], ['users.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['resolved_by'], ['users.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_reports_status', 'reports', ['status'], unique=False)
    op.create_index(
        'ix_reports_target', 'reports', ['target_type', 'target_id'], unique=False
    )

    op.create_table(
        'activities',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('actor_id', sa.UUID(), nullable=True),
        sa.Column('verb', sa.Enum(*_ACTIVITY_VERB, name='activity_verb'), nullable=False),
        sa.Column('object_type', sa.Enum(*_OBJECT_TYPE, name='object_type'), nullable=True),
        sa.Column('object_id', sa.UUID(), nullable=True),
        sa.Column('target_type', sa.String(length=30), nullable=True),
        sa.Column('target_id', sa.UUID(), nullable=True),
        sa.Column('visibility', postgresql.ENUM(*_VISIBILITY, name='visibility', create_type=False), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['actor_id'], ['users.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(
        'ix_activities_actor_created',
        'activities',
        ['actor_id', sa.text('created_at DESC')],
        unique=False,
    )
    op.create_index(
        'ix_activities_public',
        'activities',
        [sa.text('created_at DESC')],
        unique=False,
        postgresql_where=sa.text("visibility = 'PUBLIC'"),
    )
    op.create_index(
        'ix_activities_object',
        'activities',
        ['object_type', 'object_id'],
        unique=False,
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index('ix_activities_object', table_name='activities')
    op.drop_index('ix_activities_public', table_name='activities')
    op.drop_index('ix_activities_actor_created', table_name='activities')
    op.drop_table('activities')
    op.execute('DROP TYPE IF EXISTS object_type')
    op.execute('DROP TYPE IF EXISTS activity_verb')
    op.drop_index('ix_reports_target', table_name='reports')
    op.drop_index('ix_reports_status', table_name='reports')
    op.drop_table('reports')
    op.execute('DROP TYPE IF EXISTS report_status')
    op.execute('DROP TYPE IF EXISTS report_target')
    op.drop_index('ix_mutes_muter', table_name='mutes')
    op.drop_index('ix_mutes_mutee', table_name='mutes')
    op.drop_table('mutes')
    op.drop_index('ix_blocks_blocker', table_name='blocks')
    op.drop_index('ix_blocks_blocked', table_name='blocks')
    op.drop_table('blocks')
    op.drop_index('ix_follows_follower', table_name='follows')
    op.drop_index('ix_follows_followee', table_name='follows')
    op.drop_table('follows')
