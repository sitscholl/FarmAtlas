"""Add fruit count surveys and yearly stats.

Revision ID: 0010_fruit_counts_and_yearly_stats
Revises: 0009_drop_water_balance_cache
Create Date: 2026-06-20 00:00:00
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "0010_fruit_counts_and_yearly_stats"
down_revision = "0009_drop_water_balance_cache"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "fruit_count_surveys",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("season_year", sa.Integer(), nullable=False),
        sa.Column("date", sa.Date(), nullable=False),
        sa.Column("timing_code", sa.String(), nullable=False),
        sa.Column("field_id", sa.Integer(), nullable=True),
        sa.Column("planting_id", sa.Integer(), nullable=True),
        sa.Column("section_id", sa.Integer(), nullable=True),
        sa.Column("method", sa.String(), nullable=True),
        sa.Column("observer", sa.String(), nullable=True),
        sa.Column("notes", sa.String(), nullable=True),
        sa.Column("include_in_aggregation", sa.Boolean(), nullable=False),
        sa.Column("quality_flag", sa.String(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "(field_id IS NOT NULL) + (planting_id IS NOT NULL) + (section_id IS NOT NULL) = 1",
            name="ck_fruit_count_surveys_one_scope",
        ),
        sa.CheckConstraint("season_year >= 1900", name="ck_fruit_count_surveys_season_year"),
        sa.ForeignKeyConstraint(["field_id"], ["fields.id"]),
        sa.ForeignKeyConstraint(["planting_id"], ["plantings.id"]),
        sa.ForeignKeyConstraint(["section_id"], ["sections.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_fruit_count_surveys_field_year_timing",
        "fruit_count_surveys",
        ["field_id", "season_year", "timing_code"],
    )
    op.create_index(
        "ix_fruit_count_surveys_planting_year_timing",
        "fruit_count_surveys",
        ["planting_id", "season_year", "timing_code"],
    )
    op.create_index(
        "ix_fruit_count_surveys_section_year_timing",
        "fruit_count_surveys",
        ["section_id", "season_year", "timing_code"],
    )

    op.create_table(
        "fruit_count_samples",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("survey_id", sa.Integer(), nullable=False),
        sa.Column("tree_label", sa.String(), nullable=True),
        sa.Column("apple_count", sa.Integer(), nullable=False),
        sa.Column("notes", sa.String(), nullable=True),
        sa.CheckConstraint("apple_count >= 0", name="ck_fruit_count_samples_apple_count_non_negative"),
        sa.ForeignKeyConstraint(["survey_id"], ["fruit_count_surveys.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_fruit_count_samples_survey_id", "fruit_count_samples", ["survey_id"])

    op.create_table(
        "yearly_stats",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("season_year", sa.Integer(), nullable=False),
        sa.Column("field_id", sa.Integer(), nullable=True),
        sa.Column("planting_id", sa.Integer(), nullable=True),
        sa.Column("section_id", sa.Integer(), nullable=True),
        sa.Column("thinning_hours", sa.Float(), nullable=True),
        sa.Column("harvest_hours", sa.Float(), nullable=True),
        sa.Column("filled_boxes", sa.Float(), nullable=True),
        sa.Column("yield_kg", sa.Float(), nullable=True),
        sa.Column("revenue", sa.Float(), nullable=True),
        sa.Column("notes", sa.String(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "(field_id IS NOT NULL) + (planting_id IS NOT NULL) + (section_id IS NOT NULL) = 1",
            name="ck_yearly_stats_one_scope",
        ),
        sa.CheckConstraint("season_year >= 1900", name="ck_yearly_stats_season_year"),
        sa.CheckConstraint("thinning_hours IS NULL OR thinning_hours >= 0", name="ck_yearly_stats_thinning_hours"),
        sa.CheckConstraint("harvest_hours IS NULL OR harvest_hours >= 0", name="ck_yearly_stats_harvest_hours"),
        sa.CheckConstraint("filled_boxes IS NULL OR filled_boxes >= 0", name="ck_yearly_stats_filled_boxes"),
        sa.CheckConstraint("yield_kg IS NULL OR yield_kg >= 0", name="ck_yearly_stats_yield_kg"),
        sa.ForeignKeyConstraint(["field_id"], ["fields.id"]),
        sa.ForeignKeyConstraint(["planting_id"], ["plantings.id"]),
        sa.ForeignKeyConstraint(["section_id"], ["sections.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "uq_yearly_stats_field_year",
        "yearly_stats",
        ["field_id", "season_year"],
        unique=True,
        sqlite_where=sa.text("field_id IS NOT NULL"),
    )
    op.create_index(
        "uq_yearly_stats_planting_year",
        "yearly_stats",
        ["planting_id", "season_year"],
        unique=True,
        sqlite_where=sa.text("planting_id IS NOT NULL"),
    )
    op.create_index(
        "uq_yearly_stats_section_year",
        "yearly_stats",
        ["section_id", "season_year"],
        unique=True,
        sqlite_where=sa.text("section_id IS NOT NULL"),
    )


def downgrade() -> None:
    op.drop_index("uq_yearly_stats_section_year", table_name="yearly_stats")
    op.drop_index("uq_yearly_stats_planting_year", table_name="yearly_stats")
    op.drop_index("uq_yearly_stats_field_year", table_name="yearly_stats")
    op.drop_table("yearly_stats")
    op.drop_index("ix_fruit_count_samples_survey_id", table_name="fruit_count_samples")
    op.drop_table("fruit_count_samples")
    op.drop_index("ix_fruit_count_surveys_section_year_timing", table_name="fruit_count_surveys")
    op.drop_index("ix_fruit_count_surveys_planting_year_timing", table_name="fruit_count_surveys")
    op.drop_index("ix_fruit_count_surveys_field_year_timing", table_name="fruit_count_surveys")
    op.drop_table("fruit_count_surveys")
