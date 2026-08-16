"""social profiles: profiles, preferences, privacy, reading goals

Revision ID: 5f7a9c2d4e1b
Revises: e02b4ebf937f
Create Date: 2026-08-05 16:30:00.000000

Añade el contexto PROFILES (FASE 1) de forma aditiva:
- `profiles`, `profile_preferences`, `privacy_settings`, `reading_goals`
- enum `visibility`
- backfill de perfiles/privacidad/preferencias para los usuarios existentes

No modifica ninguna tabla del catálogo/availability/auth existente.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = '5f7a9c2d4e1b'
down_revision: Union[str, Sequence[str], None] = 'e02b4ebf937f'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


_VISIBILITY = ('PUBLIC', 'FOLLOWERS', 'PRIVATE')


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        'profiles',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('user_id', sa.UUID(), nullable=False),
        sa.Column('display_name', sa.String(length=120), nullable=True),
        sa.Column('bio', sa.String(length=500), nullable=True),
        sa.Column('location', sa.String(length=120), nullable=True),
        sa.Column('website', sa.String(length=500), nullable=True),
        sa.Column('avatar_url', sa.String(length=500), nullable=True),
        sa.Column('cover_url', sa.String(length=500), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_profiles_user_id', 'profiles', ['user_id'], unique=True)

    op.create_table(
        'profile_preferences',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('user_id', sa.UUID(), nullable=False),
        sa.Column('language', sa.String(length=10), nullable=True),
        sa.Column(
            'default_review_visibility',
            sa.Enum(*_VISIBILITY, name='visibility'),
            nullable=False,
        ),
        sa.Column('reading_tracking_enabled', sa.Boolean(), nullable=False),
        sa.Column('content_languages', sa.ARRAY(sa.String(length=10)), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(
        'ix_profile_preferences_user_id',
        'profile_preferences',
        ['user_id'],
        unique=True,
    )

    op.create_table(
        'privacy_settings',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('user_id', sa.UUID(), nullable=False),
        sa.Column(
            'profile_visibility',
            sa.Enum(*_VISIBILITY, name='visibility'),
            nullable=False,
        ),
        sa.Column(
            'library_visibility',
            sa.Enum(*_VISIBILITY, name='visibility'),
            nullable=False,
        ),
        sa.Column(
            'reviews_visibility',
            sa.Enum(*_VISIBILITY, name='visibility'),
            nullable=False,
        ),
        sa.Column(
            'lists_visibility',
            sa.Enum(*_VISIBILITY, name='visibility'),
            nullable=False,
        ),
        sa.Column(
            'activity_visibility',
            sa.Enum(*_VISIBILITY, name='visibility'),
            nullable=False,
        ),
        sa.Column('allow_follows', sa.Boolean(), nullable=False),
        sa.Column('show_reading_progress', sa.Boolean(), nullable=False),
        sa.Column('block_anonymous', sa.Boolean(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(
        'ix_privacy_settings_user_id', 'privacy_settings', ['user_id'], unique=True
    )

    op.create_table(
        'reading_goals',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('user_id', sa.UUID(), nullable=False),
        sa.Column('year', sa.Integer(), nullable=False),
        sa.Column('books_goal', sa.Integer(), nullable=True),
        sa.Column('pages_goal', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('user_id', 'year', name='uq_reading_goals_user_year'),
    )
    op.create_index(
        'ix_reading_goals_user_id', 'reading_goals', ['user_id'], unique=False
    )

    # Backfill: perfil/privacidad/preferencias por defecto para los usuarios
    # existentes (los nuevos se crean de forma perezosa en el servicio).
    op.execute(
        """
        INSERT INTO profiles (id, user_id, display_name, created_at, updated_at)
        SELECT gen_random_uuid(), u.id, u.full_name, u.created_at, u.updated_at
        FROM users u
        ON CONFLICT (user_id) DO NOTHING
        """
    )
    op.execute(
        """
        INSERT INTO privacy_settings (id, user_id, profile_visibility,
            library_visibility, reviews_visibility, lists_visibility,
            activity_visibility, allow_follows, show_reading_progress,
            block_anonymous, created_at, updated_at)
        SELECT gen_random_uuid(), u.id, 'PUBLIC', 'PUBLIC', 'PUBLIC', 'PUBLIC',
            'PUBLIC', TRUE, TRUE, FALSE, u.created_at, u.updated_at
        FROM users u
        ON CONFLICT (user_id) DO NOTHING
        """
    )
    op.execute(
        """
        INSERT INTO profile_preferences (id, user_id, language,
            default_review_visibility, reading_tracking_enabled,
            content_languages, created_at, updated_at)
        SELECT gen_random_uuid(), u.id, NULL, 'PUBLIC', TRUE, NULL,
            u.created_at, u.updated_at
        FROM users u
        ON CONFLICT (user_id) DO NOTHING
        """
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index('ix_reading_goals_user_id', table_name='reading_goals')
    op.drop_table('reading_goals')
    op.drop_index('ix_privacy_settings_user_id', table_name='privacy_settings')
    op.drop_table('privacy_settings')
    op.drop_index('ix_profile_preferences_user_id', table_name='profile_preferences')
    op.drop_table('profile_preferences')
    op.drop_index('ix_profiles_user_id', table_name='profiles')
    op.drop_table('profiles')
    op.execute('DROP TYPE IF EXISTS visibility')
