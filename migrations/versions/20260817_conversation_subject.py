"""Add subject_code + updated_at on conversations for per-course chat threads.

Revision ID: 20260817_conv_subject
Revises: 20260816_guardrail_reviews
Create Date: 2026-08-17
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260817_conv_subject"
down_revision: str | Sequence[str] | None = "20260816_guardrail_reviews"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _cols(table: str) -> set[str]:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if table not in inspector.get_table_names():
        return set()
    return {c["name"] for c in inspector.get_columns(table)}


def upgrade() -> None:
    existing = _cols("conversations")
    if "subject_code" not in existing:
        op.add_column("conversations", sa.Column("subject_code", sa.String(), nullable=True))
        op.create_index("ix_conversations_subject_code", "conversations", ["subject_code"])
    if "updated_at" not in existing:
        op.add_column("conversations", sa.Column("updated_at", sa.DateTime(), nullable=True))
        op.execute(sa.text("UPDATE conversations SET updated_at = created_at WHERE updated_at IS NULL"))


def downgrade() -> None:
    existing = _cols("conversations")
    if "updated_at" in existing:
        op.drop_column("conversations", "updated_at")
    if "subject_code" in existing:
        op.drop_index("ix_conversations_subject_code", table_name="conversations")
        op.drop_column("conversations", "subject_code")
