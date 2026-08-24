"""Add MFA tables

Revision ID: g7h8i9j0k1l2
Revises: f6a7b8c9d0e1
Create Date: 2026-08-05 10:38:00.000000

"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "g7h8i9j0k1l2"
down_revision: str | Sequence[str] | None = "f6a7b8c9d0e1"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "mfa_totp_credentials",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("user_id", sa.String(), nullable=False),
        sa.Column("secret_encrypted", sa.Text(), nullable=False),
        sa.Column("enabled", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("last_used_counter", sa.Integer(), nullable=True),
        sa.Column("failed_attempt_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("locked_until", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("confirmed_at", sa.DateTime(), nullable=True),
        sa.Column("disabled_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id"),
    )
    op.create_index("ix_mfa_totp_credentials_user_id", "mfa_totp_credentials", ["user_id"])
    op.create_index("ix_mfa_totp_credentials_enabled", "mfa_totp_credentials", ["enabled"])

    op.create_table(
        "mfa_recovery_codes",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("user_id", sa.String(), nullable=False),
        sa.Column("code_hash", sa.String(), nullable=False),
        sa.Column("used_at", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("code_hash"),
    )
    op.create_index("ix_mfa_recovery_codes_user_id", "mfa_recovery_codes", ["user_id"])
    op.create_index("ix_mfa_recovery_codes_code_hash", "mfa_recovery_codes", ["code_hash"], unique=True)

    op.create_table(
        "mfa_trusted_devices",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("user_id", sa.String(), nullable=False),
        sa.Column("device_token_hash", sa.String(), nullable=False),
        sa.Column("device_label", sa.String(), nullable=True),
        sa.Column("expires_at", sa.DateTime(), nullable=False),
        sa.Column("revoked_at", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("last_used_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("device_token_hash"),
    )
    op.create_index("ix_mfa_trusted_devices_user_id", "mfa_trusted_devices", ["user_id"])
    op.create_index(
        "ix_mfa_trusted_devices_device_token_hash",
        "mfa_trusted_devices",
        ["device_token_hash"],
        unique=True,
    )
    op.create_index("ix_mfa_trusted_devices_expires_at", "mfa_trusted_devices", ["expires_at"])


def downgrade() -> None:
    op.drop_index("ix_mfa_trusted_devices_expires_at", table_name="mfa_trusted_devices")
    op.drop_index("ix_mfa_trusted_devices_device_token_hash", table_name="mfa_trusted_devices")
    op.drop_index("ix_mfa_trusted_devices_user_id", table_name="mfa_trusted_devices")
    op.drop_table("mfa_trusted_devices")
    op.drop_index("ix_mfa_recovery_codes_code_hash", table_name="mfa_recovery_codes")
    op.drop_index("ix_mfa_recovery_codes_user_id", table_name="mfa_recovery_codes")
    op.drop_table("mfa_recovery_codes")
    op.drop_index("ix_mfa_totp_credentials_enabled", table_name="mfa_totp_credentials")
    op.drop_index("ix_mfa_totp_credentials_user_id", table_name="mfa_totp_credentials")
    op.drop_table("mfa_totp_credentials")
