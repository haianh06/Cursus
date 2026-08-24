"""Add instructor_student_notes table (A3 — student profile private notes).

Revision ID: 20260828_student_profile_notes
Revises: 20260827_instr_note_grail_extra
Create Date: 2026-08-28

Sổ ghi chú riêng của GV về từng SV, độc lập với risk_signals — chỉ tác giả
mới đọc/xoá được ghi chú của chính mình (xem src/api/instructor.py).
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260828_student_profile_notes"
down_revision: str | Sequence[str] | None = "20260827_instr_note_grail_extra"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _tables() -> set[str]:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    return set(inspector.get_table_names())


def upgrade() -> None:
    if "instructor_student_notes" in _tables():
        return
    op.create_table(
        "instructor_student_notes",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column(
            "instructor_id",
            sa.String(),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "student_id",
            sa.String(),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
    )
    op.create_index(
        "ix_instructor_student_notes_instructor_id", "instructor_student_notes", ["instructor_id"]
    )
    op.create_index(
        "ix_instructor_student_notes_student_id", "instructor_student_notes", ["student_id"]
    )


def downgrade() -> None:
    if "instructor_student_notes" not in _tables():
        return
    op.drop_index("ix_instructor_student_notes_student_id", table_name="instructor_student_notes")
    op.drop_index("ix_instructor_student_notes_instructor_id", table_name="instructor_student_notes")
    op.drop_table("instructor_student_notes")
