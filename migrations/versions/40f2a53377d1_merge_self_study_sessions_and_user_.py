"""merge self_study_sessions and user_onboarding_profile heads

Revision ID: 40f2a53377d1
Revises: 20260821_self_study_sessions, 20260905_user_onboarding_profile
Create Date: 2026-08-25 11:50:21.889750

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '40f2a53377d1'
down_revision: Union[str, Sequence[str], None] = ('20260821_self_study_sessions', '20260905_user_onboarding_profile')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
