"""Remove crop protection rule target.

Revision ID: 0005_remove_crop_protection_target
Revises: 0004_crop_protection_rules
Create Date: 2026-06-05 00:00:00
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "0005_remove_crop_protection_target"
down_revision = "0004_crop_protection_rules"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("crop_protection_rules") as batch_op:
        batch_op.drop_column("target")


def downgrade() -> None:
    with op.batch_alter_table("crop_protection_rules") as batch_op:
        batch_op.add_column(sa.Column("target", sa.String(), nullable=True))
