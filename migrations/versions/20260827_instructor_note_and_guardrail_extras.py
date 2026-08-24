"""Add risk_signals.instructor_note and 2 extra guardrail_events columns.

Revision ID: 20260827_instr_note_grail_extra
Revises: 20260826_risk_policy_required
Create Date: 2026-08-27

- risk_signals.instructor_note: o ghi chu can thiep GV tu nhap (F5 HITL).
- guardrail_events.created_at: thoi diem cau hoi bi chan that su xay ra, de
  hang doi Appeal hien dung "khi nao" ngay ca voi case con PENDING (truoc day
  chi co reviewed_at, tra None cho toi khi GV xu ly).
- guardrail_events.reviewer_note: ghi chu GV tu nhap khi KEEP/UNBLOCK, cung
  mau voi risk_signals.instructor_note.

Idempotent bang checkfirst, cung pattern voi 20260816_guardrail_reviews.py.
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260827_instr_note_grail_extra"
down_revision: str | Sequence[str] | None = "20260827_documents_lifecycle"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _existing_columns(table: str) -> set[str]:
    inspector = sa.inspect(op.get_bind())
    if table not in inspector.get_table_names():
        return set()
    return {col["name"] for col in inspector.get_columns(table)}


def upgrade() -> None:
    risk_signal_columns = _existing_columns("risk_signals")
    if "instructor_note" not in risk_signal_columns:
        op.add_column("risk_signals", sa.Column("instructor_note", sa.Text(), nullable=True))

    guardrail_columns = _existing_columns("guardrail_events")
    if "created_at" not in guardrail_columns:
        op.add_column("guardrail_events", sa.Column("created_at", sa.DateTime(), nullable=True))
    if "reviewer_note" not in guardrail_columns:
        op.add_column("guardrail_events", sa.Column("reviewer_note", sa.Text(), nullable=True))


def downgrade() -> None:
    guardrail_columns = _existing_columns("guardrail_events")
    if "reviewer_note" in guardrail_columns:
        op.drop_column("guardrail_events", "reviewer_note")
    if "created_at" in guardrail_columns:
        op.drop_column("guardrail_events", "created_at")

    risk_signal_columns = _existing_columns("risk_signals")
    if "instructor_note" in risk_signal_columns:
        op.drop_column("risk_signals", "instructor_note")
