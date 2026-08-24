"""Risk policy versioning + per-org admin settings.

Revision ID: 20260823_risk_policy_admin
Revises: 20260822_rls_academic_terms
Create Date: 2026-08-23

mục 14.1 PROJECT_CONTEXT.md: Admin phải chỉnh được ngưỡng/trọng số risk score
qua UI với versioning đầy đủ (policy_version tăng dần, effective_from, alert
ghim lại version đã dùng, không ghi đè lịch sử). Seeds exactly one policy row
(version 1) with the values `src/services/ai/risk_engine.py` hardcoded before
this migration, so behaviour is byte-identical immediately after upgrade —
nothing needs the Admin Console to have been touched yet for scoring to work.

mục 6.5: admin_settings (demo mode / auto risk alerts / default semester),
one row per organization. Rows are created lazily by
`AdminSettingsRepository.ensure_seeded()` on first read, same pattern as
`GuardrailRuleRepository` — this migration only creates the table.

`risk_signals.policy_version` add-column is guarded the same way
20260816_guardrail_reviews.py guards its columns: `risk_signals` is in
20260808_baseline_schema.py's `_BASELINE_TABLE_NAMES`, and that migration
builds its tables straight from the *current* `Base.metadata` — so on a
fresh DB, `policy_version` already exists on `risk_signals` by the time this
revision runs, and `ADD COLUMN` would collide. Only pre-existing (upgraded)
DBs actually need it added here.
"""

from __future__ import annotations

from collections.abc import Sequence
from datetime import UTC, datetime

import sqlalchemy as sa
from alembic import op

# Shortened from "20260823_risk_policy_and_admin_settings" (39 chars) --
# alembic_version.version_num is VARCHAR(32); the longer id overflowed it
# on Postgres (SQLite has no length enforcement, which is why this only
# surfaced running against real Postgres, not the SQLite-backed test suite).
revision: str = "20260823_risk_policy_admin"
down_revision: str | Sequence[str] | None = "20260822_rls_academic_terms"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    existing_tables = set(inspector.get_table_names())

    # Guarded the same way 20260821_semester_practice.py guards its own new
    # tables: 20260808_baseline_schema.py's create_all() now needs
    # `risk_policies` to already exist (risk_signals.policy_version has a
    # live FK to it), so on a fresh DB this table is already there by the
    # time this migration runs. Only pre-existing (already-upgraded) DBs
    # actually need it created here.
    risk_policies_is_new = "risk_policies" not in existing_tables
    if risk_policies_is_new:
        risk_policies = op.create_table(
            "risk_policies",
            sa.Column("policy_version", sa.Integer(), primary_key=True, autoincrement=True),
            sa.Column("effective_from", sa.DateTime(), nullable=False),
            sa.Column("signal_weights", sa.JSON(), nullable=False),
            sa.Column("signal_thresholds", sa.JSON(), nullable=False),
            sa.Column("severity_bands", sa.JSON(), nullable=False),
            sa.Column("reason", sa.Text(), nullable=False),
            sa.Column("rolled_back_from", sa.Integer(), nullable=True),
            sa.Column(
                "created_by", sa.String(), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True
            ),
            sa.Column("created_at", sa.DateTime(), nullable=False),
        )
    else:
        risk_policies = sa.table(
            "risk_policies",
            sa.column("policy_version", sa.Integer),
            sa.column("effective_from", sa.DateTime),
            sa.column("signal_weights", sa.JSON),
            sa.column("signal_thresholds", sa.JSON),
            sa.column("severity_bands", sa.JSON),
            sa.column("reason", sa.Text),
            sa.column("rolled_back_from", sa.Integer),
            sa.column("created_by", sa.String),
            sa.column("created_at", sa.DateTime),
        )

    seeded_at = datetime.now(UTC).replace(tzinfo=None)
    existing_policy_count = (
        0 if risk_policies_is_new
        else bind.execute(sa.text("SELECT count(*) FROM risk_policies")).scalar()
    )
    if not existing_policy_count:
        op.bulk_insert(
            risk_policies,
            [
                {
                    "policy_version": 1,
                    "effective_from": seeded_at,
                    "signal_weights": {
                        "OVERDUE_TASKS_2_PLUS": 2,
                        "COMPLETION_BELOW_40": 2,
                        "TASK_DEFERRED_2_PLUS": 1,
                        "DUE_WITHIN_48H_NOT_STARTED": 1,
                        "INACTIVE_7_DAYS": 2,
                    },
                    "signal_thresholds": {
                        "OVERDUE_TASKS_2_PLUS": 2,
                        "COMPLETION_BELOW_40": 0.4,
                        "TASK_DEFERRED_2_PLUS": 2,
                        "DUE_WITHIN_48H_NOT_STARTED": 48,
                    },
                    "severity_bands": [[0, "normal", "LOW"], [3, "watch", "MEDIUM"], [5, "needs_support", "HIGH"]],
                    "reason": "Initial policy - seeded from pre-versioning hardcoded defaults (risk_rules_v1).",
                    "rolled_back_from": None,
                    "created_by": None,
                    "created_at": seeded_at,
                }
            ],
        )

    existing_columns = {col["name"] for col in inspector.get_columns("risk_signals")}
    if "policy_version" not in existing_columns:
        op.add_column(
            "risk_signals",
            sa.Column(
                "policy_version",
                sa.Integer(),
                sa.ForeignKey("risk_policies.policy_version", ondelete="SET NULL"),
                nullable=True,
            ),
        )

    op.create_table(
        "admin_settings",
        sa.Column(
            "organization_id",
            sa.String(),
            sa.ForeignKey("organizations.id", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.Column("demo_mode_enabled", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("auto_risk_alerts_enabled", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("default_semester", sa.String(), nullable=False, server_default="Fall2026"),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.Column(
            "updated_by", sa.String(), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True
        ),
    )


def downgrade() -> None:
    op.drop_table("admin_settings")
    op.drop_column("risk_signals", "policy_version")
    op.drop_table("risk_policies")
