"""Admin course overlays and ingest jobs.

Revision ID: 20260815_admin_course_overlay
Revises: 20260813_guardrail_rules
Create Date: 2026-08-15
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260815_admin_course_overlay"
down_revision: str | Sequence[str] | None = "20260813_guardrail_rules"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "admin_course_overrides",
        sa.Column("subject_code", sa.String(), primary_key=True),
        sa.Column("subject_name", sa.String(), nullable=True),
        sa.Column("semester", sa.String(), nullable=True),
        sa.Column("is_added", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("hidden", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.Column("updated_by", sa.String(), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
    )
    op.create_table(
        "course_ingest_jobs",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("course_code", sa.String(), nullable=False),
        sa.Column("document_id", sa.String(), sa.ForeignKey("documents.id", ondelete="SET NULL"), nullable=True),
        sa.Column("operation", sa.String(), nullable=False),
        sa.Column("status", sa.String(), nullable=False),
        sa.Column("error", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("completed_at", sa.DateTime(), nullable=True),
    )
    op.create_index("ix_course_ingest_jobs_course_code", "course_ingest_jobs", ["course_code"])
    op.create_index("ix_course_ingest_jobs_document_id", "course_ingest_jobs", ["document_id"])
    op.create_index("ix_course_ingest_jobs_status", "course_ingest_jobs", ["status"])
    op.create_index("ix_course_ingest_jobs_created_at", "course_ingest_jobs", ["created_at"])


def downgrade() -> None:
    op.drop_table("course_ingest_jobs")
    op.drop_table("admin_course_overrides")
