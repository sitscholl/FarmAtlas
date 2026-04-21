"""Initial schema.

Revision ID: 0001_initial_schema
Revises:
Create Date: 2026-04-21 00:00:00
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "0001_initial_schema"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "fields",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("group", sa.String(), nullable=False),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("reference_provider", sa.String(), nullable=False),
        sa.Column("reference_station", sa.String(), nullable=False),
        sa.Column("elevation", sa.Float(), nullable=False),
        sa.Column("soil_type", sa.String(), nullable=True),
        sa.Column("soil_weight", sa.String(), nullable=True),
        sa.Column("humus_pct", sa.Float(), nullable=True),
        sa.Column("effective_root_depth_cm", sa.Float(), nullable=True),
        sa.Column("p_allowable", sa.Float(), nullable=True),
        sa.Column("drip_distance", sa.Float(), nullable=True),
        sa.Column("drip_discharge", sa.Float(), nullable=True),
        sa.Column("tree_strip_width", sa.Float(), nullable=True),
        sa.Column("valve_open", sa.Boolean(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("group", "name", name="uq_fields_group_name"),
    )

    op.create_table(
        "varieties",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("group", sa.String(), nullable=False),
        sa.Column("nr_per_kg", sa.Float(), nullable=True),
        sa.Column("kg_per_box", sa.Float(), nullable=True),
        sa.Column("slope", sa.Float(), nullable=True),
        sa.Column("intercept", sa.Float(), nullable=True),
        sa.Column("specific_weight", sa.Float(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("name"),
    )

    op.create_table(
        "field_cadastral_parcels",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("field_id", sa.Integer(), nullable=False),
        sa.Column("parcel_id", sa.String(), nullable=False),
        sa.Column("municipality_id", sa.String(), nullable=False),
        sa.Column("area", sa.Float(), nullable=False),
        sa.CheckConstraint("area >= 0", name="ck_field_cadastral_parcels_area_non_negative"),
        sa.ForeignKeyConstraint(["field_id"], ["fields.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "field_id",
            "municipality_id",
            "parcel_id",
            name="uq_field_cadastral_parcels_identity",
        ),
    )

    op.create_table(
        "irrigation_events",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("field_id", sa.Integer(), nullable=False),
        sa.Column("date", sa.Date(), nullable=False),
        sa.Column("method", sa.String(), nullable=False),
        sa.Column("duration", sa.Float(), nullable=False),
        sa.Column("amount", sa.Float(), nullable=False),
        sa.ForeignKeyConstraint(["field_id"], ["fields.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("field_id", "date", name="uq_irrigation_field_date"),
    )

    op.create_table(
        "plantings",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("field_id", sa.Integer(), nullable=False),
        sa.Column("variety_id", sa.Integer(), nullable=False),
        sa.Column("valid_from", sa.Date(), nullable=False),
        sa.Column("valid_to", sa.Date(), nullable=True),
        sa.CheckConstraint("valid_to IS NULL OR valid_to >= valid_from", name="ck_plantings_valid_range"),
        sa.ForeignKeyConstraint(["field_id"], ["fields.id"]),
        sa.ForeignKeyConstraint(["variety_id"], ["varieties.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "uq_plantings_field_variety_valid_from",
        "plantings",
        ["field_id", "variety_id", "valid_from"],
        unique=True,
    )

    op.create_table(
        "nutrients",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("variety_id", sa.Integer(), nullable=True),
        sa.Column("nutrient_code", sa.String(), nullable=False),
        sa.Column("requirement_per_kg_min", sa.Float(), nullable=False),
        sa.Column("requirement_per_kg_mean", sa.Float(), nullable=False),
        sa.Column("requirement_per_kg_max", sa.Float(), nullable=False),
        sa.ForeignKeyConstraint(["variety_id"], ["varieties.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "uq_nutrients_global_default",
        "nutrients",
        ["nutrient_code"],
        unique=True,
        sqlite_where=sa.text("variety_id IS NULL"),
    )
    op.create_index(
        "uq_nutrients_variety_override",
        "nutrients",
        ["nutrient_code", "variety_id"],
        unique=True,
        sqlite_where=sa.text("variety_id IS NOT NULL"),
    )

    op.create_table(
        "sections",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("planting_id", sa.Integer(), nullable=False),
        sa.Column("planting_year", sa.Integer(), nullable=False),
        sa.Column("area", sa.Float(), nullable=False),
        sa.Column("tree_count", sa.Integer(), nullable=True),
        sa.Column("tree_height", sa.Float(), nullable=True),
        sa.Column("row_distance", sa.Float(), nullable=True),
        sa.Column("tree_distance", sa.Float(), nullable=True),
        sa.Column("running_metre", sa.Float(), nullable=True),
        sa.Column("herbicide_free", sa.Boolean(), nullable=True),
        sa.Column("valid_from", sa.Date(), nullable=False),
        sa.Column("valid_to", sa.Date(), nullable=True),
        sa.CheckConstraint("valid_to IS NULL OR valid_to >= valid_from", name="ck_sections_valid_range"),
        sa.ForeignKeyConstraint(["planting_id"], ["plantings.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "uq_sections_planting_valid_from",
        "sections",
        ["planting_id", "name"],
        unique=True,
    )

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


def downgrade() -> None:
    op.drop_table("water_balance")
    op.drop_index("uq_sections_planting_valid_from", table_name="sections")
    op.drop_table("sections")
    op.drop_index("uq_nutrients_variety_override", table_name="nutrients")
    op.drop_index("uq_nutrients_global_default", table_name="nutrients")
    op.drop_table("nutrients")
    op.drop_index("uq_plantings_field_variety_valid_from", table_name="plantings")
    op.drop_table("plantings")
    op.drop_table("irrigation_events")
    op.drop_table("field_cadastral_parcels")
    op.drop_table("varieties")
    op.drop_table("fields")
