"""Add crisis_escalations — Admin/CTSV-only queue for Cursus Chat crisis-safety
triggers, separate from the instructor-facing guardrail review queue."""
from __future__ import annotations
from collections.abc import Sequence
import sqlalchemy as sa
from alembic import op

revision: str = "20260912_crisis_escalations"
down_revision: str | Sequence[str] | None = "20260911_add_cursus_chat"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "crisis_escalations",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("student_id", sa.String(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("conversation_id", sa.String(), sa.ForeignKey("chat_conversations.id", ondelete="SET NULL"), nullable=True),
        sa.Column("message_excerpt", sa.Text(), nullable=False),
        sa.Column("status", sa.String(), nullable=False, server_default="OPEN"),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("acknowledged_by", sa.String(), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("acknowledged_at", sa.DateTime(), nullable=True),
        sa.Column("resolution_note", sa.Text(), nullable=True),
    )
    op.create_index("ix_crisis_escalations_student_id", "crisis_escalations", ["student_id"])
    op.create_index("ix_crisis_escalations_created_at", "crisis_escalations", ["created_at"])


def downgrade() -> None:
    op.drop_table("crisis_escalations")
