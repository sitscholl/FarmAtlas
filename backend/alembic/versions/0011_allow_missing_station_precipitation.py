"""Allow missing station precipitation.

Revision ID: 0011_allow_missing_station_precipitation
Revises: 0010_fruit_counts_and_yearly_stats
Create Date: 2026-06-21 00:00:00
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "0011_allow_missing_station_precipitation"
down_revision = "0010_fruit_counts_and_yearly_stats"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("station_weather_hourly") as batch_op:
        batch_op.alter_column(
            "precipitation",
            existing_type=sa.Float(),
            nullable=True,
        )


def downgrade() -> None:
    op.execute("UPDATE station_weather_hourly SET precipitation = 0.0 WHERE precipitation IS NULL")
    with op.batch_alter_table("station_weather_hourly") as batch_op:
        batch_op.alter_column(
            "precipitation",
            existing_type=sa.Float(),
            nullable=False,
        )
