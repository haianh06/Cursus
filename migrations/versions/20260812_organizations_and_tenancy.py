"""Organizations, memberships, invites, access requests + tenant scoping.

Revision ID: 20260812_organizations
Revises: 20260808_baseline
Create Date: 2026-08-12

Additive-only migration for the B2B2C pivot: no pre-existing row is ever
deleted. Adds 4 new tables, adds nullable `organization_id` FK columns to
the 4 "root" identity/catalog tables (users, courses, programs,
curriculum_versions — the only tables where cross-tenant leakage is
directly possible; downstream tables reach organization scoping
transitively through their existing FK to one of these), backfills every
existing row into the single pre-existing tenant ("FPT University"), then
tightens the columns to NOT NULL once the backfill is verified complete.

RLS policies are created for defense-in-depth and future-correctness, but
are NOT the active enforcement boundary today: the app's DATABASE_URL
connects as a role with `rolbypassrls = true` (verified via
`SELECT rolbypassrls FROM pg_roles WHERE rolname = current_user`), so
Postgres skips RLS entirely for this connection. Application-layer
`organization_id` filtering (src/security/tenancy.py) is the real boundary
until a least-privilege, non-BYPASSRLS role is provisioned — see
docs/planning/v2/11-Cursus-ERD-Multitenancy.md.

Rollback is symmetric: drops the NOT NULL constraints, the 4 new columns,
the RLS policies, and the 4 new tables. No pre-existing table loses rows.
"""

from __future__ import annotations

import uuid
from collections.abc import Sequence
from datetime import UTC, datetime

import sqlalchemy as sa
from alembic import op

from src.db.models import Base

# revision identifiers, used by Alembic.
revision: str = "20260812_organizations"
down_revision: str | Sequence[str] | None = "20260808_baseline"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_NEW_TABLES = [
    "organizations",
    "organization_memberships",
    "org_invites",
    "access_requests",
]
_SCOPED_TABLES = ["users", "courses", "programs", "curriculum_versions"]

FPT_ORG_ID = "org_fpt_university"
DEMO_ORG_ID = "org_cursus_demo"


def _existing_columns(table: str) -> set[str]:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if table not in inspector.get_table_names():
        return set()
    return {col["name"] for col in inspector.get_columns(table)}


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    existing_tables = set(inspector.get_table_names())

    new_tables = [name for name in _NEW_TABLES if name not in existing_tables]
    if new_tables:
        Base.metadata.create_all(
            bind=bind, tables=[Base.metadata.tables[name] for name in new_tables]
        )

    for table in _SCOPED_TABLES:
        if "organization_id" not in _existing_columns(table):
            op.add_column(
                table,
                sa.Column(
                    "organization_id",
                    sa.String(),
                    sa.ForeignKey("organizations.id"),
                    nullable=True,
                ),
            )

    now = datetime.now(UTC).replace(tzinfo=None)
    organizations = sa.table(
        "organizations",
        sa.column("id", sa.String),
        sa.column("name", sa.String),
        sa.column("slug", sa.String),
        sa.column("kind", sa.String),
        sa.column("created_at", sa.DateTime),
    )
    bind.execute(
        organizations.insert(),
        [
            {
                "id": FPT_ORG_ID,
                "name": "FPT University",
                "slug": "fpt-university",
                "kind": "production",
                "created_at": now,
            },
            {
                "id": DEMO_ORG_ID,
                "name": "Cursus Demo University",
                "slug": "cursus-demo",
                "kind": "sandbox",
                "created_at": now,
            },
        ],
    )

    # Every pre-existing row genuinely belongs to the one real institution
    # this deployment has served so far.
    for table in _SCOPED_TABLES:
        op.execute(
            sa.text(f"UPDATE {table} SET organization_id = :org_id WHERE organization_id IS NULL")  # noqa: S608
            .bindparams(org_id=FPT_ORG_ID)
        )

    users = sa.table("users", sa.column("id", sa.String), sa.column("role", sa.String))
    existing_users = bind.execute(sa.select(users.c.id, users.c.role)).fetchall()
    if existing_users:
        memberships = sa.table(
            "organization_memberships",
            sa.column("id", sa.String),
            sa.column("user_id", sa.String),
            sa.column("organization_id", sa.String),
            sa.column("role", sa.String),
            sa.column("created_at", sa.DateTime),
        )
        bind.execute(
            memberships.insert(),
            [
                {
                    "id": f"orgmem_{uuid.uuid4().hex}",
                    "user_id": user_id,
                    "organization_id": FPT_ORG_ID,
                    "role": role,
                    "created_at": now,
                }
                for user_id, role in existing_users
            ],
        )

    for table in _SCOPED_TABLES:
        remaining_null = bind.execute(
            sa.text(f"SELECT count(*) FROM {table} WHERE organization_id IS NULL")  # noqa: S608
        ).scalar()
        if remaining_null:
            raise RuntimeError(
                f"Refusing to add NOT NULL: {remaining_null} row(s) in "
                f"'{table}' still have organization_id = NULL"
            )
        # Plain ALTER COLUMN ... SET NOT NULL isn't valid SQLite DDL; batch
        # mode (table-rebuild) works on both SQLite and Postgres.
        with op.batch_alter_table(table) as batch_op:
            batch_op.alter_column("organization_id", nullable=False)

    # RLS: correct policy shape per Supabase's documented pattern, inert
    # today under the BYPASSRLS connection (see module docstring). Postgres
    # only — SQLite (used by fast local/CI migration tests) has no RLS.
    if bind.dialect.name == "postgresql":
        for table in _SCOPED_TABLES:
            op.execute(f"ALTER TABLE {table} ENABLE ROW LEVEL SECURITY")
            op.execute(
                f"CREATE POLICY org_isolation_{table} ON {table} "
                f"USING (organization_id = current_setting('app.current_org_id', true))"
            )


def downgrade() -> None:
    bind = op.get_bind()

    if bind.dialect.name == "postgresql":
        for table in _SCOPED_TABLES:
            op.execute(f"DROP POLICY IF EXISTS org_isolation_{table} ON {table}")
            op.execute(f"ALTER TABLE {table} DISABLE ROW LEVEL SECURITY")
    for table in _SCOPED_TABLES:
        with op.batch_alter_table(table) as batch_op:
            batch_op.alter_column("organization_id", nullable=True)
            batch_op.drop_column("organization_id")

    Base.metadata.drop_all(
        bind=bind, tables=[Base.metadata.tables[name] for name in reversed(_NEW_TABLES)]
    )
