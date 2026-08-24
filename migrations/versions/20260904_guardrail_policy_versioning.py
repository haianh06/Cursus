"""guardrail_rules.core_locked/current_version/change_reason + guardrail_policy_versions table.

Revision ID: 20260904_guardrail_policy_ver
Revises: 20260902_data_req_org_scoping
Create Date: 2026-09-04

Two gaps closed here, both flagged in docs/archive/SPEC_ADMIN_REBUILD_TU_CHUNG_23AUG.md:

1. `core_locked` -- until now any ADMIN could disable every guardrail rule
   through the UI, including the anti prompt-injection / data-leak rule
   group. That group (PROMPT_INJECTION in guardrail_rules.py) is now marked
   core_locked=True and the repository refuses to disable it -- a safety
   net against a compromised or careless Admin account turning off the
   system's own guardrails.

2. `guardrail_policy_versions` -- every rule change now snapshots the full
   enabled/disabled state as a new version row, so the Admin Console can
   show "what did the policy look like on date X" instead of only the
   current flags. Seeds one "gpv1" version reflecting the current
   (all-enabled) state so `current_version` is never null after this
   migration runs.
"""

from __future__ import annotations

from collections.abc import Sequence
from datetime import datetime

import sqlalchemy as sa
from alembic import op

# Shortened from "20260904_guardrail_policy_versioning" (36 chars) --
# alembic_version.version_num is VARCHAR(32); see 20260823_risk_policy_admin
# for the same fix and full explanation. down_revision also repointed: this
# was authored against "20260902_data_request_org_scoping" before that
# revision id was independently shortened to "20260902_data_req_org_scoping"
# for the same 32-char reason (see that migration).
revision: str = "20260904_guardrail_policy_ver"
down_revision: str | Sequence[str] | None = "20260902_data_req_org_scoping"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_CORE_LOCKED_CODES = ("PROMPT_INJECTION",)


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if "guardrail_policy_versions" not in inspector.get_table_names():
        op.create_table(
            "guardrail_policy_versions",
            sa.Column("version", sa.String(), primary_key=True),
            sa.Column("rules_snapshot", sa.JSON(), nullable=False),
            sa.Column("source_version", sa.String(), nullable=True),
            sa.Column("change_reason", sa.Text(), nullable=True),
            sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.false()),
            sa.Column(
                "created_by", sa.String(), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True
            ),
            sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        )
        op.create_index(
            "ix_guardrail_policy_versions_is_active", "guardrail_policy_versions", ["is_active"]
        )

    existing_columns = {col["name"] for col in inspector.get_columns("guardrail_rules")}
    with op.batch_alter_table("guardrail_rules") as batch_op:
        if "core_locked" not in existing_columns:
            batch_op.add_column(
                sa.Column("core_locked", sa.Boolean(), nullable=False, server_default=sa.false())
            )
        if "current_version" not in existing_columns:
            batch_op.add_column(sa.Column("current_version", sa.String(), nullable=True))
        if "change_reason" not in existing_columns:
            batch_op.add_column(sa.Column("change_reason", sa.Text(), nullable=True))

    guardrail_rules = sa.table(
        "guardrail_rules",
        sa.column("code", sa.String()),
        sa.column("enabled", sa.Boolean()),
        sa.column("core_locked", sa.Boolean()),
        sa.column("current_version", sa.String()),
    )
    bind.execute(
        guardrail_rules.update()
        .where(guardrail_rules.c.code.in_(_CORE_LOCKED_CODES))
        .values(core_locked=True)
    )

    rows = bind.execute(sa.select(guardrail_rules.c.code, guardrail_rules.c.enabled)).fetchall()
    if rows:
        guardrail_policy_versions = sa.table(
            "guardrail_policy_versions",
            sa.column("version", sa.String()),
            sa.column("rules_snapshot", sa.JSON()),
            sa.column("source_version", sa.String()),
            sa.column("change_reason", sa.Text()),
            sa.column("is_active", sa.Boolean()),
            sa.column("created_at", sa.DateTime()),
        )
        bind.execute(
            guardrail_policy_versions.insert().values(
                version="gpv1",
                rules_snapshot={code: bool(enabled) for code, enabled in rows},
                source_version=None,
                change_reason="Initial guardrail policy",
                is_active=True,
                created_at=datetime.utcnow(),
            )
        )
        bind.execute(guardrail_rules.update().values(current_version="gpv1"))


def downgrade() -> None:
    with op.batch_alter_table("guardrail_rules") as batch_op:
        batch_op.drop_column("change_reason")
        batch_op.drop_column("current_version")
        batch_op.drop_column("core_locked")
    op.drop_index("ix_guardrail_policy_versions_is_active", table_name="guardrail_policy_versions")
    op.drop_table("guardrail_policy_versions")
