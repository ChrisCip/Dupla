"""Add workflow incident contract columns to project_clash_items.

Revision ID: 041_clash_item_incident_contract
Revises: 040_merge_heads
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "041_clash_item_incident_contract"
down_revision = "040_merge_heads"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("project_clash_items", sa.Column("title_semantic", sa.Text(), nullable=True))
    op.add_column("project_clash_items", sa.Column("short_label", sa.String(96), nullable=True))
    op.add_column("project_clash_items", sa.Column("table_comment", sa.Text(), nullable=True))
    op.add_column("project_clash_items", sa.Column("base_plan_number", sa.String(64), nullable=True))
    op.add_column("project_clash_items", sa.Column("compared_plan_number", sa.String(64), nullable=True))
    op.add_column("project_clash_items", sa.Column("base_full_plan_tile_path", sa.Text(), nullable=True))
    op.add_column("project_clash_items", sa.Column("zoom_tile_path", sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column("project_clash_items", "zoom_tile_path")
    op.drop_column("project_clash_items", "base_full_plan_tile_path")
    op.drop_column("project_clash_items", "compared_plan_number")
    op.drop_column("project_clash_items", "base_plan_number")
    op.drop_column("project_clash_items", "table_comment")
    op.drop_column("project_clash_items", "short_label")
    op.drop_column("project_clash_items", "title_semantic")
