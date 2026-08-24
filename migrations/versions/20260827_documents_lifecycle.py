"""Add curriculum lifecycle columns to documents table

Revision ID: 20260827_documents_lifecycle
Revises: 20260826_data_requests
Create Date: 2026-08-27

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '20260827_documents_lifecycle'
down_revision: Union[str, None] = '20260826_data_requests'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _existing_columns(table: str) -> set[str]:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if table not in inspector.get_table_names():
        return set()
    return {col["name"] for col in inspector.get_columns(table)}

def upgrade() -> None:
    existing = _existing_columns('documents')
    
    if 'scope' not in existing:
        op.add_column('documents', sa.Column('scope', sa.String(), nullable=True))
    if 'publication_status' not in existing:
        op.add_column('documents', sa.Column('publication_status', sa.String(), nullable=True))
    if 'version_group' not in existing:
        op.add_column('documents', sa.Column('version_group', sa.String(), nullable=True))
    if 'provenance' not in existing:
        op.add_column('documents', sa.Column('provenance', sa.JSON(), nullable=True))
    if 'checksum' not in existing:
        op.add_column('documents', sa.Column('checksum', sa.String(), nullable=True))
    if 'validated_at' not in existing:
        op.add_column('documents', sa.Column('validated_at', sa.DateTime(), nullable=True))
    if 'validated_by' not in existing:
        op.add_column('documents', sa.Column('validated_by', sa.String(), sa.ForeignKey('users.id', ondelete='SET NULL'), nullable=True))
    if 'published_at' not in existing:
        op.add_column('documents', sa.Column('published_at', sa.DateTime(), nullable=True))
    if 'published_by' not in existing:
        op.add_column('documents', sa.Column('published_by', sa.String(), sa.ForeignKey('users.id', ondelete='SET NULL'), nullable=True))
    if 'archived_at' not in existing:
        op.add_column('documents', sa.Column('archived_at', sa.DateTime(), nullable=True))
    if 'change_reason' not in existing:
        op.add_column('documents', sa.Column('change_reason', sa.Text(), nullable=True))

    # Populate defaults if they were just added or are empty
    op.execute("UPDATE documents SET scope = 'OFFICIAL', publication_status = 'PUBLISHED' WHERE scope IS NULL")

    # Alter to non-nullable if necessary, but leaving nullable for backward compatibility since the DB is live


def downgrade() -> None:
    op.drop_column('documents', 'change_reason')
    op.drop_column('documents', 'archived_at')
    op.drop_column('documents', 'published_by')
    op.drop_column('documents', 'published_at')
    op.drop_column('documents', 'validated_by')
    op.drop_column('documents', 'validated_at')
    op.drop_column('documents', 'checksum')
    op.drop_column('documents', 'provenance')
    op.drop_column('documents', 'version_group')
    op.drop_column('documents', 'publication_status')
    op.drop_column('documents', 'scope')
