"""Remove field-specific corrected ET from station weather cache.

Revision ID: 0007_remove_station_weather_et0_corrected
Revises: 0006_station_weather_hourly
Create Date: 2026-06-14 00:00:00
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "0007_remove_station_weather_et0_corrected"
down_revision = "0006_station_weather_hourly"
branch_labels = None
depends_on = None


def _has_column(table_name: str, column_name: str) -> bool:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    return any(column["name"] == column_name for column in inspector.get_columns(table_name))


def upgrade() -> None:
    if _has_column("station_weather_hourly", "et0_corrected"):
        with op.batch_alter_table("station_weather_hourly") as batch_op:
            batch_op.drop_column("et0_corrected")


def downgrade() -> None:
    if not _has_column("station_weather_hourly", "et0_corrected"):
        with op.batch_alter_table("station_weather_hourly") as batch_op:
            batch_op.add_column(sa.Column("et0_corrected", sa.Float(), nullable=True))
