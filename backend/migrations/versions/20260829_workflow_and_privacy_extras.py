"""Add users.share_reflection_summary and practice_set_decisions table.

Revision ID: 20260829_workflow_privacy_extras
Revises: 20260828_student_profile_notes
Create Date: 2026-08-29

- users.share_reflection_summary: consent flag (opt-in, default false) SV tu
  bat de cho phep ban tom tat CHI SO (khong phai van ban goc) cua phan tu
  tuan hien cho GV xem trong ho so SV (A1/C2). Xem docs/PROJECT_CONTEXT.md
  muc 14: "Reflection chi tiet mac dinh rieng tu; ban tom tat chia se phai
  co consent".
- practice_set_decisions: nhat ky duyet bo on tap (C3), cung mau voi
  instructor_interventions (F10).

Idempotent bang checkfirst, cung pattern voi cac migration truoc.
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260829_workflow_privacy_extras"
down_revision: str | Sequence[str] | None = "20260828_student_profile_notes"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _existing_columns(table: str) -> set[str]:
    inspector = sa.inspect(op.get_bind())
    if table not in inspector.get_table_names():
        return set()
    return {col["name"] for col in inspector.get_columns(table)}


def _tables() -> set[str]:
    return set(sa.inspect(op.get_bind()).get_table_names())


def upgrade() -> None:
    user_columns = _existing_columns("users")
    if "share_reflection_summary" not in user_columns:
        op.add_column(
            "users",
            sa.Column(
                "share_reflection_summary",
                sa.Boolean(),
                nullable=False,
                server_default=sa.false(),
            ),
        )

    if "practice_set_decisions" not in _tables():
        op.create_table(
            "practice_set_decisions",
            sa.Column("id", sa.String(), primary_key=True),
            sa.Column(
                "set_id",
                sa.String(),
                sa.ForeignKey("practice_sets.id", ondelete="CASCADE"),
                nullable=False,
            ),
            sa.Column("instructor_id", sa.String(), sa.ForeignKey("users.id"), nullable=False),
            sa.Column("decision", sa.String(), nullable=False),
            sa.Column("created_at", sa.DateTime(), nullable=False),
        )
        op.create_index(
            "ix_practice_set_decisions_set_id", "practice_set_decisions", ["set_id"]
        )


def downgrade() -> None:
    if "practice_set_decisions" in _tables():
        op.drop_index("ix_practice_set_decisions_set_id", table_name="practice_set_decisions")
        op.drop_table("practice_set_decisions")

    user_columns = _existing_columns("users")
    if "share_reflection_summary" in user_columns:
        op.drop_column("users", "share_reflection_summary")
