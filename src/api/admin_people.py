"""Admin "People" directory — search/filter/paginate every user in the
admin's own organization, each row carrying just enough academic summary to
tell rows apart before opening the full 360 profile.

Ported from the `chung` branch's design (docs/branch-audit/chung-admin-
frontend.md §2.2 / chung-admin-backend.md §2.3) — this branch has no
equivalent endpoint yet (confirmed absent before writing this file).
Deliberately reuses the coarse `require_roles(ADMIN)` gate, same choice
already made in admin_student360.py/admin_instructor360.py, not the finer
Resource/Permission matrix `chung` has -- see admin_student360.py's own
docstring for why that's a separate, larger change.
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func
from sqlalchemy.orm import Session

from src.api.auth import get_current_user_from_token
from src.db import models
from src.db.connection import get_db
from src.security.authorization import require_roles

router = APIRouter(
    prefix="/admin/people",
    tags=["admin-people"],
    dependencies=[Depends(require_roles(models.UserRole.ADMIN))],
)

PAGE_SIZE = 25


def _academic_summary(db: Session, user: models.User) -> dict:
    if user.role == models.UserRole.STUDENT.value:
        enrollments = (
            db.query(func.count(models.Enrollment.id))
            .filter(models.Enrollment.student_id == user.id, models.Enrollment.status == "ENROLLED")
            .scalar()
        ) or 0
        unresolved_risks = (
            db.query(func.count(models.RiskSignal.id))
            .filter(models.RiskSignal.student_id == user.id, models.RiskSignal.resolved_at.is_(None))
            .scalar()
        ) or 0
        return {"enrollments": enrollments, "unresolved_risks": unresolved_risks}
    if user.role == models.UserRole.INSTRUCTOR.value:
        sections = (
            db.query(func.count(models.CourseSection.id))
            .filter(models.CourseSection.instructor_id == user.id)
            .scalar()
        ) or 0
        return {"sections": sections}
    return {}


@router.get("")
def list_people(
    search: str = "",
    role: str = "",
    page: int = Query(default=1, ge=1),
    current_user: models.User = Depends(get_current_user_from_token),
    db: Session = Depends(get_db),
):
    query = db.query(models.User).filter(models.User.organization_id == current_user.organization_id)
    if role:
        query = query.filter(models.User.role == role.strip().upper())
    if search.strip():
        needle = f"%{search.strip().lower()}%"
        query = query.filter(
            func.lower(models.User.full_name).like(needle) | func.lower(models.User.email).like(needle)
        )

    total = query.count()
    users = (
        query.order_by(models.User.full_name.asc())
        .offset((page - 1) * PAGE_SIZE)
        .limit(PAGE_SIZE)
        .all()
    )

    items = [
        {
            "id": user.id,
            "full_name": user.full_name,
            "email": user.email,
            "role": user.role,
            "is_active": user.is_active,
            "academic_summary": _academic_summary(db, user),
        }
        for user in users
    ]

    return {
        "items": items,
        "meta": {
            "page": page,
            "page_size": PAGE_SIZE,
            "total": total,
            "has_next": page * PAGE_SIZE < total,
        },
    }
