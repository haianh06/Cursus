"""Purge legacy reflections created before academic-week naming existed."""
from __future__ import annotations
from collections.abc import Sequence
from alembic import op

revision: str = "20260914_reflection_purge"
down_revision: str | Sequence[str] | None = "20260913_timetable_plan_history"
branch_labels = None
depends_on = None

def upgrade() -> None:
    # Explicit product decision: applies to every account and role.
    op.execute("DELETE FROM weekly_reflections WHERE week_number IN (34, 35)")

def downgrade() -> None:
    # Intentionally irreversible: deleted personal reflection text cannot be reconstructed.
    pass
