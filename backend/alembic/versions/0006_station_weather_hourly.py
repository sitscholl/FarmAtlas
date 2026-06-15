"""Replace field daily weather cache with station hourly cache.

Revision ID: 0006_station_weather_hourly
Revises: 0005_remove_crop_protection_target
Create Date: 2026-06-11 00:00:00
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "0006_station_weather_hourly"
down_revision = "0005_remove_crop_protection_target"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.drop_table("field_weather_daily")
    op.create_table(
        "station_weather_hourly",
        sa.Column("source_provider", sa.String(), nullable=False),
        sa.Column("source_station", sa.String(), nullable=False),
        sa.Column("timestamp", sa.DateTime(timezone=True), nullable=False),
        sa.Column("precipitation", sa.Float(), nullable=False),
        sa.Column("tair_2m", sa.Float(), nullable=True),
        sa.Column("relative_humidity", sa.Float(), nullable=True),
        sa.Column("wind_speed", sa.Float(), nullable=True),
        sa.Column("wind_gust", sa.Float(), nullable=True),
        sa.Column("air_pressure", sa.Float(), nullable=True),
        sa.Column("sun_duration", sa.Float(), nullable=True),
        sa.Column("solar_radiation", sa.Float(), nullable=True),
        sa.Column("value_type", sa.String(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("source_provider", "source_station", "timestamp"),
        sa.UniqueConstraint(
            "source_provider",
            "source_station",
            "timestamp",
            name="uq_station_weather_hourly_station_timestamp",
        ),
    )


def downgrade() -> None:
    op.drop_table("station_weather_hourly")
    op.create_table(
        "field_weather_daily",
        sa.Column("date", sa.Date(), nullable=False),
        sa.Column("field_id", sa.Integer(), nullable=False),
        sa.Column("precipitation", sa.Float(), nullable=False),
        sa.Column("tmin", sa.Float(), nullable=True),
        sa.Column("tmax", sa.Float(), nullable=True),
        sa.Column("tmean", sa.Float(), nullable=True),
        sa.Column("source_provider", sa.String(), nullable=False),
        sa.Column("source_station", sa.String(), nullable=False),
        sa.Column("value_type", sa.String(), nullable=False),
        sa.ForeignKeyConstraint(["field_id"], ["fields.id"]),
        sa.PrimaryKeyConstraint("date", "field_id"),
        sa.UniqueConstraint("field_id", "date", name="uq_field_weather_daily_field_date"),
    )
