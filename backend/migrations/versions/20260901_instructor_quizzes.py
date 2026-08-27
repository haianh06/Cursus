"""Instructor-authored quizzes: publish flag, open window, question order.

Revision ID: 20260901_instructor_quizzes
Revises: 20260831_class_activity_window
Create Date: 2026-09-01

Thay the luong "Duyet bo on tap" (AI sinh + GV duyet) bang quiz do GV tu tao
va giao theo tung lop (quizzes.section_id da co san). Bang quizzes/
quiz_questions chua co du lieu nen khong can backfill.
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260901_instructor_quizzes"
down_revision: str | Sequence[str] | None = "20260831_class_activity_window"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _existing_columns(table: str) -> set[str]:
    return {col["name"] for col in sa.inspect(op.get_bind()).get_columns(table)}


def upgrade() -> None:
    quiz_columns = _existing_columns("quizzes")
    if "created_by" not in quiz_columns:
        op.add_column("quizzes", sa.Column("created_by", sa.String(), sa.ForeignKey("users.id"), nullable=True))
    if "is_published" not in quiz_columns:
        op.add_column("quizzes", sa.Column("is_published", sa.Boolean(), nullable=False, server_default=sa.false()))
    if "opens_at" not in quiz_columns:
        op.add_column("quizzes", sa.Column("opens_at", sa.DateTime(), nullable=True))
    with op.batch_alter_table("quizzes") as batch_op:
        batch_op.alter_column("due_date", existing_type=sa.DateTime(), nullable=True)

    question_columns = _existing_columns("quiz_questions")
    if "order_index" not in question_columns:
        op.add_column(
            "quiz_questions", sa.Column("order_index", sa.Integer(), nullable=False, server_default="0")
        )


def downgrade() -> None:
    question_columns = _existing_columns("quiz_questions")
    if "order_index" in question_columns:
        op.drop_column("quiz_questions", "order_index")

    quiz_columns = _existing_columns("quizzes")
    with op.batch_alter_table("quizzes") as batch_op:
        batch_op.alter_column("due_date", existing_type=sa.DateTime(), nullable=False)
    if "opens_at" in quiz_columns:
        op.drop_column("quizzes", "opens_at")
    if "is_published" in quiz_columns:
        op.drop_column("quizzes", "is_published")
    if "created_by" in quiz_columns:
        op.drop_column("quizzes", "created_by")
