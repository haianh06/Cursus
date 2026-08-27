"""data_requests.organization_id -- fail-closed org scoping for DSAR requests.

Revision ID: 20260902_data_req_org_scoping
Revises: 20260901_instructor_quizzes
Create Date: 2026-09-02

`data_requests` had no organization column, so an ADMIN of one org could
list/process/reject/complete or run the delete-preview/delete-confirm flow
on another org's DSAR requests through `GET/POST /api/v1/admin/data-
requests/*` -- the same class of gap already fixed for `audit_logs` in
`20260825_audit_log_org_scoping.py`. Nullable + fail-closed for the same
reason: `list_data_requests`/`_get_request` filter by exact match, so a NULL
row is excluded for every admin instead of shown to everyone.

Backfill stamps each existing row with its requester's *current*
organization_id (best-effort, same caveat as the audit_logs backfill).

Column-existence guarded the same way `20260825_audit_log_org_scoping.py`
guards `audit_logs.organization_id`: `data_requests` is in
`20260808_baseline_schema.py`'s `_BASELINE_TABLE_NAMES`... no wait, it was
actually added later in `20260826_data_requests.py`, built straight from the
*current* `Base.metadata` at that time -- so on a fresh DB (created after
this revision) the column already exists by the time this revision runs,
and a plain `ADD COLUMN` would collide. Only a pre-existing DB needs it
added here.
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# Shortened from "20260902_data_request_org_scoping" (33 chars) --
# alembic_version.version_num is VARCHAR(32); see 20260823_risk_policy_admin
# for the same fix and full explanation.
revision: str = "20260902_data_req_org_scoping"
down_revision: str | Sequence[str] | None = "20260901_instructor_quizzes"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    existing_columns = {col["name"] for col in inspector.get_columns("data_requests")}
    if "organization_id" not in existing_columns:
        with op.batch_alter_table("data_requests") as batch_op:
            batch_op.add_column(sa.Column("organization_id", sa.String(), nullable=True))
            batch_op.create_foreign_key(
                "fk_data_requests_organization_id", "organizations", ["organization_id"], ["id"]
            )

    data_requests = sa.table(
        "data_requests",
        sa.column("requester_id", sa.String()),
        sa.column("organization_id", sa.String()),
    )
    users = sa.table(
        "users",
        sa.column("id", sa.String()),
        sa.column("organization_id", sa.String()),
    )
    bind.execute(
        data_requests.update()
        .values(
            organization_id=sa.select(users.c.organization_id)
            .where(users.c.id == data_requests.c.requester_id)
            .scalar_subquery()
        )
        .where(data_requests.c.organization_id.is_(None))
    )

    existing_indexes = {ix["name"] for ix in inspector.get_indexes("data_requests")}
    if "ix_data_requests_organization_id" not in existing_indexes:
        op.create_index("ix_data_requests_organization_id", "data_requests", ["organization_id"])


def downgrade() -> None:
    op.drop_index("ix_data_requests_organization_id", table_name="data_requests")
    with op.batch_alter_table("data_requests") as batch_op:
        batch_op.drop_constraint("fk_data_requests_organization_id", type_="foreignkey")
        batch_op.drop_column("organization_id")
