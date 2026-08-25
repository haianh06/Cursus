"""Self-study Pomodoro sessions.

Revision ID: 20260821_self_study_sessions
Revises: 20260820_practice_sets
Create Date: 2026-08-21
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260821_self_study_sessions"
down_revision: str | Sequence[str] | None = "20260820_practice_sets"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _tables() -> set[str]:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    return set(inspector.get_table_names())


def upgrade() -> None:
    if "self_study_sessions" in _tables():
        return
    op.create_table(
        "self_study_sessions",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column(
            "student_id",
            sa.String(),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "schedule_block_id",
            sa.String(),
            sa.ForeignKey("schedule_blocks.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("title", sa.String(), nullable=False),
        sa.Column("planned_minutes", sa.Integer(), nullable=False),
        sa.Column("started_at", sa.DateTime(), nullable=False),
        sa.Column("scheduled_end_at", sa.DateTime(), nullable=False),
        sa.Column("ended_at", sa.DateTime(), nullable=True),
        sa.Column("actual_minutes", sa.Integer(), nullable=True),
        sa.Column("pomodoros_completed", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("status", sa.String(), nullable=False),
        sa.UniqueConstraint("schedule_block_id", name="uq_self_study_session_block"),
    )
    op.create_index("ix_self_study_sessions_student_id", "self_study_sessions", ["student_id"])


def downgrade() -> None:
    if "self_study_sessions" not in _tables():
        return
    op.drop_index("ix_self_study_sessions_student_id", table_name="self_study_sessions")
    op.drop_table("self_study_sessions")
