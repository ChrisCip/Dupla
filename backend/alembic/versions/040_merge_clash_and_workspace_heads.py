"""merge clash workflow and workspace migration heads

Revision ID: 040_merge_heads
Revises: 035_clash_job_export_revisions, 039_file_counts_for_budget
"""
from __future__ import annotations

revision = "040_merge_heads"
down_revision = ("035_clash_job_export_revisions", "039_file_counts_for_budget")
branch_labels = None
depends_on = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
