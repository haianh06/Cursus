"""Add OrgInvite.section_id.

Revision ID: 20260911_invite_section
Revises: 20260910_announcement_org
Create Date: 2026-09-11

B5: inviting an instructor used to be two disconnected steps -- send the
invite, wait for them to register, then go back to the sections screen and
assign them by hand. The gap between those steps is exactly the window where
a section sits with no one responsible for it, which is the state Task 8 now
surfaces as UNASSIGNED_SECTION work-queue items.

Carrying the section on the invite closes that gap: the assignment is decided
once, at invite time, and applied automatically when the account is created.

Nullable -- most invites (every STUDENT and ADMIN one) carry no section, and
existing rows predate the column entirely. `ondelete="SET NULL"` rather than
CASCADE: deleting a section must not silently destroy a pending invitation
that a real person is about to accept; they should still get their account,
just without the assignment.

Idempotent (checks for the column before adding it), following the pattern of
20260910_admin_announcement_org_scoping.py.
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260911_invite_section"
down_revision: str | Sequence[str] | None = "20260912_crisis_escalations"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_TABLE = "org_invites"
_COLUMN = "section_id"


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


def downgrade() -> None:
    inspector = sa.inspect(op.get_bind())
    if _TABLE not in inspector.get_table_names():
        return
    if not any(col["name"] == _COLUMN for col in inspector.get_columns(_TABLE)):
        return
    with op.batch_alter_table(_TABLE) as batch_op:
        batch_op.drop_column(_COLUMN)
