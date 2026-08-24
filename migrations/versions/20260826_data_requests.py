"""Add data_requests table for DSAR

Revision ID: 20260826_data_requests
Revises: 20260825_audit_log_org_scoping
Create Date: 2026-08-26

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '20260826_data_requests'
down_revision: Union[str, None] = '20260825_audit_log_org_scoping'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if 'data_requests' not in inspector.get_table_names():
        op.create_table(
            'data_requests',
            sa.Column('id', sa.String(), nullable=False),
            sa.Column('requester_id', sa.String(), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
            sa.Column('request_type', sa.String(), nullable=False),
            sa.Column('status', sa.String(), nullable=False),
            sa.Column('admin_notes', sa.Text(), nullable=True),
            sa.Column('preview_summary', sa.JSON(), nullable=True),
            sa.Column('preview_hash', sa.String(), nullable=True),
            sa.Column('result_summary', sa.JSON(), nullable=True),
            sa.Column('processed_by', sa.String(), sa.ForeignKey('users.id', ondelete='SET NULL'), nullable=True),
            sa.Column('created_at', sa.DateTime(), nullable=False),
            sa.Column('updated_at', sa.DateTime(), nullable=False),
            sa.PrimaryKeyConstraint('id')
        )

def downgrade() -> None:
    op.drop_table('data_requests')
