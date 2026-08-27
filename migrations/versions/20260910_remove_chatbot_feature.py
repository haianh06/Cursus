"""Remove chatbot feature: drop conversations/messages and everything that
only existed to serve chat (student memory, RAG trace, LLM usage events).

Revision ID: 20260910_remove_chatbot_feature
Revises: 20260910_announcement_org
Create Date: 2026-08-27

The chatbot feature (companion/QA/chat, in every iteration it went through)
has been removed from the codebase. `GuardrailEvent` is kept as an
independent feature (its own admin policy UI + instructor review queue) --
20260908_guardrail_scoping.py already made it self-contained via its own
`student_id`/`section_id` columns, so it loses only the now-dangling
`message_id` column/FK once `messages` is gone.

Drop order respects FK dependencies: children of `messages`/`conversations`
first, then `messages`, then `conversations`. Idempotent via table/column
existence checks, matching this repo's existing migration style (see
20260816_guardrail_reviews.py).
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260910_remove_chatbot_feature"
down_revision: str | Sequence[str] | None = "20260910_announcement_org"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _table_names() -> set[str]:
    bind = op.get_bind()
    return set(sa.inspect(bind).get_table_names())


def _existing_columns(table: str) -> set[str]:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if table not in inspector.get_table_names():
        return set()
    return {col["name"] for col in inspector.get_columns(table)}


def upgrade() -> None:
    tables = _table_names()

    if "guardrail_events" in tables and "message_id" in _existing_columns("guardrail_events"):
        with op.batch_alter_table("guardrail_events") as batch_op:
            batch_op.drop_column("message_id")

    for table in ("rag_traces", "llm_usage_events", "student_memory_entries", "student_memory_consent"):
        if table in tables:
            op.drop_table(table)

    if "messages" in tables:
        op.drop_table("messages")
    if "conversations" in tables:
        op.drop_table("conversations")


def downgrade() -> None:
    tables = _table_names()

    if "conversations" not in tables:
        op.create_table(
            "conversations",
            sa.Column("id", sa.String(), primary_key=True),
            sa.Column("student_id", sa.String(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
            sa.Column("section_id", sa.String(), sa.ForeignKey("course_sections.id", ondelete="SET NULL"), nullable=True),
            sa.Column("title", sa.String(), nullable=False),
            sa.Column("subject_code", sa.String(), nullable=True),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.Column("updated_at", sa.DateTime(), nullable=True),
        )

    if "messages" not in tables:
        op.create_table(
            "messages",
            sa.Column("id", sa.String(), primary_key=True),
            sa.Column("conversation_id", sa.String(), sa.ForeignKey("conversations.id", ondelete="CASCADE"), nullable=False),
            sa.Column("sender", sa.String(), nullable=False),
            sa.Column("content", sa.Text(), nullable=False),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.Column("metadata_info", sa.JSON(), nullable=False),
        )

    if "student_memory_consent" not in tables:
        op.create_table(
            "student_memory_consent",
            sa.Column("student_id", sa.String(), sa.ForeignKey("users.id", ondelete="CASCADE"), primary_key=True),
            sa.Column("granted", sa.Boolean(), nullable=False),
            sa.Column("updated_at", sa.DateTime(), nullable=False),
        )

    if "student_memory_entries" not in tables:
        op.create_table(
            "student_memory_entries",
            sa.Column("id", sa.String(), primary_key=True),
            sa.Column("student_id", sa.String(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True),
            sa.Column("subject_code", sa.String(), nullable=True, index=True),
            sa.Column("kind", sa.String(), nullable=False),
            sa.Column("content", sa.String(), nullable=False),
            sa.Column("source_conversation_id", sa.String(), sa.ForeignKey("conversations.id", ondelete="SET NULL"), nullable=True),
            sa.Column("reinforce_count", sa.Integer(), nullable=False),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.Column("last_reinforced_at", sa.DateTime(), nullable=False),
        )

    if "llm_usage_events" not in tables:
        op.create_table(
            "llm_usage_events",
            sa.Column("id", sa.String(), primary_key=True),
            sa.Column("message_id", sa.String(), sa.ForeignKey("messages.id", ondelete="CASCADE"), nullable=False),
            sa.Column("model", sa.String(), nullable=False),
            sa.Column("prompt_tokens", sa.Integer(), nullable=False),
            sa.Column("completion_tokens", sa.Integer(), nullable=False),
            sa.Column("cost", sa.Float(), nullable=False),
        )

    if "rag_traces" not in tables:
        op.create_table(
            "rag_traces",
            sa.Column("id", sa.String(), primary_key=True),
            sa.Column("message_id", sa.String(), sa.ForeignKey("messages.id", ondelete="CASCADE"), nullable=False),
            sa.Column("retrieved_chunks", sa.JSON(), nullable=False),
            sa.Column("generation_metadata", sa.JSON(), nullable=False),
        )

    if "guardrail_events" in _table_names() and "message_id" not in _existing_columns("guardrail_events"):
        with op.batch_alter_table("guardrail_events") as batch_op:
            batch_op.add_column(
                sa.Column(
                    "message_id",
                    sa.String(),
                    sa.ForeignKey("messages.id", ondelete="CASCADE"),
                    nullable=True,
                )
            )
