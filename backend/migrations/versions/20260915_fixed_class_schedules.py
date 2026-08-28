"""Add institutional class schedules, exceptions and recipient notifications.

Revision ID: 20260915_fixed_class_schedules
Revises: 20260914_reflection_purge
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260915_fixed_class_schedules"
down_revision: str | Sequence[str] | None = "20260914_reflection_purge"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "term_study_slots",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("organization_id", sa.String(), sa.ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False),
        sa.Column("term_name", sa.String(), nullable=False),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("start_minute", sa.Integer(), nullable=False),
        sa.Column("end_minute", sa.Integer(), nullable=False),
        sa.Column("display_order", sa.Integer(), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
    )
    op.create_index("ix_term_study_slots_organization_id", "term_study_slots", ["organization_id"])
    op.create_index("ix_term_study_slots_term_name", "term_study_slots", ["term_name"])
    op.create_table(
        "fixed_class_schedules",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("section_id", sa.String(), sa.ForeignKey("course_sections.id", ondelete="CASCADE"), nullable=False),
        sa.Column("slot_id", sa.String(), sa.ForeignKey("term_study_slots.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("weekday", sa.Integer(), nullable=False),
        sa.Column("start_minute", sa.Integer(), nullable=False),
        sa.Column("end_minute", sa.Integer(), nullable=False),
        sa.Column("room", sa.String(), nullable=True), sa.Column("note", sa.Text(), nullable=True),
        sa.Column("effective_from", sa.Date(), nullable=False), sa.Column("effective_to", sa.Date(), nullable=False),
        sa.Column("created_by", sa.String(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
    )
    op.create_index("ix_fixed_class_schedules_section_id", "fixed_class_schedules", ["section_id"])
    op.create_table(
        "class_schedule_exceptions",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("schedule_id", sa.String(), sa.ForeignKey("fixed_class_schedules.id", ondelete="CASCADE"), nullable=True),
        sa.Column("section_id", sa.String(), sa.ForeignKey("course_sections.id", ondelete="CASCADE"), nullable=False),
        sa.Column("kind", sa.String(), nullable=False), sa.Column("event_date", sa.Date(), nullable=False),
        sa.Column("start_minute", sa.Integer(), nullable=False), sa.Column("end_minute", sa.Integer(), nullable=False),
        sa.Column("room", sa.String(), nullable=True), sa.Column("note", sa.Text(), nullable=True),
        sa.Column("reason", sa.Text(), nullable=False), sa.Column("created_by", sa.String(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
    )
    op.create_index("ix_class_schedule_exceptions_section_id", "class_schedule_exceptions", ["section_id"])
    op.create_index("ix_class_schedule_exceptions_schedule_id", "class_schedule_exceptions", ["schedule_id"])
    op.create_index("ix_class_schedule_exceptions_event_date", "class_schedule_exceptions", ["event_date"])
    op.create_table(
        "class_schedule_notifications",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("recipient_id", sa.String(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("exception_id", sa.String(), sa.ForeignKey("class_schedule_exceptions.id", ondelete="CASCADE"), nullable=False),
        sa.Column("title", sa.String(), nullable=False), sa.Column("body", sa.Text(), nullable=False),
        sa.Column("read_at", sa.DateTime(), nullable=True), sa.Column("created_at", sa.DateTime(), nullable=False),
    )
    op.create_index("ix_class_schedule_notifications_recipient_id", "class_schedule_notifications", ["recipient_id"])
    op.create_index("ix_class_schedule_notifications_exception_id", "class_schedule_notifications", ["exception_id"])


def downgrade() -> None:
    op.drop_table("class_schedule_notifications")
    op.drop_table("class_schedule_exceptions")
    op.drop_table("fixed_class_schedules")
    op.drop_table("term_study_slots")
