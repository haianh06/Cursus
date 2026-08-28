"""Keep Pomodoro history when a student removes a calendar plan.

Revision ID: 20260913_timetable_plan_history
Revises: 20260912_ai_usage, 20260912_crisis_escalations
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260913_timetable_plan_history"
down_revision: str | Sequence[str] | None = (
    "20260912_ai_usage",
    "20260912_crisis_escalations",
)
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    inspector = sa.inspect(op.get_bind())
    columns = {column["name"] for column in inspector.get_columns("schedule_blocks")}
    if "cancelled_at" not in columns:
        op.add_column("schedule_blocks", sa.Column("cancelled_at", sa.DateTime(), nullable=True))
        op.create_index("ix_schedule_blocks_cancelled_at", "schedule_blocks", ["cancelled_at"])


def downgrade() -> None:
    inspector = sa.inspect(op.get_bind())
    columns = {column["name"] for column in inspector.get_columns("schedule_blocks")}
    if "cancelled_at" in columns:
        op.drop_index("ix_schedule_blocks_cancelled_at", table_name="schedule_blocks")
        op.drop_column("schedule_blocks", "cancelled_at")
