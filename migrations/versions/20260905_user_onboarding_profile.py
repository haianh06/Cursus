"""Restore users.major/student_code/preferences (a46db63 restoration, item 1).

Revision ID: 20260905_user_onboarding_profile
Revises: 20260902_student_role_restore

These three columns existed on the pre-merge `develop` branch (see
docs/planning/STUDENT_ROLE_RESTORE_SPEC.md §7) and were dropped when merge
d764153 replaced that architecture. `is_onboarded()`
(src/services/onboarding_status.py) and the Settings-screen mascot
preference sync both need them again. Idempotent via `_existing_columns`
so it's safe to re-run on a DB that already has them.
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260905_user_onboarding_profile"
down_revision: str | Sequence[str] | None = "20260902_student_role_restore"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _existing_columns(table_name: str) -> set[str]:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    return {col["name"] for col in inspector.get_columns(table_name)}


def upgrade() -> None:
    columns = _existing_columns("users")
    with op.batch_alter_table("users") as batch_op:
        if "major" not in columns:
            batch_op.add_column(sa.Column("major", sa.String(), nullable=True))
        if "student_code" not in columns:
            batch_op.add_column(sa.Column("student_code", sa.String(), nullable=True))
        if "preferences" not in columns:
            batch_op.add_column(sa.Column("preferences", sa.JSON(), nullable=True))


def downgrade() -> None:
    columns = _existing_columns("users")
    with op.batch_alter_table("users") as batch_op:
        if "preferences" in columns:
            batch_op.drop_column("preferences")
        if "student_code" in columns:
            batch_op.drop_column("student_code")
        if "major" in columns:
            batch_op.drop_column("major")
