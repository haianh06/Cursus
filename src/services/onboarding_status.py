"""Whether a user still needs to go through onboarding.

Students used to be gated on having an active semester setup (course +
weekly schedule) before reaching the dashboard. That self-service step is
gone — assigning a student's class schedule is now an admin task, not
something a student declares on first login — so nobody is gated on
onboarding anymore.
"""

from __future__ import annotations

from sqlalchemy.orm import Session

from src.db import models


def is_onboarded(db: Session, user: models.User) -> bool:
    return True
