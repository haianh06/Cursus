"""Track invitation delivery and resend lifecycle."""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260907_invite_delivery"
down_revision: str | Sequence[str] | None = "20260906_admin_document_versions"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    inspector = sa.inspect(op.get_bind())
    columns = {column["name"] for column in inspector.get_columns("org_invites")}
    with op.batch_alter_table("org_invites") as batch:
        if "delivery_status" not in columns:
            batch.add_column(
                sa.Column("delivery_status", sa.String(), nullable=False, server_default="sent")
            )
        if "resend_count" not in columns:
            batch.add_column(
                sa.Column("resend_count", sa.Integer(), nullable=False, server_default="0")
            )
        if "last_sent_at" not in columns:
            batch.add_column(sa.Column("last_sent_at", sa.DateTime(), nullable=True))


def downgrade() -> None:
    inspector = sa.inspect(op.get_bind())
    columns = {column["name"] for column in inspector.get_columns("org_invites")}
    with op.batch_alter_table("org_invites") as batch:
        for name in ("last_sent_at", "resend_count", "delivery_status"):
            if name in columns:
                batch.drop_column(name)
