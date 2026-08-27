"""Close RLS coverage gap on academic_terms (org-scoped, missing policy).

Revision ID: 20260822_rls_academic_terms
Revises: 20260821_semester_practice
Create Date: 2026-08-22

`academic_terms` carries `organization_id` directly (added after the
2026-08-12 tenancy migration, see `src/db/models.py` comment "org-scoped
directly") but was never added to that migration's `_SCOPED_TABLES` list, so
it has never had Row Level Security enabled — a real gap, not a
by-design omission like the downstream tables that only reach org scope
transitively through a FK to users/courses.

Same caveat as the 2026-08-12 migration: this policy is inert today because
the app's DATABASE_URL connects as a role with `rolbypassrls = true`. See
`docs/decisions/rls-migration-plan.md` for the steps to provision a
non-BYPASSRLS role on Supabase and make this policy the real enforcement
boundary, not just a defense-in-depth artifact.

Rollback drops the policy and disables RLS on the table; no data is touched.
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "20260822_rls_academic_terms"
down_revision: str | Sequence[str] | None = "20260821_semester_practice"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_TABLE = "academic_terms"


def upgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name != "postgresql":
        # SQLite (fast local/CI migration tests) has no RLS concept.
        return

    op.execute(f"ALTER TABLE {_TABLE} ENABLE ROW LEVEL SECURITY")
    # Guarded: on a fresh DB, 20260821_semester_practice.py's own tail end
    # already creates this exact policy (added there after this migration
    # was written -- the two ended up overlapping). Only pre-existing DBs
    # upgraded before that overlap was introduced still need it created here.
    policy_exists = bind.execute(
        sa.text(
            "SELECT 1 FROM pg_policies WHERE tablename = :table AND policyname = :policy"
        ),
        {"table": _TABLE, "policy": f"org_isolation_{_TABLE}"},
    ).scalar()
    if not policy_exists:
        op.execute(
            f"CREATE POLICY org_isolation_{_TABLE} ON {_TABLE} "
            f"USING (organization_id = current_setting('app.current_org_id', true))"
        )


def downgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name != "postgresql":
        return

    op.execute(f"DROP POLICY IF EXISTS org_isolation_{_TABLE} ON {_TABLE}")
    op.execute(f"ALTER TABLE {_TABLE} DISABLE ROW LEVEL SECURITY")
