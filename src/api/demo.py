"""Demo control surface for Gate-2 rehearsals.

`GET /demo/seed`   what the fixture contains (version, ids, personas)
`POST /demo/reset` idempotent reset back to the opening state
`POST /demo/fast-forward` apply the Blueprint §7 "Kết quả demo" outcomes to
                   the current week so a rehearsal reaches the Reflect step
                   without six manual clicks.

Fast-forward is explicitly labelled in its response (`simulated: true`) — it
must never be presented on screen as if the student really did the work.
"""

from __future__ import annotations

import uuid
from datetime import date, datetime

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session

from src.api.auth import get_current_user_from_token
from src.db import models
from src.db.connection import get_db
from src.security.authorization import require_roles
from src.services.academic.timetable_service import monday_of
from src.services.ai.plan_builder import serialize_plan
from src.services.ai.risk_engine import RULES_VERSION, RiskEngine, current_rule_catalog
from src.services.mock import gate2_demo
from src.services.mock.gate2_demo import Gate2DemoService

router = APIRouter(
    prefix="/demo",
    tags=["demo"],
    dependencies=[
        Depends(
            require_roles(
                models.UserRole.STUDENT,
                models.UserRole.INSTRUCTOR,
                models.UserRole.ADMIN,
            )
        )
    ],
)


class ResetRequest(BaseModel):
    # Guard against a mis-click during a live demo.
    confirm: bool = True


def _target_student(db: Session, current_user: models.User) -> str:
    role = (
        current_user.role
        if isinstance(current_user.role, str)
        else current_user.role.value
    )
    if role == models.UserRole.STUDENT.value:
        return current_user.id
    demo_student = (
        db.query(models.User)
        .filter_by(email=gate2_demo.DEMO_STUDENT_EMAIL)
        .first()
    )
    return demo_student.id if demo_student else current_user.id


@router.get("/seed")
def get_demo_seed(
    current_user: models.User = Depends(get_current_user_from_token),
    db: Session = Depends(get_db),
):
    info = Gate2DemoService(db).ensure_class()
    assignment = (
        db.query(models.Assignment)
        .filter_by(id=gate2_demo.PART1_ASSIGNMENT_ID)
        .first()
    )
    return {
        "fixtureVersion": gate2_demo.FIXTURE_VERSION,
        "demo": True,
        "class": {
            "id": gate2_demo.CLASS_SECTION_ID,
            "code": gate2_demo.CLASS_SECTION_CODE,
            "term": gate2_demo.CLASS_TERM,
        },
        "course": {
            "id": info["courseId"],
            "code": gate2_demo.SSA101_CODE,
            "syllabusVersion": gate2_demo.SSA101_SYLLABUS_VERSION,
            "officialChunks": info["officialChunks"],
        },
        "assignment": {
            "id": gate2_demo.PART1_ASSIGNMENT_ID,
            "title": gate2_demo.PART1_TITLE,
            "dueAt": assignment.due_date.isoformat() if assignment else None,
            "deliverables": gate2_demo.deliverables_payload(),
            "sourceRefs": list(gate2_demo.PART1_SOURCE_REFS),
            "provenance": {"source_type": "simulated"},
        },
        "personas": [
            {"role": "student", "name": gate2_demo.PERSONA_NAMES[gate2_demo.DEMO_STUDENT_EMAIL]},
            {
                "role": "instructor",
                "name": gate2_demo.PERSONA_NAMES[gate2_demo.DEMO_INSTRUCTOR_EMAIL],
            },
            {"role": "admin", "name": gate2_demo.PERSONA_NAMES[gate2_demo.DEMO_ADMIN_EMAIL]},
            {"role": "student_at_risk", "name": gate2_demo.MINH_NAME},
        ],
        "riskRules": [
            {"code": code, "points": points, "rule": text}
            for code, (points, text) in current_rule_catalog(db).items()
        ],
        "rulesVersion": RULES_VERSION,
    }


@router.post("/reset")
def reset_demo(
    payload: ResetRequest,
    current_user: models.User = Depends(get_current_user_from_token),
    db: Session = Depends(get_db),
):
    if not payload.confirm:
        return {"reset": False, "reason": "confirmation_required"}
    student_id = _target_student(db, current_user)
    result = Gate2DemoService(db).reset(student_id=student_id)
    RiskEngine(db).refresh_section(section_id=gate2_demo.CLASS_SECTION_ID)
    return result


@router.post("/fast-forward")
def fast_forward_week(
    current_user: models.User = Depends(get_current_user_from_token),
    db: Session = Depends(get_db),
):
    """Apply the scripted week outcome to the caller's current plan."""
    student_id = _target_student(db, current_user)
    week_number = monday_of(date.today()).isocalendar().week
    plan = (
        db.query(models.WeeklyPlan)
        .filter_by(student_id=student_id, week_number=week_number)
        .order_by(models.WeeklyPlan.id.desc())
        .first()
    )
    if plan is None:
        return {"applied": False, "reason": "no_plan_for_current_week"}

    goals = dict(plan.goals or {})
    task_meta = dict(goals.get("task_meta") or {})
    rows = (
        db.query(models.StudyTask)
        .join(
            models.ScheduleBlock,
            models.ScheduleBlock.id == models.StudyTask.schedule_block_id,
        )
        .join(
            models.DailyPlan,
            models.DailyPlan.id == models.ScheduleBlock.daily_plan_id,
        )
        .filter(models.DailyPlan.weekly_plan_id == plan.id)
        .all()
    )

    applied = 0
    now = datetime.now()
    for task in rows:
        meta = dict(task_meta.get(task.id) or {})
        outcome = gate2_demo.DEMO_OUTCOMES.get(meta.get("key") or "")
        if not outcome:
            continue
        status = outcome["status"]
        task.status = status
        if outcome.get("actual_minutes") is not None:
            task.actual_minutes = outcome["actual_minutes"]
        if status == "DEFERRED":
            task.rescheduled_count = (task.rescheduled_count or 0) + 1
            meta["defer_count"] = int(meta.get("defer_count") or 0) + 1
            meta["defer_reason"] = outcome.get("reason_code")
            meta["defer_reason_label"] = dict(gate2_demo.DEFER_REASON_CODES).get(
                outcome.get("reason_code")
            )
        task_meta[task.id] = meta

        if status in {"COMPLETED", "DEFERRED"}:
            db.add(
                models.ProgressEvent(
                    id=f"evt_{uuid.uuid4().hex[:10]}",
                    student_id=student_id,
                    task_id=task.id,
                    event_type="TASK_COMPLETED"
                    if status == "COMPLETED"
                    else "TASK_DEFERRED",
                    payload={
                        "status": status,
                        "actual_minutes": outcome.get("actual_minutes"),
                        "reason_code": outcome.get("reason_code"),
                        "simulated": True,
                    },
                    occurred_at=now,
                )
            )
        applied += 1

    goals["task_meta"] = task_meta
    goals["status"] = "APPROVED"
    goals["fast_forwarded"] = True
    plan.goals = goals
    db.commit()

    RiskEngine(db).refresh_student(
        student_id=student_id, section_id=gate2_demo.CLASS_SECTION_ID
    )
    db.commit()

    return {
        "applied": True,
        "simulated": True,
        "note": (
            "Kết quả tuần được mô phỏng theo kịch bản demo, không phải hoạt "
            "động thật của sinh viên."
        ),
        "tasksUpdated": applied,
        "plan": serialize_plan(db, plan),
    }
