"""audit_logs.organization_id -- fail-closed org scoping for the Audit log.

Revision ID: 20260825_audit_log_org_scoping
Revises: 20260824_mock_lms_sync_versions
Create Date: 2026-08-25

docs/PENDING_DECISIONS.md #2 / PROJECT_CONTEXT.md mục 9 ý2: `audit_logs` had
no organization column at all, so any ADMIN could read every other
organization's audit log through `GET /api/v1/audit/events`. Nullable on
purpose -- a row whose actor no longer exists, or a system event with no
actor at all, can't always resolve to an org; `AuditRepository.list_events()`
filters by exact match, so a NULL row is excluded for every viewer instead
of shown to everyone (fail closed, same choice already made for the admin
analytics/user-status org-scoping fix earlier in this branch's history).

Backfill is best-effort: it stamps each existing row with its actor's
*current* organization_id, not whatever org that actor belonged to at the
moment the event actually happened (this table never stored that, so there
is nothing more precise to recover it from).

Column-existence guarded the same way `20260823_risk_policy_and_admin_
settings.py` guards `risk_signals.policy_version`: `audit_logs` is in
`20260808_baseline_schema.py`'s `_BASELINE_TABLE_NAMES`, built straight from
the *current* `Base.metadata` -- so on a fresh DB this column already exists
by the time this revision runs, and a plain `ADD COLUMN` would collide. Only
a pre-existing (already-upgraded) DB actually needs it added here.

The live Supabase dev DB for this branch has a separately-known, unrelated
`alembic_version` mismatch (PROJECT_CONTEXT.md mục 9 ý8) that keeps this
migration from being run through Alembic there directly -- see
`scripts/sql/add_audit_log_org_scoping_22aug.sql` for the raw-SQL
equivalent of this exact change, meant to be pasted into the Supabase
Dashboard's SQL Editor instead.
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260825_audit_log_org_scoping"
down_revision: str | Sequence[str] | None = "20260824_mock_lms_sync_versions"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    existing_columns = {col["name"] for col in inspector.get_columns("audit_logs")}
    if "organization_id" not in existing_columns:
        op.add_column(
            "audit_logs",
            sa.Column(
                "organization_id",
                sa.String(),
                sa.ForeignKey("organizations.id", ondelete="CASCADE"),
                nullable=True,
            ),
        )

    audit_logs = sa.table(
        "audit_logs",
        sa.column("actor_user_id", sa.String()),
        sa.column("organization_id", sa.String()),
    )
    users = sa.table(
        "users",
        sa.column("id", sa.String()),
        sa.column("organization_id", sa.String()),
    )
    bind.execute(
        audit_logs.update()
        .values(
            organization_id=sa.select(users.c.organization_id)
            .where(users.c.id == audit_logs.c.actor_user_id)
            .scalar_subquery()
        )
        .where(audit_logs.c.organization_id.is_(None))
    )

    existing_indexes = {ix["name"] for ix in inspector.get_indexes("audit_logs")}
    if "ix_audit_logs_organization_id" not in existing_indexes:
        op.create_index("ix_audit_logs_organization_id", "audit_logs", ["organization_id"])


def downgrade() -> None:
    op.drop_index("ix_audit_logs_organization_id", table_name="audit_logs")
    op.drop_column("audit_logs", "organization_id")
