# src/api/plans.py
import uuid
from datetime import UTC, date, datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from src.api.auth import get_current_user_from_token
from src.db import models
from src.db.connection import get_db
from src.repositories.ownership_repository import OwnershipRepository
from src.security.authorization import require_roles
from src.security.ownership import require_study_task_owner, require_weekly_plan_owner
from src.services.academic.academic_calendar import current_week_for_student
from src.services.academic.timetable_service import TimetableService, monday_of
from src.services.ai import weekly_plan_engine
from src.services.ai.plan_builder import PlanBuilder, resolve_current_plan, serialize_plan
from src.services.ai.reflection_engine import ReflectionEngine
from src.services.ai.risk_engine import RiskEngine
from src.services.mock import gate2_demo
from src.services.mock.gate2_demo import Gate2DemoService
from src.services.mock.student_mock_data_service import StudentMockDataService

router = APIRouter(
    prefix="/plans",
    tags=["plans"],
    dependencies=[Depends(require_roles(models.UserRole.STUDENT))],
)


class SessionPreference(BaseModel):
    sessions: list[str]


class AvailabilitySlot(BaseModel):
    """One declared free block. Provenance = user_entered."""

    date: date
    availableMinutes: int = Field(..., ge=0, le=24 * 60)  # noqa: N815


class GeneratePlanRequest(BaseModel):
    # StudentPlanner (a46db63 contract): goal_text + subject_code, no
    # assignment. assignment_id stays for any other caller still using the
    # assignment-driven flow (e.g. LecturePlanPanel's own generate call).
    goal_text: str | None = Field(default=None, min_length=1, max_length=500)
    subject_code: str | None = Field(default=None, min_length=2, max_length=32)
    assignment_id: str | None = None
    available_hours: float
    preferred_sessions: list[str]
    availability: list[AvailabilitySlot] | None = None
    week_start: date | None = None


class UpdateTaskRequest(BaseModel):
    status: str
    actual_minutes: int | None = None
    # Blueprint §3.1 "Khi defer bắt buộc chọn lý do ngắn" — enforced below for
    # DEFERRED, optional for every other transition.
    reason_code: str | None = None
    reason_note: str | None = Field(default=None, max_length=500)


class AcceptPlanRequest(BaseModel):
    plan_id: str


class FromReflectionRequest(BaseModel):
    reflection_id: str | None = None
    plan_id: str | None = None
    available_hours: float | None = None
    preferred_sessions: list[str] | None = None


class CreateTimetableBlockRequest(BaseModel):
    title: str = Field(..., min_length=1, max_length=255)
    start: datetime
    end: datetime
    repeatWeeklyUntil: date | None = None  # noqa: N815


class UpdateTimetableBlockRequest(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=255)
    start: datetime | None = None
    end: datetime | None = None
    recurrenceScope: str = "this"  # noqa: N815

@router.get("/timetable")
def get_timetable(
    week_start: date | None = Query(default=None),
    preview_plan_id: str | None = Query(default=None),
    current_user: models.User = Depends(get_current_user_from_token),
    db: Session = Depends(get_db),
):
    StudentMockDataService(db).ensure_if_missing(current_user.id)
    service = TimetableService(db)
    target = monday_of(week_start or date.today())
    return service.get_week(
        student_id=current_user.id, week_start=target, preview_plan_id=preview_plan_id
    )


@router.post("/timetable/bootstrap")
def bootstrap_timetable(
    week_start: date | None = Query(default=None),
    current_user: models.User = Depends(get_current_user_from_token),
    db: Session = Depends(get_db),
):
    """Seed demo class sessions + a sample self-study block for the selected week."""
    service = TimetableService(db)
    target = monday_of(week_start or date.today())
    return service.bootstrap_demo_week(student_id=current_user.id, week_start=target)


