"""Remove station weather et0 and add station metadata.

Revision ID: 0008_remove_station_weather_et0_add_metadata
Revises: 0007_remove_station_weather_et0_corrected
Create Date: 2026-06-15 00:00:00
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "0008_remove_station_weather_et0_add_metadata"
down_revision = "0007_remove_station_weather_et0_corrected"
branch_labels = None
depends_on = None


def _has_column(table_name: str, column_name: str) -> bool:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    return any(column["name"] == column_name for column in inspector.get_columns(table_name))


def _has_table(table_name: str) -> bool:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    return table_name in inspector.get_table_names()


def upgrade() -> None:
    if _has_column("station_weather_hourly", "et0"):
        with op.batch_alter_table("station_weather_hourly") as batch_op:
            batch_op.drop_column("et0")

    if not _has_table("station_weather_metadata"):
        op.create_table(
            "station_weather_metadata",
            sa.Column("source_provider", sa.String(), nullable=False),
            sa.Column("source_station", sa.String(), nullable=False),
            sa.Column("longitude", sa.Float(), nullable=False),
            sa.Column("latitude", sa.Float(), nullable=False),
            sa.Column("crs", sa.Integer(), nullable=False),
            sa.Column("elevation", sa.Float(), nullable=True),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
            sa.PrimaryKeyConstraint("source_provider", "source_station"),
        )


def downgrade() -> None:
    if _has_table("station_weather_metadata"):
        op.drop_table("station_weather_metadata")

    if not _has_column("station_weather_hourly", "et0"):
        with op.batch_alter_table("station_weather_hourly") as batch_op:
            batch_op.add_column(sa.Column("et0", sa.Float(), nullable=True))
