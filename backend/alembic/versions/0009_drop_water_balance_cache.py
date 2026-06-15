"""Drop persisted water balance cache.

Revision ID: 0009_drop_water_balance_cache
Revises: 0008_remove_station_weather_et0_add_metadata
Create Date: 2026-06-15 00:00:00
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "0009_drop_water_balance_cache"
down_revision = "0008_remove_station_weather_et0_add_metadata"
branch_labels = None
depends_on = None


def _has_table(table_name: str) -> bool:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    return table_name in inspector.get_table_names()


def upgrade() -> None:
    if _has_table("water_balance"):
        op.drop_table("water_balance")


def downgrade() -> None:
    if not _has_table("water_balance"):
        op.create_table(
            "water_balance",
            sa.Column("date", sa.Date(), nullable=False),
            sa.Column("field_id", sa.Integer(), nullable=False),
            sa.Column("precipitation", sa.Float(), nullable=False),
            sa.Column("irrigation", sa.Float(), nullable=False),
            sa.Column("evapotranspiration", sa.Float(), nullable=False),
            sa.Column("incoming", sa.Float(), nullable=False),
            sa.Column("net", sa.Float(), nullable=False),
            sa.Column("soil_water_content", sa.Float(), nullable=False),
            sa.Column("available_water_storage", sa.Float(), nullable=False),
            sa.Column("water_deficit", sa.Float(), nullable=False),
            sa.Column("readily_available_water", sa.Float(), nullable=True),
            sa.Column("safe_ratio", sa.Float(), nullable=True),
            sa.Column("below_raw", sa.Boolean(), nullable=True),
            sa.ForeignKeyConstraint(["field_id"], ["fields.id"]),
            sa.PrimaryKeyConstraint("date", "field_id"),
            sa.UniqueConstraint("field_id", "date", name="uq_waterbalance_field_date"),
        )
