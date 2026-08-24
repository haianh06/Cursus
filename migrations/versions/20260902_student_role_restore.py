"""Add Self-Study Pomodoro + Student Memory tables (genuinely missing features,
not restoring anything haidang2425 already rebuilt independently).

Revision ID: 20260902_student_role_restore
Revises: 20260902_data_req_org_scoping
Create Date: 2026-09-02

See docs/planning/STUDENT_ROLE_RESTORE_SPEC.md -- after comparing the pre-merge
develop branch against current HEAD, most Student-role functionality
(Planner/Timetable/SemesterSetup/Reflection/Practice) already exists here,
independently rebuilt. Only three things were verified genuinely missing:
Self-Study Pomodoro sessions, Student cross-session chat Memory, and recurring
self-study timetable blocks. This migration adds exactly those, nothing else.

Everything here reaches organization scoping transitively through student_id
-> User.organization_id (same pattern as WeeklyPlan/StudyTask) -- no direct
organization_id column needed.

Guarded the same way other migrations in this chain guard themselves: on a
*fresh* database, 20260808_baseline_schema.py's create_all() already builds
`schedule_blocks` straight from the *current* (post-restore) src/db/models.py,
so `recurrence_series_id` already exists by the time this migration runs --
only a pre-existing (already-upgraded) database needs it added here. The two
new tables are not part of baseline's create_all list, so those are
unconditional (still existence-guarded for safe re-runs).
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

from src.db.models import Base

# down_revision repointed onto 20260904_guardrail_policy_ver (a sibling
# migration merged in from origin/develop after this one was authored) to
# keep a single linear chain instead of two heads -- this migration doesn't
# touch anything guardrail-related, so ordering relative to it is arbitrary.
revision: str = "20260902_student_role_restore"
down_revision: str | Sequence[str] | None = "20260904_guardrail_policy_ver"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_NEW_TABLES = ["self_study_sessions", "student_memory_consent", "student_memory_entries"]


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    existing_tables = set(inspector.get_table_names())

    new_tables = [name for name in _NEW_TABLES if name not in existing_tables]
    if new_tables:
        Base.metadata.create_all(bind=bind, tables=[Base.metadata.tables[name] for name in new_tables])

    block_cols = {c["name"] for c in inspector.get_columns("schedule_blocks")} if "schedule_blocks" in existing_tables else set()
    if "recurrence_series_id" not in block_cols:
        with op.batch_alter_table("schedule_blocks") as batch_op:
            batch_op.add_column(sa.Column("recurrence_series_id", sa.String(), nullable=True))
        op.create_index(
            "ix_schedule_blocks_recurrence_series_id", "schedule_blocks", ["recurrence_series_id"]
        )


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    existing_tables = set(inspector.get_table_names())

    if "schedule_blocks" in existing_tables:
        cols = {c["name"] for c in inspector.get_columns("schedule_blocks")}
        if "recurrence_series_id" in cols:
            op.drop_index("ix_schedule_blocks_recurrence_series_id", table_name="schedule_blocks")
            with op.batch_alter_table("schedule_blocks") as batch_op:
                batch_op.drop_column("recurrence_series_id")

    for name in reversed(_NEW_TABLES):
        if name in existing_tables:
            Base.metadata.drop_all(bind=bind, tables=[Base.metadata.tables[name]])
