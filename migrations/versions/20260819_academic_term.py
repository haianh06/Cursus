"""Academic term, course exams, and instructor class activities.

Revision ID: 20260819_academic_term
Revises: 20260818_semester_setup
Create Date: 2026-08-19
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260819_academic_term"
down_revision: str | Sequence[str] | None = "20260818_semester_setup"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _tables() -> set[str]:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    return set(inspector.get_table_names())


def upgrade() -> None:
    tables = _tables()
    if "academic_terms" not in tables:
        op.create_table(
            "academic_terms",
            sa.Column("id", sa.String(), primary_key=True),
            sa.Column("name", sa.String(), nullable=False),
            sa.Column("start_date", sa.Date(), nullable=False),
            sa.Column("study_weeks", sa.Integer(), nullable=False, server_default="10"),
            sa.Column("exam_weeks", sa.Integer(), nullable=False, server_default="2"),
            sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
            sa.Column("created_at", sa.DateTime(), nullable=False),
        )
        op.create_index("ix_academic_terms_is_active", "academic_terms", ["is_active"])

    if "course_exams" not in tables:
        op.create_table(
            "course_exams",
            sa.Column("id", sa.String(), primary_key=True),
            sa.Column(
                "term_id",
                sa.String(),
                sa.ForeignKey("academic_terms.id", ondelete="CASCADE"),
                nullable=False,
            ),
            sa.Column(
                "course_id",
                sa.String(),
                sa.ForeignKey("courses.id", ondelete="CASCADE"),
                nullable=False,
            ),
            sa.Column("kind", sa.String(), nullable=False),
            sa.UniqueConstraint("term_id", "course_id", "kind", name="uq_course_exam_kind"),
        )
        op.create_index("ix_course_exams_term_id", "course_exams", ["term_id"])
        op.create_index("ix_course_exams_course_id", "course_exams", ["course_id"])

    if "course_exam_sessions" not in tables:
        op.create_table(
            "course_exam_sessions",
            sa.Column("id", sa.String(), primary_key=True),
            sa.Column(
                "exam_id",
                sa.String(),
                sa.ForeignKey("course_exams.id", ondelete="CASCADE"),
                nullable=False,
            ),
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
            sa.Column(
                "session_id",
                sa.String(),
                sa.ForeignKey("course_exam_sessions.id", ondelete="CASCADE"),
                nullable=False,
            ),
            sa.Column(
                "student_id",
                sa.String(),
                sa.ForeignKey("users.id", ondelete="CASCADE"),
                nullable=False,
            ),
            sa.UniqueConstraint("session_id", "student_id", name="uq_exam_session_student"),
        )
        op.create_index(
            "ix_course_exam_session_students_session_id",
            "course_exam_session_students",
            ["session_id"],
        )
        op.create_index(
            "ix_course_exam_session_students_student_id",
            "course_exam_session_students",
            ["student_id"],
        )

    if "class_activities" not in tables:
        op.create_table(
            "class_activities",
            sa.Column("id", sa.String(), primary_key=True),
            sa.Column(
                "course_id",
                sa.String(),
                sa.ForeignKey("courses.id", ondelete="CASCADE"),
                nullable=False,
            ),
            sa.Column("activity_date", sa.Date(), nullable=False),
            sa.Column("kind", sa.String(), nullable=False),
            sa.Column("title", sa.String(), nullable=False, server_default=""),
            sa.Column(
                "created_by",
                sa.String(),
                sa.ForeignKey("users.id"),
                nullable=False,
            ),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.UniqueConstraint("course_id", "activity_date", name="uq_class_activity_day"),
        )
        op.create_index("ix_class_activities_course_id", "class_activities", ["course_id"])
        op.create_index("ix_class_activities_activity_date", "class_activities", ["activity_date"])


def downgrade() -> None:
    tables = _tables()
    if "class_activities" in tables:
        op.drop_table("class_activities")
    if "course_exam_session_students" in tables:
        op.drop_table("course_exam_session_students")
    if "course_exam_sessions" in tables:
        op.drop_table("course_exam_sessions")
    if "course_exams" in tables:
        op.drop_table("course_exams")
    if "academic_terms" in tables:
        op.drop_table("academic_terms")