@router.post("/timetable/blocks", status_code=201)
def create_timetable_block(
    payload: CreateTimetableBlockRequest,
    current_user: models.User = Depends(get_current_user_from_token),
    db: Session = Depends(get_db),
):
    service = TimetableService(db)
    try:
        return service.create_self_study_block(
            student_id=current_user.id,
            title=payload.title,
            start=payload.start,
            end=payload.end,
            repeat_weekly_until=payload.repeatWeeklyUntil,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.patch("/timetable/blocks/{block_id}")
def update_timetable_block(
    block_id: str,
    payload: UpdateTimetableBlockRequest,
    current_user: models.User = Depends(get_current_user_from_token),
    db: Session = Depends(get_db),
):
    service = TimetableService(db)
    try:
        return service.update_self_study_block(
            student_id=current_user.id,
            block_id=block_id,
            title=payload.title,
            start=payload.start,
            end=payload.end,
            recurrence_scope=payload.recurrenceScope,
        )
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.delete("/timetable/blocks/{block_id}", status_code=204)
def delete_timetable_block(
    block_id: str,
    scope: str = Query(default="this"),
    current_user: models.User = Depends(get_current_user_from_token),
    db: Session = Depends(get_db),
):
    service = TimetableService(db)
    try:
        service.delete_self_study_block(
            student_id=current_user.id, block_id=block_id, scope=scope
        )
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.get("/defer-reasons")
def list_defer_reasons():
    """Fixed vocabulary for the defer dialog — free text is not a reason code."""
    return {
        "reasons": [
            {"code": code, "label": label}
            for code, label in gate2_demo.DEFER_REASON_CODES
        ]
    }


@router.get("/weekly")
def get_weekly_plan(
    week_number: int | None = Query(default=None),
    current_user: models.User = Depends(get_current_user_from_token),
    db: Session = Depends(get_db),
):
    target_week = (
        week_number
        if week_number is not None
        else current_week_for_student(db, current_user.id)
    )
    plan, superseded = resolve_current_plan(
        db, student_id=current_user.id, week_number=target_week, with_superseded=True
    )
    if plan is None:
        raise HTTPException(status_code=404, detail="Weekly plan not found")
    payload = serialize_plan(db, plan)
    if superseded:
        payload["warnings"] = [
            *payload.get("warnings", []),
            "Bạn có một kế hoạch theo lịch học cho tuần này, nhưng kế hoạch từ "
            "assignment đang được ưu tiên hiển thị thay thế.",
        ]
    return payload


@router.get("/{plan_id}")
def get_plan(
    plan_id: str,
    current_user: models.User = Depends(get_current_user_from_token),
    db: Session = Depends(get_db),
):
    plan = db.query(models.WeeklyPlan).filter_by(id=plan_id).first()
    if not plan or plan.student_id != current_user.id:
        # Do not leak the existence of another student's plan.
        raise HTTPException(status_code=404, detail="Weekly plan not found")
    return serialize_plan(db, plan)


@router.post("/generate")
def generate_weekly_plan(
    payload: GeneratePlanRequest,
    current_user: models.User = Depends(get_current_user_from_token),
    db: Session = Depends(get_db),
):
    availability = (
        [
            {"date": slot.date.isoformat(), "availableMinutes": slot.availableMinutes}
            for slot in payload.availability
        ]
        if payload.availability
        else None
    )

    if payload.goal_text and payload.subject_code:
        plan = weekly_plan_engine.generate(
            db,
            student_id=current_user.id,
            goal_text=payload.goal_text,
            subject_code=payload.subject_code,
            available_hours=payload.available_hours,
            preferred_sessions=payload.preferred_sessions,
            availability=availability,
            week_start=payload.week_start,
        )
        db.commit()
        return serialize_plan(db, plan)

    if not payload.assignment_id:
        raise HTTPException(
            status_code=400,
            detail="Cần goal_text + subject_code, hoặc assignment_id.",
        )

    Gate2DemoService(db).ensure_student(current_user.id)
    asg = db.query(models.Assignment).filter_by(id=payload.assignment_id).first()
    # Hide existence of assignments outside the student's enrollments (IDOR).
    if not asg or not OwnershipRepository(db).student_has_assignment_access(
        current_user.id,
        asg.id,
    ):
        raise HTTPException(status_code=404, detail="Assignment not found")

    plan = PlanBuilder(db).generate(
        student_id=current_user.id,
        assignment=asg,
        available_hours=payload.available_hours,
        preferred_sessions=payload.preferred_sessions,
        availability=availability,
        week_start=payload.week_start,
    )
    db.commit()
    return serialize_plan(db, plan)


@router.post("/from-reflection")
def generate_plan_from_reflection(
    payload: FromReflectionRequest,
    current_user: models.User = Depends(get_current_user_from_token),
    db: Session = Depends(get_db),
):
    """Next week's draft, built from the adjustments the student confirmed.

    Only adjustments stored on a *confirmed* reflection are applied, and the
    response carries a `reflectionChanges` diff so the UI can show the causal
    before/after instead of asking the viewer to take it on faith.
    """
    reflection = None
    if payload.reflection_id:
        reflection = (
            db.query(models.WeeklyReflection)
            .filter_by(id=payload.reflection_id, student_id=current_user.id)
            .first()
        )
    elif payload.plan_id:
        plan = db.query(models.WeeklyPlan).filter_by(id=payload.plan_id).first()
        if plan and plan.student_id == current_user.id:
            reflection = (
                db.query(models.WeeklyReflection)
                .filter_by(student_id=current_user.id, week_number=plan.week_number)
                .first()
            )
    if reflection is None:
        reflection = (
            db.query(models.WeeklyReflection)
            .filter_by(student_id=current_user.id)
            .order_by(models.WeeklyReflection.week_number.desc())
            .first()
        )
    if reflection is None:
        raise HTTPException(status_code=404, detail="Reflection not found")

    metrics = reflection.metrics if isinstance(reflection.metrics, dict) else {}
    if not metrics.get("studentConfirmed"):
        raise HTTPException(
            status_code=400,
            detail="Reflection chưa được xác nhận — chỉ điều chỉnh đã xác nhận mới vào kế hoạch.",
        )

    source_plan = (
        db.query(models.WeeklyPlan).filter_by(id=metrics.get("planId")).first()
        if metrics.get("planId")
        else None
    )
    source_kind = (
        source_plan.goals.get("kind")
        if source_plan and isinstance(source_plan.goals, dict)
        else None
    )

    if source_kind == weekly_plan_engine.PLAN_KIND:
        try:
            plan = weekly_plan_engine.regenerate_from_reflection(
                db, student_id=current_user.id, reflection=reflection
            )
        except (LookupError, ValueError) as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        db.commit()
        payload_out = serialize_plan(db, plan)
        payload_out["previousPlan"] = (
            serialize_plan(db, source_plan) if source_plan is not None else None
        )
        payload_out["reflectionId"] = reflection.id
        return payload_out

    assignment_id = None
    if source_plan and isinstance(source_plan.goals, dict):
        assignment_id = source_plan.goals.get("assignment_id")
    assignment = (
        db.query(models.Assignment).filter_by(id=assignment_id).first()
        if assignment_id
        else None
    )
    if assignment is None:
        assignment = (
            db.query(models.Assignment)
            .filter_by(id=gate2_demo.PART1_ASSIGNMENT_ID)
            .first()
        )
    if assignment is None:
        raise HTTPException(status_code=404, detail="Assignment not found")

    previous_week_start = None
    if source_plan and isinstance(source_plan.goals, dict):
        previous_week_start = source_plan.goals.get("week_start")
    base_monday = (
        date.fromisoformat(previous_week_start)
        if previous_week_start
        else monday_of(date.today())
    )
    next_monday = base_monday + timedelta(days=7)

    capacity_hours = payload.available_hours
    if capacity_hours is None and source_plan is not None:
        capacity_hours = source_plan.study_hours_allocated
    sessions = payload.preferred_sessions
    if not sessions and source_plan and isinstance(source_plan.goals, dict):
        sessions = source_plan.goals.get("preferred_sessions")

    plan = PlanBuilder(db).generate(
        student_id=current_user.id,
        assignment=assignment,
        available_hours=float(capacity_hours or 8.0),
        preferred_sessions=sessions,
        week_start=next_monday,
        adjustments=list(metrics.get("adjustments") or []),
        source_reflection_id=reflection.id,
        goal=f"Tuần sau: {assignment.title}",
    )
    db.commit()

    payload_out = serialize_plan(db, plan)
    payload_out["previousPlan"] = (
        serialize_plan(db, source_plan) if source_plan is not None else None
    )
    payload_out["reflectionId"] = reflection.id
    return payload_out


@router.post("/accept")
def accept_weekly_plan(
    payload: AcceptPlanRequest,
    _: None = Depends(require_weekly_plan_owner),
    current_user: models.User = Depends(get_current_user_from_token),
    db: Session = Depends(get_db),
):
    plan = db.query(models.WeeklyPlan).filter_by(id=payload.plan_id).first()
    if not plan:
        raise HTTPException(status_code=404, detail="Weekly plan not found")

    goals = dict(plan.goals or {})
    current_monday = monday_of(date.today())
    if goals.get("kind") == weekly_plan_engine.PLAN_KIND:
        # a46db63 §6.3.5: current week, next week (lets a reflection draft be
        # pre-accepted before its week starts), or the semester's suggested
        # week-start.
        if not weekly_plan_engine.is_plan_acceptable_this_week(
            plan, date.today(), current_week_for_student(db, current_user.id)
        ):
            raise HTTPException(
                status_code=409,
                detail="Weekly plan is not for an acceptable week",
            )
    else:
        stored_week_start = goals.get("week_start")
        if stored_week_start:
            try:
                planned_monday = monday_of(date.fromisoformat(str(stored_week_start)))
            except ValueError as exc:
                raise HTTPException(
                    status_code=409,
                    detail="Weekly plan has invalid week start",
                ) from exc
            if planned_monday != current_monday:
                raise HTTPException(
                    status_code=409,
                    detail="Weekly plan is not for the current week",
                )
        elif plan.week_number != current_week_for_student(db, current_user.id):
            raise HTTPException(
                status_code=409,
                detail="Weekly plan is not for the current week",
            )

    # Schedule first, before committing the approval — if scheduling fails
    # the plan must not be left half-approved (status flip and scheduling
    # commit atomically together).
    timetable_service = TimetableService(db)
    try:
        timetable = timetable_service.schedule_plan_into_gaps(
            student_id=current_user.id,
            plan_id=plan.id,
            week_start=current_monday,
        )
    except LookupError as exc:
        db.rollback()
        raise HTTPException(status_code=409, detail=str(exc)) from exc

    goals["status"] = "APPROVED"
    goals["confirmed_at"] = datetime.now(UTC).isoformat()
    plan.goals = goals
    db.commit()

    return {
        "status": "ACTIVE",
        "plan": serialize_plan(db, plan),
        "timetable": timetable,
    }


_EVENT_FOR_STATUS = {
    "IN_PROGRESS": "TASK_STARTED",
    "COMPLETED": "TASK_COMPLETED",
    "DEFERRED": "TASK_DEFERRED",
    "SKIPPED": "TASK_SKIPPED",
    "TODO": "TASK_RESET",
}


def apply_task_status_update(
    db: Session,
    *,
    task_id: str,
    current_user: models.User,
    status: str,
    actual_minutes: int | None = None,
    reason_code: str | None = None,
    reason_note: str | None = None,
) -> dict:
    """Body of `PATCH /plans/tasks/{task_id}`, extracted so callers other
    than the HTTP route (e.g. Cursus Chat's action-proposal confirm) can
    apply the exact same status-change side effects (ProgressEvent,
    plan.goals task_meta, risk refresh) without going through FastAPI's
    dependency injection. Callers must verify task ownership themselves
    first (the route does it via `require_study_task_owner`)."""
    task = db.query(models.StudyTask).filter_by(id=task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Study task not found")

    status = str(status or "").strip().upper()
    if status not in _EVENT_FOR_STATUS:
        raise HTTPException(status_code=400, detail=f"Unknown task status: {status}")

    valid_reason_codes = {code for code, _ in gate2_demo.DEFER_REASON_CODES}
    if status == "DEFERRED":
        if not reason_code:
            raise HTTPException(
                status_code=400,
                detail="Dời task cần chọn lý do (reason_code).",
            )
        if reason_code not in valid_reason_codes:
            raise HTTPException(
                status_code=400,
                detail=f"Lý do không hợp lệ: {reason_code}",
            )

    task.status = status
    if actual_minutes is not None:
        if actual_minutes < 0:
            raise HTTPException(status_code=400, detail="actual_minutes phải >= 0")
        task.actual_minutes = actual_minutes
    if status == "DEFERRED":
        task.rescheduled_count = (task.rescheduled_count or 0) + 1

    block = db.query(models.ScheduleBlock).filter_by(id=task.schedule_block_id).first()
    daily = (
        db.query(models.DailyPlan).filter_by(id=block.daily_plan_id).first()
        if block
        else None
    )
    plan = (
        db.query(models.WeeklyPlan).filter_by(id=daily.weekly_plan_id).first()
        if daily
        else None
    )

    reason_label = None
    if reason_code:
        reason_label = dict(gate2_demo.DEFER_REASON_CODES).get(reason_code)

    # Task events live in their own table so the Reflect summary and the risk
    # engine can both be recomputed from evidence rather than from a snapshot.
    db.add(
        models.ProgressEvent(
            id=f"evt_{uuid.uuid4().hex[:10]}",
            student_id=current_user.id,
            task_id=task.id,
            event_type=_EVENT_FOR_STATUS[status],
            payload={
                "status": status,
                "actual_minutes": actual_minutes,
                "reason_code": reason_code,
                "reason_label": reason_label,
                "reason_note": reason_note,
            },
            occurred_at=datetime.now(),
        )
    )

    if plan is not None and isinstance(plan.goals, dict):
        goals = dict(plan.goals)
        task_meta = dict(goals.get("task_meta") or {})
        meta = dict(task_meta.get(task.id) or {})
        if status == "DEFERRED":
            meta["defer_count"] = int(meta.get("defer_count") or 0) + 1
            meta["defer_reason"] = reason_code
            meta["defer_reason_label"] = reason_label
            meta["defer_reason_note"] = reason_note
            meta["defer_provenance"] = {
                "source_type": "user_entered",
                "source_id": "defer_dialog",
            }
        task_meta[task.id] = meta
        goals["task_meta"] = task_meta
        plan.goals = goals

    db.commit()

    # Keep the lecturer queue honest the moment behaviour changes.
    try:
        RiskEngine(db).refresh_student(
            student_id=current_user.id, section_id=gate2_demo.CLASS_SECTION_ID
        )
        db.commit()
    except Exception:  # pragma: no cover - risk refresh must never block a click
        db.rollback()

    return {
        "id": task.id,
        "status": task.status,
        "actualMinutes": task.actual_minutes,
        "deferCount": task.rescheduled_count or 0,
        "reasonCode": reason_code,
        "reasonLabel": reason_label,
        "weeklyPlanId": plan.id if plan else None,
        "plan": serialize_plan(db, plan) if plan is not None else None,
    }


@router.patch("/tasks/{task_id}")
def update_study_task(
    task_id: str,
    payload: UpdateTaskRequest,
    _: None = Depends(require_study_task_owner),
    current_user: models.User = Depends(get_current_user_from_token),
    db: Session = Depends(get_db),
):
    return apply_task_status_update(
        db,
        task_id=task_id,
        current_user=current_user,
        status=payload.status,
        actual_minutes=payload.actual_minutes,
        reason_code=payload.reason_code,
        reason_note=payload.reason_note,
    )


@router.get("/reflection/preview")
def reflection_preview(
    week_number: int | None = Query(default=None),
    current_user: models.User = Depends(get_current_user_from_token),
    db: Session = Depends(get_db),
):
    """Evidence + adaptive questions for the Reflect step of a given week."""
    target_week = (
        week_number
        if week_number is not None
        else current_week_for_student(db, current_user.id)
    )
    plan = resolve_current_plan(db, student_id=current_user.id, week_number=target_week)
    if plan is None:
        raise HTTPException(status_code=404, detail="Weekly plan not found")
    return ReflectionEngine(db).preview(plan)
