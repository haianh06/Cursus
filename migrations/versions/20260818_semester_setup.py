"""Student semester setup tables and calendar_events.semester_setup_id.

Revision ID: 20260818_semester_setup
Revises: 20260817_conv_subject
Create Date: 2026-08-18
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260818_semester_setup"
down_revision: str | Sequence[str] | None = "20260817_conv_subject"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _tables() -> set[str]:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    return set(inspector.get_table_names())


def _cols(table: str) -> set[str]:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if table not in inspector.get_table_names():
        return set()
    return {c["name"] for c in inspector.get_columns(table)}


def upgrade() -> None:
    tables = _tables()
    if "semester_setups" not in tables:
        op.create_table(
            "semester_setups",
            sa.Column("id", sa.String(), primary_key=True),
            sa.Column("student_id", sa.String(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
            sa.Column("name", sa.String(), nullable=False),
            sa.Column("start_date", sa.Date(), nullable=False),
            sa.Column("end_date", sa.Date(), nullable=False),
            sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
            sa.Column("created_at", sa.DateTime(), nullable=False),
        )
        op.create_index("ix_semester_setups_student_id", "semester_setups", ["student_id"])
        op.create_index("ix_semester_setups_is_active", "semester_setups", ["is_active"])

    if "semester_courses" not in tables:
        op.create_table(
            "semester_courses",
            sa.Column("id", sa.String(), primary_key=True),
            sa.Column(
                "semester_id",
                sa.String(),
                sa.ForeignKey("semester_setups.id", ondelete="CASCADE"),
                nullable=False,
            ),
            sa.Column("course_id", sa.String(), sa.ForeignKey("courses.id", ondelete="CASCADE"), nullable=False),
            sa.UniqueConstraint("semester_id", "course_id", name="uq_semester_course"),
        )
        op.create_index("ix_semester_courses_semester_id", "semester_courses", ["semester_id"])

    if "semester_week_slots" not in tables:
        op.create_table(
            "semester_week_slots",
            sa.Column("id", sa.String(), primary_key=True),
            sa.Column(
                "semester_id",
                sa.String(),
                sa.ForeignKey("semester_setups.id", ondelete="CASCADE"),
                nullable=False,
            ),
            sa.Column("weekday", sa.Integer(), nullable=False),
            sa.Column("slot_id", sa.Integer(), nullable=False),
            sa.Column("course_id", sa.String(), sa.ForeignKey("courses.id", ondelete="CASCADE"), nullable=False),
            sa.UniqueConstraint("semester_id", "weekday", "slot_id", name="uq_semester_week_slot"),
        )
        op.create_index("ix_semester_week_slots_semester_id", "semester_week_slots", ["semester_id"])

    if "semester_exceptions" not in tables:
        op.create_table(
            "semester_exceptions",
            sa.Column("id", sa.String(), primary_key=True),
            sa.Column(
                "semester_id",
                sa.String(),
                sa.ForeignKey("semester_setups.id", ondelete="CASCADE"),
                nullable=False,
            ),
            sa.Column("kind", sa.String(), nullable=False),
            sa.Column("start_date", sa.Date(), nullable=False),
            sa.Column("end_date", sa.Date(), nullable=False),
            sa.Column("label", sa.String(), nullable=False, server_default=""),
        )
        op.create_index("ix_semester_exceptions_semester_id", "semester_exceptions", ["semester_id"])

    event_cols = _cols("calendar_events")
    if "calendar_events" in tables and "semester_setup_id" not in event_cols:
        op.add_column(
            "calendar_events",
            sa.Column(
                "semester_setup_id",
                sa.String(),
                sa.ForeignKey("semester_setups.id", ondelete="CASCADE"),
                nullable=True,
            ),
        )
        op.create_index(
            "ix_calendar_events_semester_setup_id",
            "calendar_events",
            ["semester_setup_id"],
        )


def downgrade() -> None:
    event_cols = _cols("calendar_events")
    if "semester_setup_id" in event_cols:
        op.drop_index("ix_calendar_events_semester_setup_id", table_name="calendar_events")
        op.drop_column("calendar_events", "semester_setup_id")

    tables = _tables()
    if "semester_exceptions" in tables:
        op.drop_table("semester_exceptions")
    if "semester_week_slots" in tables:
        op.drop_table("semester_week_slots")
    if "semester_courses" in tables:
        op.drop_table("semester_courses")
    if "semester_setups" in tables:
        op.drop_table("semester_setups")
