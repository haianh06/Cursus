"""Add short-lived Cursus Chat storage."""
from __future__ import annotations
from collections.abc import Sequence
import sqlalchemy as sa
from alembic import op

revision: str = "20260911_add_cursus_chat"
down_revision: str | Sequence[str] | None = "20260910_remove_chatbot_feature"
branch_labels = None
depends_on = None

def upgrade() -> None:
    op.create_table("chat_conversations", sa.Column("id", sa.String(), primary_key=True), sa.Column("student_id", sa.String(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False), sa.Column("created_at", sa.DateTime(), nullable=False), sa.Column("updated_at", sa.DateTime(), nullable=False), sa.Column("expires_at", sa.DateTime(), nullable=False))
    op.create_index("ix_chat_conversations_student_id", "chat_conversations", ["student_id"])
    op.create_index("ix_chat_conversations_expires_at", "chat_conversations", ["expires_at"])
    op.create_table("chat_messages", sa.Column("id", sa.String(), primary_key=True), sa.Column("conversation_id", sa.String(), sa.ForeignKey("chat_conversations.id", ondelete="CASCADE"), nullable=False), sa.Column("role", sa.String(), nullable=False), sa.Column("content", sa.Text(), nullable=False), sa.Column("metadata_info", sa.JSON(), nullable=False), sa.Column("created_at", sa.DateTime(), nullable=False))
    op.create_index("ix_chat_messages_conversation_id", "chat_messages", ["conversation_id"])
    op.create_table("chat_briefing_impressions", sa.Column("id", sa.String(), primary_key=True), sa.Column("student_id", sa.String(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False), sa.Column("briefing_key", sa.String(), nullable=False), sa.Column("shown_at", sa.DateTime(), nullable=False))
    op.create_index("ix_chat_briefing_impressions_student_id", "chat_briefing_impressions", ["student_id"])
    op.create_table("chat_action_proposals", sa.Column("id", sa.String(), primary_key=True), sa.Column("student_id", sa.String(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False), sa.Column("action_type", sa.String(), nullable=False), sa.Column("payload", sa.JSON(), nullable=False), sa.Column("status", sa.String(), nullable=False), sa.Column("expires_at", sa.DateTime(), nullable=False))

def downgrade() -> None:
    op.drop_table("chat_action_proposals")
    op.drop_table("chat_briefing_impressions")
    op.drop_table("chat_messages")
    op.drop_table("chat_conversations")
