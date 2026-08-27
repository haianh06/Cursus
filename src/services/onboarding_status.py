"""Whether a user still needs to go through onboarding.

The mandatory profile-setup + semester-setup gate (blocking every screen
behind /onboarding until a STUDENT has an active SemesterSetup) has been
removed from the product flow: it doesn't match how accounts are actually
used here (demo role selection, invited accounts) and left users with no
way back out of it. Every user is now considered onboarded from account
creation; a student still sets up their semester from within the app
(Timetable / Semester Setup screens), just not as a forced gate.
"""

from __future__ import annotations

from sqlalchemy.orm import Session

from src.db import models


def is_onboarded(db: Session, user: models.User) -> bool:
    return True
