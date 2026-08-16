"""recreate seed_aladi with adreca, codi_postal, id_establishment

Revision ID: ff1122334455
Revises: 637773d1ff90
Create Date: 2026-08-13 09:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "ff1122334455"
down_revision: Union[str, Sequence[str], None] = "637773d1ff90"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Borra i recrea seed_aladi amb els nous camps."""
    op.drop_table("seed_aladi")
    op.create_table(
        "seed_aladi",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("punt_id", sa.String(), nullable=False),
        sa.Column("nom", sa.String(), nullable=True),
        sa.Column("municipi", sa.String(), nullable=True),
        sa.Column("adreca", sa.String(), nullable=True),
        sa.Column("codi_postal", sa.String(), nullable=True),
        sa.Column("lat", sa.Float(), nullable=True),
        sa.Column("lon", sa.Float(), nullable=True),
        sa.Column("id_establishment", sa.Integer(), nullable=True),
        sa.Column("dades", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("punt_id"),
    )
    op.create_index(
        "ix_seed_aladi_id_establishment", "seed_aladi", ["id_establishment"]
    )
    op.create_foreign_key(
        "fk_seed_aladi_id_establishment_establishments",
        "seed_aladi",
        "establishments",
        ["id_establishment"],
        ["id"],
    )


def downgrade() -> None:
    """Torna a la versió anterior (només punt_id, nom, municipi, lat, lon, dades)."""
    op.drop_constraint(
        "fk_seed_aladi_id_establishment_establishments", "seed_aladi", type_="foreignkey"
    )
    op.drop_index("ix_seed_aladi_id_establishment", table_name="seed_aladi")
    op.drop_table("seed_aladi")
    op.create_table(
        "seed_aladi",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("punt_id", sa.String(), nullable=False),
        sa.Column("nom", sa.String(), nullable=True),
        sa.Column("municipi", sa.String(), nullable=True),
        sa.Column("lat", sa.Float(), nullable=True),
        sa.Column("lon", sa.Float(), nullable=True),
        sa.Column("dades", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("punt_id"),
    )