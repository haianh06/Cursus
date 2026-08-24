"""Add instructor review fields to guardrail_events.

Revision ID: 20260816_guardrail_reviews
Revises: 20260815_admin_course_overlay
Create Date: 2026-08-16

Idempotent: baseline create_all already materializes these columns from the
current ORM model (``GuardrailEvent`` in src/db/models.py already declares
review_status/block_reason/blocked_answer/reviewed_by/reviewed_at) on fresh
DBs built via 20260808_baseline_schema.py, so on a fresh DB every column
below is already present and this revision is a no-op. It still upgrades
older DBs that were created before those columns were added to the model.
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260816_guardrail_reviews"
down_revision: str | Sequence[str] | None = "20260815_admin_course_overlay"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _existing_columns(table: str) -> set[str]:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if table not in inspector.get_table_names():
        return set()
    return {col["name"] for col in inspector.get_columns(table)}


def upgrade() -> None:
    existing = _existing_columns("guardrail_events")
    if "review_status" not in existing:
        op.add_column("guardrail_events", sa.Column("review_status", sa.String(), nullable=True))
    if "block_reason" not in existing:
        op.add_column("guardrail_events", sa.Column("block_reason", sa.String(), nullable=True))
    if "blocked_answer" not in existing:
        op.add_column("guardrail_events", sa.Column("blocked_answer", sa.Text(), nullable=True))
    if "reviewed_by" not in existing:
        op.add_column(
            "guardrail_events",
            sa.Column(
                "reviewed_by",
                sa.String(),
                sa.ForeignKey("users.id", ondelete="SET NULL"),
                nullable=True,
            ),
        )
    if "reviewed_at" not in existing:
        op.add_column("guardrail_events", sa.Column("reviewed_at", sa.DateTime(), nullable=True))


def downgrade() -> None:
    existing = _existing_columns("guardrail_events")
    for col in ("reviewed_at", "reviewed_by", "blocked_answer", "block_reason", "review_status"):
        if col in existing:
            op.drop_column("guardrail_events", col)
