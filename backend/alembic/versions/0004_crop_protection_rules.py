"""Add crop protection rules.

Revision ID: 0004_crop_protection_rules
Revises: 0003_field_weather_and_treatments
Create Date: 2026-06-05 00:00:00
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "0004_crop_protection_rules"
down_revision = "0003_field_weather_and_treatments"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "crop_protection_rules",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("target", sa.String(), nullable=False),
        sa.Column("enabled", sa.Boolean(), nullable=False),
        sa.Column("season_start", sa.Date(), nullable=True),
        sa.Column("season_end", sa.Date(), nullable=True),
        sa.Column("logic", sa.String(), nullable=False),
        sa.Column("notes", sa.String(), nullable=True),
        sa.CheckConstraint("logic IN ('any', 'all')", name="ck_crop_protection_rules_logic"),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_table(
        "crop_protection_rule_products",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("rule_id", sa.Integer(), nullable=False),
        sa.Column("product_name", sa.String(), nullable=False),
        sa.ForeignKeyConstraint(["rule_id"], ["crop_protection_rules.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("rule_id", "product_name", name="uq_crop_protection_rule_products_rule_product"),
    )

    op.create_table(
        "crop_protection_rule_scopes",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("rule_id", sa.Integer(), nullable=False),
        sa.Column("field_id", sa.Integer(), nullable=True),
        sa.Column("planting_id", sa.Integer(), nullable=True),
        sa.Column("section_id", sa.Integer(), nullable=True),
        sa.CheckConstraint(
            "(field_id IS NOT NULL) + (planting_id IS NOT NULL) + (section_id IS NOT NULL) = 1",
            name="ck_crop_protection_rule_scopes_one_scope",
        ),
        sa.ForeignKeyConstraint(["field_id"], ["fields.id"]),
        sa.ForeignKeyConstraint(["planting_id"], ["plantings.id"]),
        sa.ForeignKeyConstraint(["rule_id"], ["crop_protection_rules.id"]),
        sa.ForeignKeyConstraint(["section_id"], ["sections.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "rule_id",
            "field_id",
            "planting_id",
            "section_id",
            name="uq_crop_protection_rule_scopes_rule_scope",
        ),
    )

    op.create_table(
        "crop_protection_rule_metrics",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("rule_id", sa.Integer(), nullable=False),
        sa.Column("metric_type", sa.String(), nullable=False),
        sa.Column("enabled", sa.Boolean(), nullable=False),
        sa.Column("threshold", sa.Float(), nullable=False),
        sa.Column("warning_threshold", sa.Float(), nullable=True),
        sa.Column("metric_config", sa.JSON(), nullable=True),
        sa.CheckConstraint(
            "metric_type IN ('days_since', 'rain_since', 'gdd_since')",
            name="ck_crop_protection_rule_metrics_type",
        ),
        sa.ForeignKeyConstraint(["rule_id"], ["crop_protection_rules.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("rule_id", "metric_type", name="uq_crop_protection_rule_metrics_rule_type"),
    )


def downgrade() -> None:
    op.drop_table("crop_protection_rule_metrics")
    op.drop_table("crop_protection_rule_scopes")
    op.drop_table("crop_protection_rule_products")
    op.drop_table("crop_protection_rules")
