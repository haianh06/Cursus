"""Add AdminAnnouncement.organization_id.

Revision ID: 20260910_announcement_org
Revises: 20260909_instructor_nullable
Create Date: 2026-09-10

`admin_announcements` is read by `GET /instructor/announcements` and shown on
the instructor dashboard, but no route ever wrote to it -- the panel was
permanently empty, so the reader's complete lack of an organization filter
never mattered. Task 14 adds `POST /admin/announcements`; the moment the
table holds rows, an unscoped reader would show every school's notices to
every other school's instructors. The model's own docstring says these go to
"TAT CA giang vien", which means all instructors *of one school*.

Nullable, and deliberately not backfilled: any row that predates this column
has no organization to attribute it to, and guessing from `created_by` would
be inventing data. The reader filters on the caller's organization, so those
rows simply stop being visible -- which is the safe direction for a table
that was never supposed to be cross-tenant.

Idempotent (checks for the column before adding it), following the pattern of
20260909_section_instructor_nullable.py.
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260910_announcement_org"
down_revision: str | Sequence[str] | None = "20260909_instructor_nullable"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_TABLE = "admin_announcements"
_COLUMN = "organization_id"


def _has_column(inspector: sa.engine.reflection.Inspector) -> bool:
    if _TABLE not in inspector.get_table_names():
        return True  # nothing to do; treat as already in the target shape
    return any(col["name"] == _COLUMN for col in inspector.get_columns(_TABLE))


def upgrade() -> None:
    inspector = sa.inspect(op.get_bind())
    if _has_column(inspector):
        return
    with op.batch_alter_table(_TABLE) as batch_op:
        batch_op.add_column(sa.Column(_COLUMN, sa.String(), nullable=True))
    op.create_index(
        f"ix_{_TABLE}_{_COLUMN}", _TABLE, [_COLUMN], unique=False
    )


def downgrade() -> None:
    inspector = sa.inspect(op.get_bind())
    if _TABLE not in inspector.get_table_names():
        return
    if not any(col["name"] == _COLUMN for col in inspector.get_columns(_TABLE)):
        return
    op.drop_index(f"ix_{_TABLE}_{_COLUMN}", table_name=_TABLE)
    with op.batch_alter_table(_TABLE) as batch_op:
        batch_op.drop_column(_COLUMN)
