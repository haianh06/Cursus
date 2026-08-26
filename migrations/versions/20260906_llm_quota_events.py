"""Add llm_quota_events table.

Revision ID: 20260906_llm_quota_events
Revises: 20260905_user_onboarding_profile

Tracks every real 429 RESOURCE_EXHAUSTED response from the LLM provider, so
admin has a quota-status panel and the chat UI can show a "using fallback"
badge — see `src/services/core/llm_quota_service.py`. Idempotent via
`_existing_tables` so it's safe to re-run.
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260906_llm_quota_events"
down_revision: str | Sequence[str] | None = "20260905_user_onboarding_profile"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _existing_tables() -> set[str]:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    return set(inspector.get_table_names())


def upgrade() -> None:
    if "llm_quota_events" in _existing_tables():
        return
    op.create_table(
        "llm_quota_events",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("occurred_at", sa.DateTime(), nullable=False),
        sa.Column("model", sa.String(), nullable=False),
        sa.Column("source", sa.String(), nullable=False),
    )
    op.create_index(
        "ix_llm_quota_events_occurred_at", "llm_quota_events", ["occurred_at"]
    )


def downgrade() -> None:
    if "llm_quota_events" not in _existing_tables():
        return
    op.drop_index("ix_llm_quota_events_occurred_at", table_name="llm_quota_events")
    op.drop_table("llm_quota_events")
