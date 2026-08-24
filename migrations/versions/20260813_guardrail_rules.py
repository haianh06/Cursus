"""Guardrail rule toggle state.

Revision ID: 20260813_guardrail_rules
Revises: 20260812_organizations
Create Date: 2026-08-13
"""

from __future__ import annotations

from collections.abc import Sequence
from datetime import UTC, datetime

import sqlalchemy as sa
from alembic import op

revision: str = "20260813_guardrail_rules"
down_revision: str | Sequence[str] | None = "20260812_organizations"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    guardrail_rules = op.create_table(
        "guardrail_rules",
        sa.Column("code", sa.String(), primary_key=True),
        sa.Column("enabled", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.Column(
            "updated_by",
            sa.String(),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
    )
    seeded_at = datetime.now(UTC).replace(tzinfo=None)
    op.bulk_insert(
        guardrail_rules,
        [
            {"code": "HOMEWORK_VI", "enabled": True, "updated_at": seeded_at},
            {"code": "FULL_CODE", "enabled": True, "updated_at": seeded_at},
            {"code": "HOMEWORK_EN", "enabled": True, "updated_at": seeded_at},
        ],
    )


def downgrade() -> None:
    op.drop_table("guardrail_rules")
