"""Add verification tokens

Revision ID: b2c3d4e5f6a7
Revises: a1b2c3d4e5f6
Create Date: 2026-08-04 21:18:00.000000

"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "b2c3d4e5f6a7"
down_revision: str | Sequence[str] | None = "a1b2c3d4e5f6"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "verification_tokens",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("user_id", sa.String(), nullable=False),
        sa.Column("token_hash", sa.String(), nullable=False),
        sa.Column("purpose", sa.String(), nullable=False),
        sa.Column("used_at", sa.DateTime(), nullable=True),
        sa.Column("expires_at", sa.DateTime(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("token_hash"),
    )
    op.create_index(
        "ix_verification_tokens_user_id",
        "verification_tokens",
        ["user_id"],
        unique=False,
    )
    op.create_index(
        "ix_verification_tokens_token_hash",
        "verification_tokens",
        ["token_hash"],
        unique=True,
    )
    op.create_index(
        "ix_verification_tokens_purpose",
        "verification_tokens",
        ["purpose"],
        unique=False,
    )
    op.create_index(
        "ix_verification_tokens_expires_at",
        "verification_tokens",
        ["expires_at"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_verification_tokens_expires_at", table_name="verification_tokens")
    op.drop_index("ix_verification_tokens_purpose", table_name="verification_tokens")
    op.drop_index(
        "ix_verification_tokens_token_hash",
        table_name="verification_tokens",
    )
    op.drop_index("ix_verification_tokens_user_id", table_name="verification_tokens")
    op.drop_table("verification_tokens")
