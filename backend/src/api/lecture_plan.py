"""Lecture-driven weekly plan: a second, independent plan-generation flow.

Separate from Gate 2's assignment-driven planner (`src/api/plans.py`, never
modified here). ``organization_id``/``student_id`` always come from the
authenticated user — never client input, matching the pattern in
`src/api/semester.py`.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from src.api.auth import get_current_user_from_token
from src.db import models
from src.db.connection import get_db
from src.db.models import User
from src.schemas.lecture_plan import LecturePlanGenerateRequest
from src.security.authorization import require_roles
from src.services.academic.lecture_plan_service import LECTURE_PLAN_SOURCE, LecturePlanService
from src.services.ai.plan_builder import serialize_plan

router = APIRouter(
    prefix="/student/lecture-plan",
    tags=["student-lecture-plan"],
    dependencies=[Depends(require_roles(models.UserRole.STUDENT))],
)


@router.post("/generate")
def generate_lecture_plan(
    payload: LecturePlanGenerateRequest,
    current_user: User = Depends(get_current_user_from_token),
    db: Session = Depends(get_db),
):
    service = LecturePlanService(db)
    try:
        plan = service.generate(
            student_id=current_user.id,
            organization_id=current_user.organization_id,
            week_start=payload.week_start,
            available_hours=payload.available_hours,
            language=payload.language,
        )
    except LookupError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    return serialize_plan(db, plan)


@router.get("/{plan_id}")
def get_lecture_plan(
    plan_id: str,
    current_user: User = Depends(get_current_user_from_token),
    db: Session = Depends(get_db),
):
    plan = db.query(models.WeeklyPlan).filter_by(id=plan_id, student_id=current_user.id).first()
    if plan is None or (plan.goals or {}).get("source") != LECTURE_PLAN_SOURCE:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Lecture plan not found")
    return serialize_plan(db, plan)


@router.get("")
def get_latest_lecture_plan(
    week_number: int | None = None,
    current_user: User = Depends(get_current_user_from_token),
    db: Session = Depends(get_db),
):
    """Most recently generated lecture plan for this student (optionally for
    a specific week number) — never touches Gate 2's WeeklyPlan rows since
    it filters strictly on ``goals.source == "lecture_plan"``.

    Returns `null` (200), not 404, when the student simply hasn't generated
    one yet — this is the "list the current one, if any" read the Lecture
    Plan screen polls on every load, not a lookup by id, so an empty result
    is a normal state rather than an error the caller must catch.
    """
    query = db.query(models.WeeklyPlan).filter_by(student_id=current_user.id)
    if week_number is not None:
        query = query.filter_by(week_number=week_number)
    candidates = [
        plan for plan in query.order_by(models.WeeklyPlan.id.desc()).all()
        if (plan.goals or {}).get("source") == LECTURE_PLAN_SOURCE
    ]
    if not candidates:
        return None
    return serialize_plan(db, candidates[0])
