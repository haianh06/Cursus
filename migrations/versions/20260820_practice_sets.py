"""Shared lecture practice sets (MCQ + flashcards) with instructor review.

Revision ID: 20260820_practice_sets
Revises: 20260819_academic_term
Create Date: 2026-08-20
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260820_practice_sets"
down_revision: str | Sequence[str] | None = "20260819_academic_term"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _tables() -> set[str]:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    return set(inspector.get_table_names())


def upgrade() -> None:
    tables = _tables()
    if "practice_sets" not in tables:
        op.create_table(
            "practice_sets",
            sa.Column("id", sa.String(), primary_key=True),
            sa.Column(
                "course_id",
                sa.String(),
                sa.ForeignKey("courses.id", ondelete="CASCADE"),
                nullable=False,
            ),
            sa.Column("course_code", sa.String(), nullable=False),
            sa.Column("slide_key", sa.String(), nullable=False),
            sa.Column("week_number", sa.Integer(), nullable=False),
            sa.Column("status", sa.String(), nullable=False),
            sa.Column("language", sa.String(), nullable=False, server_default="vi"),
            sa.Column(
                "requested_by",
                sa.String(),
                sa.ForeignKey("users.id", ondelete="SET NULL"),
                nullable=True,
            ),
            sa.Column(
                "reviewed_by",
                sa.String(),
                sa.ForeignKey("users.id", ondelete="SET NULL"),
                nullable=True,
            ),
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
            sa.Column(
                "set_id",
                sa.String(),
                sa.ForeignKey("practice_sets.id", ondelete="CASCADE"),
                nullable=False,
            ),
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


def downgrade() -> None:
    tables = _tables()
    if "practice_items" in tables:
        op.drop_index("ix_practice_items_set_id", table_name="practice_items")
        op.drop_table("practice_items")
    if "practice_sets" in tables:
        op.drop_index("ix_practice_sets_status", table_name="practice_sets")
        op.drop_index("ix_practice_sets_slide_key", table_name="practice_sets")
        op.drop_index("ix_practice_sets_course_code", table_name="practice_sets")
        op.drop_index("ix_practice_sets_course_id", table_name="practice_sets")
        op.drop_table("practice_sets")
