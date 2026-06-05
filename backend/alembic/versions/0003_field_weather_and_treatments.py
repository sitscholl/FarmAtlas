"""Add field weather cache and treatment imports.

Revision ID: 0003_field_weather_and_treatments
Revises: 0002_section_phenology_events
Create Date: 2026-06-05 00:00:00
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "0003_field_weather_and_treatments"
down_revision = "0002_section_phenology_events"
branch_labels = None
depends_on = None


def upgrade() -> None:
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

    op.create_table(
        "treatment_imports",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("source", sa.String(), nullable=False),
        sa.Column("season_year", sa.Integer(), nullable=False),
        sa.Column("imported_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("row_count", sa.Integer(), nullable=False),
        sa.Column("unresolved_count", sa.Integer(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("source", "season_year", name="uq_treatment_imports_source_season"),
    )

    op.create_table(
        "treatment_section_aliases",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("source", sa.String(), nullable=False),
        sa.Column("external_section_name", sa.String(), nullable=False),
        sa.Column("section_id", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(["section_id"], ["sections.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("source", "external_section_name", name="uq_treatment_section_aliases_source_name"),
    )

    op.create_table(
        "treatment_events",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("source", sa.String(), nullable=False),
        sa.Column("season_year", sa.Integer(), nullable=False),
        sa.Column("date", sa.Date(), nullable=False),
        sa.Column("external_section_name", sa.String(), nullable=False),
        sa.Column("section_id", sa.Integer(), nullable=True),
        sa.Column("product_name", sa.String(), nullable=False),
        sa.Column("reason", sa.String(), nullable=True),
        sa.Column("dose_per_hl", sa.Float(), nullable=True),
        sa.Column("hl", sa.Float(), nullable=True),
        sa.Column("cost", sa.Float(), nullable=True),
        sa.Column("row_hash", sa.String(), nullable=False),
        sa.Column("resolution_status", sa.String(), nullable=False),
        sa.ForeignKeyConstraint(["section_id"], ["sections.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("source", "season_year", "row_hash", name="uq_treatment_events_source_season_hash"),
    )
    op.create_index("ix_treatment_events_product", "treatment_events", ["product_name"])
    op.create_index("ix_treatment_events_section_date", "treatment_events", ["section_id", "date"])


def downgrade() -> None:
    op.drop_index("ix_treatment_events_section_date", table_name="treatment_events")
    op.drop_index("ix_treatment_events_product", table_name="treatment_events")
    op.drop_table("treatment_events")
    op.drop_table("treatment_section_aliases")
    op.drop_table("treatment_imports")
    op.drop_table("field_weather_daily")
