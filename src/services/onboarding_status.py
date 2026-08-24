"""Whether a user still needs to go through onboarding.

Deliberately not a stored column: a STUDENT is "onboarded" once they have
an active semester setup (course + weekly schedule), which is also what
makes their Timetable non-empty (see SemesterService.create). Other roles
have nothing to onboard into, so they're always considered onboarded.
"""

from __future__ import annotations

from sqlalchemy.orm import Session

from src.db import models


def is_onboarded(db: Session, user: models.User) -> bool:
    role = user.role if isinstance(user.role, str) else user.role.value
    if role != models.UserRole.STUDENT.value:
        return True
    active = (
        db.query(models.SemesterSetup.id)
        .filter_by(student_id=user.id, is_active=True)
        .first()
    )
    return active is not None
