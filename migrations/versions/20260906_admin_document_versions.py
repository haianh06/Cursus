"""Add immutable links and constraints for Admin curriculum versions.

Revision ID: 20260906_admin_document_versions
Revises: 20260905_user_onboarding_profile
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260906_admin_document_versions"
down_revision: str | Sequence[str] | None = "20260905_user_onboarding_profile"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

VERSION_UNIQUE = "uq_documents_version_group_version"
PUBLISHED_UNIQUE = "uq_documents_one_published_per_version_group"
PREVIOUS_FK = "fk_documents_previous_version_id_documents"


def upgrade() -> None:
    inspector = sa.inspect(op.get_bind())
    columns = {column["name"] for column in inspector.get_columns("documents")}
    foreign_keys = {tuple(item["constrained_columns"]) for item in inspector.get_foreign_keys("documents")}
    unique_columns = {tuple(item["column_names"]) for item in inspector.get_unique_constraints("documents")}

    with op.batch_alter_table("documents") as batch:
        if "previous_version_id" not in columns:
            batch.add_column(sa.Column("previous_version_id", sa.String(), nullable=True))
        if ("previous_version_id",) not in foreign_keys:
            batch.create_foreign_key(
                PREVIOUS_FK,
                "documents",
                ["previous_version_id"],
                ["id"],
                ondelete="SET NULL",
            )
        if ("version_group", "version") not in unique_columns:
            batch.create_unique_constraint(VERSION_UNIQUE, ["version_group", "version"])

    indexes = {item["name"] for item in sa.inspect(op.get_bind()).get_indexes("documents")}
    if PUBLISHED_UNIQUE not in indexes:
        published = sa.text("publication_status = 'PUBLISHED'")
        op.create_index(
            PUBLISHED_UNIQUE,
            "documents",
            ["version_group"],
            unique=True,
            sqlite_where=published,
            postgresql_where=published,
        )


def downgrade() -> None:
    inspector = sa.inspect(op.get_bind())
    indexes = {item["name"] for item in inspector.get_indexes("documents")}
    if PUBLISHED_UNIQUE in indexes:
        op.drop_index(PUBLISHED_UNIQUE, table_name="documents")

    foreign_keys = {
        tuple(item["constrained_columns"]): item["name"]
        for item in sa.inspect(op.get_bind()).get_foreign_keys("documents")
    }
    unique_constraints = {
        tuple(item["column_names"]): item["name"]
        for item in sa.inspect(op.get_bind()).get_unique_constraints("documents")
    }
    columns = {column["name"] for column in sa.inspect(op.get_bind()).get_columns("documents")}
    with op.batch_alter_table("documents") as batch:
        unique_name = unique_constraints.get(("version_group", "version"))
        if unique_name:
            batch.drop_constraint(unique_name, type_="unique")
        previous_fk = foreign_keys.get(("previous_version_id",))
        if previous_fk:
            batch.drop_constraint(previous_fk, type_="foreignkey")
        if "previous_version_id" in columns:
            batch.drop_column("previous_version_id")
