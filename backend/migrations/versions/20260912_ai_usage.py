"""Create the ai_usage table.

Revision ID: 20260912_ai_usage
Revises: 20260911_invite_section
Create Date: 2026-09-12

D1+D2. PLO 5 asks for "giam sat co ban (do tre/loi/chi phi)". Errors were
already covered (structured logging, ingest job status, the Option B quality
trace); latency existed only at the HTTP layer and never separated the LLM
portion; cost was not measured at all. The provider client already returns
`usage_metadata` on every response -- it was being discarded at the point of
receipt.

Deliberately a NEW table. `RAGTrace` and `LLMUsageEvent` exist in the schema
and look like they were built for exactly this, but ADR-017 closed both for
reasons that would recur verbatim if they were reused:

  * `LLMUsageEvent.message_id` is a NOT NULL FK, and `plan_builder` /
    `reflection_engine` produce no `Message` row to point at.
  * `LLMUsageEvent` has no timestamp column, so spend cannot be sliced by
    period -- which is the only question anyone actually asks of it.
  * Neither carries `organization_id`, so per-tenant cost is unanswerable.

`organization_id` and `user_id` are nullable and NOT foreign keys. Some call
sites legitimately have no user context (`qa_answer_service` holds no DB
session at all), and a usage row must never be rejected -- or worse, cascade
away -- because the actor it names was deleted. Losing an audit-adjacent
measurement to a FK is a bad trade for a metrics table.

Indexes on `created_at` (every query filters by period), `organization_id`
(per-tenant rollups) and `feature` (the "which feature costs most" report).
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260912_ai_usage"
down_revision: str | Sequence[str] | None = "20260911_invite_section"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_TABLE = "ai_usage"


def upgrade() -> None:
    inspector = sa.inspect(op.get_bind())
    if _TABLE in inspector.get_table_names():
        return
    op.create_table(
        _TABLE,
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.Column("organization_id", sa.String(), nullable=True),
        sa.Column("user_id", sa.String(), nullable=True),
        sa.Column("feature", sa.String(), nullable=False),
        sa.Column("model", sa.String(), nullable=False),
        sa.Column("input_tokens", sa.Integer(), nullable=True),
        sa.Column("output_tokens", sa.Integer(), nullable=True),
        sa.Column("latency_ms", sa.Integer(), nullable=True),
        sa.Column("success", sa.Boolean(), nullable=True),
    )
    op.create_index(f"ix_{_TABLE}_created_at", _TABLE, ["created_at"], unique=False)
    op.create_index(
        f"ix_{_TABLE}_organization_id", _TABLE, ["organization_id"], unique=False
    )
    op.create_index(f"ix_{_TABLE}_feature", _TABLE, ["feature"], unique=False)


def downgrade() -> None:
    inspector = sa.inspect(op.get_bind())
    if _TABLE not in inspector.get_table_names():
        return
    op.drop_index(f"ix_{_TABLE}_feature", table_name=_TABLE)
    op.drop_index(f"ix_{_TABLE}_organization_id", table_name=_TABLE)
    op.drop_index(f"ix_{_TABLE}_created_at", table_name=_TABLE)
    op.drop_table(_TABLE)
