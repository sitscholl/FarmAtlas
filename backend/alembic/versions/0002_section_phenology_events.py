"""Add section phenology events.

Revision ID: 0002_section_phenology_events
Revises: 0001_initial_schema
Create Date: 2026-04-24 00:00:00
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "0002_section_phenology_events"
down_revision = "0001_initial_schema"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "section_phenology_events",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("section_id", sa.Integer(), nullable=False),
        sa.Column("stage_code", sa.String(), nullable=False),
        sa.Column("date", sa.Date(), nullable=False),
        sa.Column("year", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(["section_id"], ["sections.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("section_id", "date", name="uq_section_phenology_events_section_date"),
        sa.UniqueConstraint(
            "section_id",
            "stage_code",
            "year",
            name="uq_section_phenology_events_section_stage_year",
        ),
    )


def downgrade() -> None:
    op.drop_table("section_phenology_events")
