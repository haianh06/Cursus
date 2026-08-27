"""Make CourseSection.instructor_id nullable.

Revision ID: 20260909_instructor_nullable
Revises: 20260908_guardrail_scoping
Create Date: 2026-09-09

Every path that created a `CourseSection` before this migration (the
student's own semester-setup wizard, the timetable service, mock services,
seed scripts) had to supply an instructor up front -- none of them is Admin,
and worse, `semester_repository.first_instructor_id()` picks the first
instructor row in the organisation and assigns them to every subject a
student declares. Task 6 (src/services/core/admin_section_service.py) gives
Admin a screen to create a section with no instructor and assign one later,
which needs this column to accept NULL. `src/db/models.py` was updated in
the same commit; this migration brings existing databases (already created
by `20260808_baseline_schema.py`, which builds from the *current* ORM
metadata, so a genuinely fresh database is already nullable and this
migration is a no-op there) up to the same shape.

Idempotent (checks the column's nullability before altering), following the
pattern of 20260908_guardrail_event_scoping.py.
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260909_instructor_nullable"
down_revision: str | Sequence[str] | None = "20260908_guardrail_scoping"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _instructor_id_column(inspector: sa.engine.reflection.Inspector) -> dict | None:
    for col in inspector.get_columns("course_sections"):
        if col["name"] == "instructor_id":
            return col
    return None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    column = _instructor_id_column(inspector)
    if column is not None and not column["nullable"]:
        with op.batch_alter_table("course_sections") as batch_op:
            batch_op.alter_column("instructor_id", existing_type=sa.String(), nullable=True)


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    column = _instructor_id_column(inspector)
    if column is not None and column["nullable"]:
        # Mirror of 20260908_guardrail_event_scoping.py's downgrade: rows
        # created with no instructor assigned have nothing to backfill a
        # NOT NULL column with, so they can't survive a downgrade.
        op.execute(sa.text("DELETE FROM course_sections WHERE instructor_id IS NULL"))
        with op.batch_alter_table("course_sections") as batch_op:
            batch_op.alter_column("instructor_id", existing_type=sa.String(), nullable=False)
