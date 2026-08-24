"""Mock LMS sync version history (mục 6.6).

Revision ID: 20260824_mock_lms_sync_versions
Revises: 20260823_risk_policy_admin
Create Date: 2026-08-24

Same immutable-append pattern as `risk_policies` (20260823 migration): no
`is_active` flag, "current" = MAX(sync_version), every publish/rollback inserts
a new row. No seed row here (unlike risk_policies) -- there is no pre-existing
hardcoded sync state to preserve; before the first real publish, "no sync has
happened yet" is simply an empty table, handled in the service layer.
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260824_mock_lms_sync_versions"
down_revision: str | Sequence[str] | None = "20260823_risk_policy_admin"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "mock_lms_sync_versions",
        sa.Column("sync_version", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("payload", sa.JSON(), nullable=False),
        sa.Column("reason", sa.Text(), nullable=False),
        sa.Column("rolled_back_from", sa.Integer(), nullable=True),
        sa.Column(
            "created_by", sa.String(), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True
        ),
        sa.Column("created_at", sa.DateTime(), nullable=False),
    )


def downgrade() -> None:
    op.drop_table("mock_lms_sync_versions")
