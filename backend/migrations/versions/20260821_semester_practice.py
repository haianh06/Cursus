"""Semester setup, academic terms, practice sets, and per-course chat threads.

Revision ID: 20260821_semester_practice
Revises: 20260816_guardrail_reviews
Create Date: 2026-08-13

Reimplementation (not a straight port) of origin/develop's four migrations
(20260817_conv_subject, 20260818_semester_setup, 20260819_academic_term,
20260820_practice_sets) — those can't be applied as-is because develop's
chain forks from this branch's history at 20260813_guardrail_rules (same
revision id, different down_revision) and develop has no organization/tenant
concept at all. See docs/discovery/05_DEVELOP_FEATURE_SPEC.md section on
Semester/Practice/Companion for the full rationale.

Tenant scoping follows 20260812_organizations_and_tenancy.py's own rule:
only "root" tables with no existing path to an org-scoped table get a direct
`organization_id` column. Every table below reaches org scoping transitively
through an existing FK — `semester_setups.student_id -> users.organization_id`,
`course_exams.course_id` / `practice_sets.course_id` / `class_activities.course_id`
-> `courses.organization_id` — EXCEPT `academic_terms`, which (like develop's
version) has no course/student FK at all, so it gets `organization_id`
directly, matching the `courses`/`programs`/`curriculum_versions` precedent.
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260821_semester_practice"
down_revision: str | Sequence[str] | None = "20260816_guardrail_reviews"
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

    # ── conversations: per-course chat threads ──────────────────────────
    conv_cols = _cols("conversations")
    if "conversations" in tables and "subject_code" not in conv_cols:
        op.add_column("conversations", sa.Column("subject_code", sa.String(), nullable=True))
        op.create_index("ix_conversations_subject_code", "conversations", ["subject_code"])
    if "conversations" in tables and "updated_at" not in conv_cols:
        op.add_column("conversations", sa.Column("updated_at", sa.DateTime(), nullable=True))
        op.execute(sa.text("UPDATE conversations SET updated_at = created_at WHERE updated_at IS NULL"))

    # ── semester setup (student-scoped, org reached via student_id) ─────
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
            sa.Column("semester_id", sa.String(), sa.ForeignKey("semester_setups.id", ondelete="CASCADE"), nullable=False),
            sa.Column("course_id", sa.String(), sa.ForeignKey("courses.id", ondelete="CASCADE"), nullable=False),
            sa.UniqueConstraint("semester_id", "course_id", name="uq_semester_course"),
        )
        op.create_index("ix_semester_courses_semester_id", "semester_courses", ["semester_id"])

    if "semester_week_slots" not in tables:
        op.create_table(
            "semester_week_slots",
            sa.Column("id", sa.String(), primary_key=True),
            sa.Column("semester_id", sa.String(), sa.ForeignKey("semester_setups.id", ondelete="CASCADE"), nullable=False),
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
            sa.Column("semester_id", sa.String(), sa.ForeignKey("semester_setups.id", ondelete="CASCADE"), nullable=False),
            sa.Column("kind", sa.String(), nullable=False),
            sa.Column("start_date", sa.Date(), nullable=False),
            sa.Column("end_date", sa.Date(), nullable=False),
            sa.Column("label", sa.String(), nullable=False, server_default=""),
        )
        op.create_index("ix_semester_exceptions_semester_id", "semester_exceptions", ["semester_id"])

    event_cols = _cols("calendar_events")
    if "calendar_events" in tables and "semester_setup_id" not in event_cols:
        # batch mode: SQLite (used by the migration test suite) can't ALTER
        # in a FK constraint directly — needs the copy-and-move strategy.
        with op.batch_alter_table("calendar_events") as batch_op:
            batch_op.add_column(
                sa.Column(
                    "semester_setup_id",
                    sa.String(),
                    sa.ForeignKey(
                        "semester_setups.id",
                        ondelete="CASCADE",
                        name="fk_calendar_events_semester_setup_id",
                    ),
                    nullable=True,
                ),
            )
        op.create_index("ix_calendar_events_semester_setup_id", "calendar_events", ["semester_setup_id"])

    # ── academic terms: root table, no course/student FK -> needs org_id ─
    if "academic_terms" not in tables:
        op.create_table(
            "academic_terms",
            sa.Column("id", sa.String(), primary_key=True),
            sa.Column("organization_id", sa.String(), sa.ForeignKey("organizations.id"), nullable=False),
            sa.Column("name", sa.String(), nullable=False),
            sa.Column("start_date", sa.Date(), nullable=False),
            sa.Column("study_weeks", sa.Integer(), nullable=False, server_default="10"),
            sa.Column("exam_weeks", sa.Integer(), nullable=False, server_default="2"),
            sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
            sa.Column("created_at", sa.DateTime(), nullable=False),
        )
        op.create_index("ix_academic_terms_organization_id", "academic_terms", ["organization_id"])
        op.create_index("ix_academic_terms_is_active", "academic_terms", ["is_active"])

    if "course_exams" not in tables:
        op.create_table(
            "course_exams",
            sa.Column("id", sa.String(), primary_key=True),
            sa.Column("term_id", sa.String(), sa.ForeignKey("academic_terms.id", ondelete="CASCADE"), nullable=False),
            sa.Column("course_id", sa.String(), sa.ForeignKey("courses.id", ondelete="CASCADE"), nullable=False),
            sa.Column("kind", sa.String(), nullable=False),
            sa.UniqueConstraint("term_id", "course_id", "kind", name="uq_course_exam_kind"),
        )
        op.create_index("ix_course_exams_term_id", "course_exams", ["term_id"])
        op.create_index("ix_course_exams_course_id", "course_exams", ["course_id"])

    if "course_exam_sessions" not in tables:
        op.create_table(
            "course_exam_sessions",
            sa.Column("id", sa.String(), primary_key=True),
            sa.Column("exam_id", sa.String(), sa.ForeignKey("course_exams.id", ondelete="CASCADE"), nullable=False),
            sa.Column("exam_date", sa.Date(), nullable=False),
            sa.Column("slot_id", sa.Integer(), nullable=False),
            sa.Column("label", sa.String(), nullable=False, server_default="Ca 1"),
        )
        op.create_index("ix_course_exam_sessions_exam_id", "course_exam_sessions", ["exam_id"])
        op.create_index("ix_course_exam_sessions_exam_date", "course_exam_sessions", ["exam_date"])

    if "course_exam_session_students" not in tables:
        op.create_table(
            "course_exam_session_students",
            sa.Column("id", sa.String(), primary_key=True),
            sa.Column("session_id", sa.String(), sa.ForeignKey("course_exam_sessions.id", ondelete="CASCADE"), nullable=False),
            sa.Column("student_id", sa.String(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
            sa.UniqueConstraint("session_id", "student_id", name="uq_exam_session_student"),
        )
        op.create_index("ix_course_exam_session_students_session_id", "course_exam_session_students", ["session_id"])
        op.create_index("ix_course_exam_session_students_student_id", "course_exam_session_students", ["student_id"])

    if "class_activities" not in tables:
        op.create_table(
            "class_activities",
            sa.Column("id", sa.String(), primary_key=True),
            sa.Column("course_id", sa.String(), sa.ForeignKey("courses.id", ondelete="CASCADE"), nullable=False),
            sa.Column("activity_date", sa.Date(), nullable=False),
            sa.Column("kind", sa.String(), nullable=False),
            sa.Column("title", sa.String(), nullable=False, server_default=""),
            sa.Column("created_by", sa.String(), sa.ForeignKey("users.id"), nullable=False),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.UniqueConstraint("course_id", "activity_date", name="uq_class_activity_day"),
        )
        op.create_index("ix_class_activities_course_id", "class_activities", ["course_id"])
        op.create_index("ix_class_activities_activity_date", "class_activities", ["activity_date"])

    # ── practice sets: course-scoped ─────────────────────────────────────
    if "practice_sets" not in tables:
        op.create_table(
            "practice_sets",
            sa.Column("id", sa.String(), primary_key=True),
            sa.Column("course_id", sa.String(), sa.ForeignKey("courses.id", ondelete="CASCADE"), nullable=False),
            sa.Column("course_code", sa.String(), nullable=False),
            sa.Column("slide_key", sa.String(), nullable=False),
            sa.Column("week_number", sa.Integer(), nullable=False),
            sa.Column("status", sa.String(), nullable=False),
            sa.Column("language", sa.String(), nullable=False, server_default="vi"),
            sa.Column("requested_by", sa.String(), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
            sa.Column("reviewed_by", sa.String(), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
            sa.Column("reviewed_at", sa.DateTime(), nullable=True),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.Column("updated_at", sa.DateTime(), nullable=False),
            sa.UniqueConstraint("course_code", "slide_key", name="uq_practice_set_slide"),
        )
        op.create_index("ix_practice_sets_course_id", "practice_sets", ["course_id"])
        op.create_index("ix_practice_sets_course_code", "practice_sets", ["course_code"])
        op.create_index("ix_practice_sets_slide_key", "practice_sets", ["slide_key"])
        op.create_index("ix_practice_sets_status", "practice_sets", ["status"])

    if "practice_items" not in tables:
        op.create_table(
            "practice_items",
            sa.Column("id", sa.String(), primary_key=True),
            sa.Column("set_id", sa.String(), sa.ForeignKey("practice_sets.id", ondelete="CASCADE"), nullable=False),
            sa.Column("kind", sa.String(), nullable=False),
            sa.Column("sort_order", sa.Integer(), nullable=False),
            sa.Column("prompt", sa.Text(), nullable=False),
            sa.Column("options", sa.JSON(), nullable=True),
            sa.Column("correct_key", sa.String(), nullable=True),
            sa.Column("answer", sa.Text(), nullable=False, server_default=""),
            sa.Column("explanation", sa.Text(), nullable=False, server_default=""),
            sa.Column("source_label", sa.String(), nullable=False, server_default=""),
        )
        op.create_index("ix_practice_items_set_id", "practice_items", ["set_id"])

    if bind_is_postgres():
        op.execute("ALTER TABLE academic_terms ENABLE ROW LEVEL SECURITY")
        op.execute(
            "CREATE POLICY org_isolation_academic_terms ON academic_terms "
            "USING (organization_id = current_setting('app.current_org_id', true))"
        )


def bind_is_postgres() -> bool:
    return op.get_bind().dialect.name == "postgresql"


def downgrade() -> None:
    tables = _tables()

    if bind_is_postgres() and "academic_terms" in tables:
        op.execute("DROP POLICY IF EXISTS org_isolation_academic_terms ON academic_terms")
        op.execute("ALTER TABLE academic_terms DISABLE ROW LEVEL SECURITY")

    for table in ("practice_items", "practice_sets", "class_activities",
                  "course_exam_session_students", "course_exam_sessions",
                  "course_exams", "academic_terms"):
        if table in tables:
            op.drop_table(table)

    event_cols = _cols("calendar_events")
    if "semester_setup_id" in event_cols:
        op.drop_index("ix_calendar_events_semester_setup_id", table_name="calendar_events")
        op.drop_column("calendar_events", "semester_setup_id")

    for table in ("semester_exceptions", "semester_week_slots", "semester_courses", "semester_setups"):
        if table in tables:
            op.drop_table(table)

    conv_cols = _cols("conversations")
    if "updated_at" in conv_cols:
        op.drop_column("conversations", "updated_at")
    if "subject_code" in conv_cols:
        op.drop_index("ix_conversations_subject_code", table_name="conversations")
        op.drop_column("conversations", "subject_code")
