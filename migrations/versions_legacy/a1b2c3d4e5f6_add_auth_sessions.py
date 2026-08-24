"""Add auth sessions

Revision ID: a1b2c3d4e5f6
Revises: 92b2b506d493
Create Date: 2026-08-04 21:03:00.000000

"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "a1b2c3d4e5f6"
down_revision: str | Sequence[str] | None = "92b2b506d493"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "sessions",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("user_id", sa.String(), nullable=False),
        sa.Column("refresh_token_hash", sa.String(), nullable=False),
        sa.Column("token_family_id", sa.String(), nullable=False),
        sa.Column("device_label", sa.String(), nullable=True),
        sa.Column("user_agent_hash", sa.String(), nullable=True),
        sa.Column("ip_address", sa.String(), nullable=True),
        sa.Column("remember_me", sa.Boolean(), nullable=False),
        sa.Column("revoked_at", sa.DateTime(), nullable=True),
        sa.Column("revoked_reason", sa.String(), nullable=True),
        sa.Column("expires_at", sa.DateTime(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("last_used_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("refresh_token_hash"),
    )
    op.create_index("ix_sessions_user_id", "sessions", ["user_id"], unique=False)
    op.create_index(
        "ix_sessions_refresh_token_hash",
        "sessions",
        ["refresh_token_hash"],
        unique=True,
    )
    op.create_index(
        "ix_sessions_token_family_id",
        "sessions",
        ["token_family_id"],
        unique=False,
    )
    op.create_index(
        "ix_sessions_expires_at",
        "sessions",
        ["expires_at"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_sessions_expires_at", table_name="sessions")
    op.drop_index("ix_sessions_token_family_id", table_name="sessions")
    op.drop_index("ix_sessions_refresh_token_hash", table_name="sessions")
    op.drop_index("ix_sessions_user_id", table_name="sessions")
    op.drop_table("sessions")
