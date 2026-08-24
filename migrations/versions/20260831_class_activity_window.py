"""Add opens_at/closes_at window to class_activities.

Revision ID: 20260831_class_activity_window
Revises: 20260830_admin_announcements
Create Date: 2026-08-31

Cho phep giang vien set gio mo bai / dong bai khi gan Assignment, Progress
Test, Lab len tiet giang (thay vi chi co ngay).
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260831_class_activity_window"
down_revision: str | Sequence[str] | None = "20260830_admin_announcements"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _existing_columns(table: str) -> set[str]:
    return {col["name"] for col in sa.inspect(op.get_bind()).get_columns(table)}


def upgrade() -> None:
    columns = _existing_columns("class_activities")
    if "opens_at" not in columns:
        op.add_column("class_activities", sa.Column("opens_at", sa.DateTime(), nullable=True))
    if "closes_at" not in columns:
        op.add_column("class_activities", sa.Column("closes_at", sa.DateTime(), nullable=True))


def downgrade() -> None:
    columns = _existing_columns("class_activities")
    if "closes_at" in columns:
        op.drop_column("class_activities", "closes_at")
    if "opens_at" in columns:
        op.drop_column("class_activities", "opens_at")
