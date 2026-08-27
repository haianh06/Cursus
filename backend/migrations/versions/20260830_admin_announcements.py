"""Add admin_announcements table.

Revision ID: 20260830_admin_announcements
Revises: 20260829_workflow_privacy_extras
Create Date: 2026-08-30

Thong bao rong tu Admin toi tat ca giang vien, hien o dashboard GV (nhu mot
phan cua khoi "thong bao can thiet" khi tai cau truc dashboard).
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260830_admin_announcements"
down_revision: str | Sequence[str] | None = "20260829_workflow_privacy_extras"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _tables() -> set[str]:
    return set(sa.inspect(op.get_bind()).get_table_names())


def upgrade() -> None:
    if "admin_announcements" in _tables():
        return
    op.create_table(
        "admin_announcements",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("title", sa.String(), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("created_by", sa.String(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
    )


def downgrade() -> None:
    if "admin_announcements" in _tables():
        op.drop_table("admin_announcements")
