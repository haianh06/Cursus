"""Make GuardrailEvent self-contained: student_id, section_id, nullable message_id.

Revision ID: 20260908_guardrail_scoping
Revises: 20260907_invite_delivery
Create Date: 2026-09-08

Review finding (Critical): `guardrail_events.message_id` was
`ForeignKey("messages.id", ondelete="CASCADE")`, and `messages.conversation_id`
is itself `ondelete="CASCADE"`. `DELETE /student/companion/threads/{id}` (and
the per-course thread eviction in `ConversationRepository.delete_oldest_for_
course`) therefore cascaded conversation -> messages -> guardrail_events: a
student blocked for asking the AI to do graded work could delete the thread
and erase the instructor's only record of the incident. On SQLite (this
project's test/dev backend, which never enables `PRAGMA foreign_keys`) the
rows were merely orphaned instead of deleted -- but `_visible_guardrail_
events` then resolved `conversation = None` -> `conv_section_id = None`,
which is the same branch used for genuinely unscoped questions, so the
"orphaned" case leaked to *every* instructor instead of just its owner.

`message_id` alone can never fix the second half of that (an event with no
message can't be traced back to a section), so this migration also adds
`student_id` and `section_id` directly on `guardrail_events`, captured by
`guardrail_event_recorder.record_block` at write time. The row is now
self-contained: it survives its message being purged AND still knows which
student/section it belongs to. `_visible_guardrail_events` and
`OwnershipRepository.instructor_owns_guardrail_event` prefer these columns
and fall back to deriving them from the conversation only for rows written
before this migration.

Idempotent (checks columns/constraints before touching them) so it is safe
to re-run against a database that already has some of this shape, following
the pattern of every other migration in this directory.
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260908_guardrail_scoping"
down_revision: str | Sequence[str] | None = "20260907_invite_delivery"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_MESSAGE_FK = "fk_guardrail_events_message_id"
_STUDENT_FK = "fk_guardrail_events_student_id"
_SECTION_FK = "fk_guardrail_events_section_id"


def _columns(inspector: sa.engine.reflection.Inspector) -> dict[str, dict]:
    return {col["name"]: col for col in inspector.get_columns("guardrail_events")}


def _fk_name(inspector: sa.engine.reflection.Inspector, *, referred_table: str, column: str) -> str | None:
    for fk in inspector.get_foreign_keys("guardrail_events"):
        if fk.get("referred_table") == referred_table and fk.get("constrained_columns") == [column]:
            return fk.get("name")
    return None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    columns = _columns(inspector)

    if "student_id" not in columns or "section_id" not in columns:
        with op.batch_alter_table("guardrail_events") as batch_op:
            if "student_id" not in columns:
                batch_op.add_column(sa.Column("student_id", sa.String(), nullable=True))
                batch_op.create_foreign_key(
                    _STUDENT_FK, "users", ["student_id"], ["id"], ondelete="SET NULL"
                )
            if "section_id" not in columns:
                batch_op.add_column(sa.Column("section_id", sa.String(), nullable=True))
                batch_op.create_foreign_key(
                    _SECTION_FK, "course_sections", ["section_id"], ["id"], ondelete="SET NULL"
                )

    # Re-inspect: the batch above may have recreated the table on SQLite.
    inspector = sa.inspect(bind)
    columns = _columns(inspector)
    message_id_col = columns.get("message_id")
    if message_id_col is not None and not message_id_col["nullable"]:
        # On Postgres this constraint has a real DB-assigned name that must be
        # dropped before adding the replacement, or the old CASCADE stays live
        # side-by-side with the new SET NULL and still destroys the row. On
        # SQLite it reflects as unnamed (batch's table-recreate drops it for
        # us regardless of whether we can name it here).
        message_fk_name = _fk_name(inspector, referred_table="messages", column="message_id")
        with op.batch_alter_table("guardrail_events") as batch_op:
            if message_fk_name:
                batch_op.drop_constraint(message_fk_name, type_="foreignkey")
            batch_op.alter_column("message_id", existing_type=sa.String(), nullable=True)
            batch_op.create_foreign_key(
                _MESSAGE_FK, "messages", ["message_id"], ["id"], ondelete="SET NULL"
            )


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    columns = _columns(inspector)

    message_id_col = columns.get("message_id")
    if message_id_col is not None and message_id_col["nullable"]:
        # Mirror of 20260903_guardrail_event_retention.py's downgrade: rows
        # that lost their message have nothing to backfill a NOT NULL column
        # with, so they can't survive a downgrade to the old shape.
        op.execute(sa.text("DELETE FROM guardrail_events WHERE message_id IS NULL"))
        message_fk_name = _fk_name(inspector, referred_table="messages", column="message_id")
        with op.batch_alter_table("guardrail_events") as batch_op:
            if message_fk_name:
                batch_op.drop_constraint(message_fk_name, type_="foreignkey")
            batch_op.alter_column("message_id", existing_type=sa.String(), nullable=False)
            batch_op.create_foreign_key(
                _MESSAGE_FK, "messages", ["message_id"], ["id"], ondelete="CASCADE"
            )

    inspector = sa.inspect(bind)
    columns = _columns(inspector)
    with op.batch_alter_table("guardrail_events") as batch_op:
        if "section_id" in columns:
            section_fk_name = _fk_name(inspector, referred_table="course_sections", column="section_id")
            if section_fk_name:
                batch_op.drop_constraint(section_fk_name, type_="foreignkey")
            batch_op.drop_column("section_id")
        if "student_id" in columns:
            student_fk_name = _fk_name(inspector, referred_table="users", column="student_id")
            if student_fk_name:
                batch_op.drop_constraint(student_fk_name, type_="foreignkey")
            batch_op.drop_column("student_id")
