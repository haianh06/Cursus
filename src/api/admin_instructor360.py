"""Admin Instructor 360 — aggregate-only summary for one instructor (spec: docs/SPEC_ADMIN_REBUILD_TU_CHUNG_23AUG.md mục 3.4).

Simpler than Student 360: identity + 3 aggregate cards (headcount, risk
load, intervention count) + sections taught.  NO raw-data tabs, NO link
down to individual students — the spec is deliberate about this: "cố tình
không có link đi sâu xuống từng sinh viên từ đây."

Because this route returns only aggregate counts (not raw student data),
it does NOT use the fail-closed audited-read pattern from
admin_student360.py. The summary endpoint is analogous to the Student 360
summary endpoint (which also skips auditing — same reasoning).

Role comparison uses `.value` (string), not the enum instance — per
HANDOFF mục 3.2 (lỗi đã gặp, tránh lặp lại).
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from src.api.auth import get_current_user_from_token
from src.db import models
from src.db.connection import get_db
from src.security.authorization import require_roles

router = APIRouter(
    prefix="/admin/instructors",
    tags=["admin-instructor-360"],
    dependencies=[Depends(require_roles(models.UserRole.ADMIN))],
)


def _require_instructor(db: Session, current_user: models.User, instructor_id: str) -> models.User:
    """Org-scoped fail-closed lookup — same 404 whether the id doesn't exist,
    belongs to a non-instructor, or belongs to another organization."""
    instructor = db.get(models.User, instructor_id)
    if (
        not instructor
        or instructor.role != models.UserRole.INSTRUCTOR.value
        or instructor.organization_id != current_user.organization_id
    ):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="instructor_not_found")
    return instructor


@router.get("/{instructor_id}/summary")
async def get_instructor_summary(
    instructor_id: str,
    current_user: models.User = Depends(get_current_user_from_token),
    db: Session = Depends(get_db),
):
    """Aggregate-only profile — NOT a raw-data route (no audit event).

    Returns identity, 3 aggregate cards, and list of sections taught.
    Deliberately does NOT expose per-student data or links."""
    instructor = _require_instructor(db, current_user, instructor_id)

    # Sections taught by this instructor
    sections = (
        db.query(models.CourseSection, models.Course)
        .join(models.Course, models.Course.id == models.CourseSection.course_id)
        .filter(models.CourseSection.instructor_id == instructor_id)
        .all()
    )

    # Headcount: distinct enrolled students across all sections
    section_ids = [s.id for s, _ in sections]
    headcount = 0
    if section_ids:
        headcount = db.scalar(
            select(func.count(func.distinct(models.Enrollment.student_id)))
            .where(models.Enrollment.section_id.in_(section_ids))
        ) or 0

    # Risk load: open (unresolved) risk signals for students in instructor's sections
    open_risk = 0
    if section_ids:
        open_risk = db.scalar(
            select(func.count(models.RiskSignal.id))
            .where(
                models.RiskSignal.section_id.in_(section_ids),
                models.RiskSignal.resolved_at.is_(None),
            )
        ) or 0

    # Intervention count: total interventions by this instructor
    intervention_count = db.scalar(
        select(func.count(models.InstructorIntervention.id))
        .where(models.InstructorIntervention.instructor_id == instructor_id)
    ) or 0

    return {
        "instructor": {
            "id": instructor.id,
            "fullName": instructor.full_name,
            "email": instructor.email,
            "role": instructor.role.value if hasattr(instructor.role, "value") else str(instructor.role),
            "isActive": instructor.is_active,
        },
        "headcount": headcount,
        "riskLoad": {"openSignals": open_risk},
        "interventionCount": intervention_count,
        "sections": [
            {
                "sectionCode": section.section_code,
                "courseCode": course.code,
                "courseName": course.name,
                "term": section.term,
            }
            for section, course in sections
        ],
    }
