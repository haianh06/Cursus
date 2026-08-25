"""Goal-text weekly-plan engine — the a46db63 StudentPlanner contract.

Distinct from `plan_builder.PlanBuilder`, which is assignment-driven (a fixed
demo Assignment row supplies the task template/RAG query). This engine is the
original Student flow: the student types a free-text goal + picks a course,
and the plan is grounded via `RetrievalService` against that course's
ingested chunks — no `Assignment` row involved at all. `WeeklyPlan.goals`
here carries `subject_code`/`statement`, never `assignment_id` (verified
safe: RiskEngine/admin/instructor read deadlines from `Assignment`/
`AssignmentOverride` directly, never from `WeeklyPlan.goals`).

`plan_builder.py` is left untouched — `lecture_plan_service.py` still uses it
for the separate Lecture Plan flow.
"""

from __future__ import annotations

import logging
import uuid
from dataclasses import dataclass
from datetime import date, datetime, time, timedelta

from sqlalchemy.orm import Session

from src.db import models
from src.repositories.chunk_repository import ChunkRepository
from src.schemas.plan import LlmPlanPayload
from src.services.academic.timetable_service import monday_of
from src.services.ai.reflection_suggestion import build_next_week_suggestion
from src.services.core import provenance as prov
from src.services.core.llm import get_llm, has_configured_llm
from src.services.rag.retrieval_service import RetrievalService

logger = logging.getLogger(__name__)

PLANNER_VERSION = "curi_planner_goal_v1"
PLAN_KIND = "weekly_goal"

SESSION_CLOCK: dict[str, tuple[int, int]] = {
    "MORNING": (8, 0),
    "AFTERNOON": (14, 0),
    "EVENING": (19, 30),
}


@dataclass
class GeneratedTask:
    key: str
    title: str
    estimated_minutes: int
    weekday: int
    priority: str
    source_refs: tuple[str, ...] = ()
    source_fact: str | None = None
    suggestion_reason: str = ""


def _generic_templates(goal_text: str) -> list[GeneratedTask]:
    """Honest, uncited 5-step decomposition — used when no LLM is configured
    or the LLM call fails/returns insufficient context. Never claims a
    syllabus source it doesn't have."""
    return [
        GeneratedTask(
            key="understand",
            title=f"Làm rõ mục tiêu: {goal_text}",
            estimated_minutes=30,
            weekday=0,
            priority="HIGH",
            suggestion_reason="Hiểu rõ mục tiêu trước khi bắt tay làm.",
        ),
        GeneratedTask(
            key="outline",
            title="Phác thảo hướng thực hiện",
            estimated_minutes=45,
            weekday=1,
            priority="HIGH",
            suggestion_reason="Có khung trước giúp phần thực thi không bị lạc hướng.",
        ),
        GeneratedTask(
            key="build",
            title="Thực hiện phần nội dung chính",
            estimated_minutes=120,
            weekday=3,
            priority="MEDIUM",
            suggestion_reason="Phần chiếm nhiều thời gian nhất, cần block liền mạch.",
        ),
        GeneratedTask(
            key="review",
            title="Rà soát lại so với mục tiêu",
            estimated_minutes=45,
            weekday=5,
            priority="MEDIUM",
            suggestion_reason="Tự kiểm tra trước khi coi là xong.",
        ),
        GeneratedTask(
            key="wrap_up",
            title="Hoàn thiện và chốt tuần",
            estimated_minutes=20,
            weekday=6,
            priority="HIGH",
            suggestion_reason="Chừa ngày cuối làm buffer.",
        ),
    ]


def _llm_generated_tasks(
    db: Session, *, subject_code: str, goal_text: str
) -> tuple[list[GeneratedTask] | None, dict]:
    """Mirrors plan_builder._llm_generated_tasks's trace contract, grounded in
    the student's own goal text instead of an Assignment row."""
    if not has_configured_llm():
        return None, {"retrieval_empty": False, "llm_success": False}

    retrieved = RetrievalService(ChunkRepository(db)).retrieve(
        subject_code=subject_code, question=goal_text
    )
    if not retrieved:
        return None, {"retrieval_empty": True, "llm_success": False}

    try:
        system_prompt = (
            "Bạn là trợ lý lập kế hoạch học tập. Từ mục tiêu tuần của sinh viên và "
            "các đoạn tài liệu môn học được cung cấp, hãy chia thành 3-7 công việc "
            "cụ thể, mỗi việc 15-300 phút. Chỉ trích dẫn source_chunk_ids nếu công "
            "việc thực sự dựa trên nội dung đoạn đó — không bịa nguồn."
        )
        context_blocks = [
            f"[{item.chunk.chunk_id}] {item.chunk.source_label}\n{item.chunk.text}"
            for item in retrieved
        ]
        user_prompt = (
            f"Mục tiêu tuần: {goal_text}\n\n"
            "Đoạn tài liệu môn học:\n" + "\n\n".join(context_blocks)
        )
        llm = get_llm().with_structured_output(LlmPlanPayload)
        payload = llm.invoke(
            [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ]
        )
        if not isinstance(payload, LlmPlanPayload):
            payload = LlmPlanPayload.model_validate(payload)

        if payload.insufficient_context or not payload.tasks:
            return None, {"retrieval_empty": False, "llm_success": False}

        allowed_ids = {item.chunk.chunk_id for item in retrieved}
        tasks = [
            GeneratedTask(
                key=task.key,
                title=task.title,
                estimated_minutes=task.estimated_minutes,
                weekday=task.weekday,
                priority=task.priority,
                source_refs=tuple(cid for cid in task.source_chunk_ids if cid in allowed_ids),
                suggestion_reason=task.suggestion_reason,
            )
            for task in payload.tasks
        ]
        if not tasks:
            return None, {"retrieval_empty": False, "llm_success": False}
        return tasks, {"retrieval_empty": False, "llm_success": True}
    except Exception:
        logger.exception("llm_weekly_goal_plan_failed subject_code=%s", subject_code)
        return None, {"retrieval_empty": False, "llm_success": False}


def _capacity_minutes(availability: list[dict] | None, available_hours: float) -> int:
    if availability:
        total = 0
        for slot in availability:
            try:
                total += int(slot.get("availableMinutes") or slot.get("minutes") or 0)
            except (TypeError, ValueError):
                continue
        if total > 0:
            return total
    return int(round(max(0.0, float(available_hours or 0)) * 60))


def academic_week_number(db: Session, student_id: str, week_start: date) -> int:
    """Week number relative to the student's active semester when one exists,
    else the plain ISO week — a46db63 always had a semester; this codebase's
    multi-tenant students may not yet have one at generation time."""
    monday = monday_of(week_start)
    semester = (
        db.query(models.SemesterSetup)
        .filter_by(student_id=student_id, is_active=True)
        .first()
    )
    if semester is not None:
        return max(1, ((monday - semester.start_date).days // 7) + 1)
    return monday.isocalendar().week


def discard_drafts_for_week(db: Session, student_id: str, week_start: date) -> None:
    """Hard-delete every DRAFT weekly_goal plan tree for (student, week) before
    generating a new one — a46db63 invariant: only one DRAFT plan per
    (student, week) survives. Scoped to `kind == PLAN_KIND` only, so it never
    touches lecture-plan-sourced or timetable-container plans."""
    plans = (
        db.query(models.WeeklyPlan)
        .filter_by(student_id=student_id, week_number=monday_of(week_start).isocalendar().week)
        .all()
    )
    targets = [
        plan
        for plan in plans
        if isinstance(plan.goals, dict)
        and plan.goals.get("kind") == PLAN_KIND
        and str(plan.goals.get("status") or "DRAFT").upper() == "DRAFT"
    ]
    _delete_plan_trees(db, targets)


def _delete_plan_trees(db: Session, plans: list[models.WeeklyPlan]) -> None:
    plan_ids = [plan.id for plan in plans]
    if not plan_ids:
        return
    daily_ids = [
        row.id
        for row in db.query(models.DailyPlan.id)
        .filter(models.DailyPlan.weekly_plan_id.in_(plan_ids))
        .all()
    ]
    block_ids = (
        [
            row.id
            for row in db.query(models.ScheduleBlock.id)
            .filter(models.ScheduleBlock.daily_plan_id.in_(daily_ids))
            .all()
        ]
        if daily_ids
        else []
    )
    task_ids = (
        [
            row.id
            for row in db.query(models.StudyTask.id)
            .filter(models.StudyTask.schedule_block_id.in_(block_ids))
            .all()
        ]
        if block_ids
        else []
    )
    if task_ids:
        db.query(models.ProgressEvent).filter(
            models.ProgressEvent.task_id.in_(task_ids)
        ).delete(synchronize_session=False)
        db.query(models.StudyTask).filter(
            models.StudyTask.id.in_(task_ids)
        ).delete(synchronize_session=False)
    if block_ids:
        db.query(models.ScheduleBlock).filter(
            models.ScheduleBlock.id.in_(block_ids)
        ).delete(synchronize_session=False)
    if daily_ids:
        db.query(models.DailyPlan).filter(
            models.DailyPlan.id.in_(daily_ids)
        ).delete(synchronize_session=False)
    db.query(models.WeeklyPlan).filter(
        models.WeeklyPlan.id.in_(plan_ids)
    ).delete(synchronize_session=False)


def _persist_tasks(
    db: Session,
    *,
    plan: models.WeeklyPlan,
    tasks: list[GeneratedTask],
    monday: date,
    sessions: list[str],
) -> dict[str, dict]:
    task_meta: dict[str, dict] = {}
    for index, generated in enumerate(tasks):
        scheduled_day = monday + timedelta(days=min(6, max(0, generated.weekday)))
        hour, minute = SESSION_CLOCK.get(
            sessions[index % len(sessions)], SESSION_CLOCK["EVENING"]
        )
        start = datetime.combine(scheduled_day, time(hour, minute))
        end = start + timedelta(minutes=generated.estimated_minutes)

        daily_id = f"dp_{uuid.uuid4().hex[:8]}"
        block_id = f"sb_{uuid.uuid4().hex[:8]}"
        task_id = f"task_{uuid.uuid4().hex[:8]}"

        db.add(
            models.DailyPlan(
                id=daily_id,
                weekly_plan_id=plan.id,
                date=datetime.combine(scheduled_day, time.min),
                status="TODO",
            )
        )
        db.add(
            models.ScheduleBlock(
                id=block_id,
                daily_plan_id=daily_id,
                start_time=start,
                end_time=end,
                activity_description=f"Khung giờ: {sessions[index % len(sessions)].lower()}",
            )
        )
        db.add(
            models.StudyTask(
                id=task_id,
                schedule_block_id=block_id,
                assignment_id=None,
                title=generated.title,
                planned_minutes=generated.estimated_minutes,
                actual_minutes=None,
                priority=generated.priority,
                status="TODO",
                difficulty="MEDIUM",
                rescheduled_count=0,
            )
        )
        task_meta[task_id] = {
            "key": generated.key,
            "scheduled_date": scheduled_day.isoformat(),
            "source_refs": list(generated.source_refs),
            "source_fact": generated.source_fact,
            "suggestion_reason": generated.suggestion_reason,
            "provenance": prov.ai_suggested(PLANNER_VERSION),
            "estimate_provenance": prov.ai_suggested(PLANNER_VERSION),
            "defer_count": 0,
            "defer_reason": None,
        }
    return task_meta


def generate(
    db: Session,
    *,
    student_id: str,
    goal_text: str,
    subject_code: str,
    available_hours: float,
    preferred_sessions: list[str] | None = None,
    availability: list[dict] | None = None,
    week_start: date | None = None,
) -> models.WeeklyPlan:
    monday = monday_of(week_start or date.today())
    sessions = [
        str(item).strip().upper()
        for item in (preferred_sessions or ["EVENING"])
        if str(item).strip()
    ] or ["EVENING"]

    discard_drafts_for_week(db, student_id, monday)

    llm_tasks, trace = _llm_generated_tasks(db, subject_code=subject_code, goal_text=goal_text)
    tasks = llm_tasks or _generic_templates(goal_text)

    capacity_minutes = _capacity_minutes(availability, available_hours)
    plan_id = f"plan_{uuid.uuid4().hex[:8]}"
    planned_minutes = sum(task.estimated_minutes for task in tasks)

    plan = models.WeeklyPlan(
        id=plan_id,
        student_id=student_id,
        week_number=academic_week_number(db, student_id, monday),
        goals={
            "kind": PLAN_KIND,
            "statement": goal_text,
            "subject_code": subject_code,
            "status": "DRAFT",
            "week_start": monday.isoformat(),
            "capacity_minutes": capacity_minutes,
            "planned_minutes": planned_minutes,
            "preferred_sessions": sessions,
            "availability": availability or [],
            "availability_provenance": prov.user_entered("availability_form"),
            "planner_version": PLANNER_VERSION,
            "provenance": prov.ai_suggested(PLANNER_VERSION),
            "task_meta": {},
            "llm_attempted": has_configured_llm(),
            "llm_success": trace["llm_success"],
            "fallback_used": llm_tasks is None,
            "retrieval_empty": trace["retrieval_empty"],
        },
        study_hours_allocated=round(capacity_minutes / 60.0, 2),
    )
    db.add(plan)
    db.flush()

    task_meta = _persist_tasks(db, plan=plan, tasks=tasks, monday=monday, sessions=sessions)
    goals = dict(plan.goals)
    goals["task_meta"] = task_meta
    plan.goals = goals
    db.flush()
    return plan


def regenerate_from_reflection(
    db: Session,
    *,
    student_id: str,
    reflection: models.WeeklyReflection,
) -> models.WeeklyPlan:
    """Next week's draft from a confirmed reflection — a46db63 §6.3.6.

    If the reflection's `next_week_outcomes` answer has non-empty items
    (legacy reflections only — that question was retired, see
    `reflection_engine.py`), each outcome is planned fresh (RAG-grounded,
    same as `generate`). Otherwise every task from the previous plan carries
    forward unchanged. An LLM then reads the reflection's stats + 5
    self-feedback answers (`reflection_suggestion.build_next_week_suggestion`)
    and may nudge every task's estimate by a bounded +/-30% multiplier —
    best-effort, a no-op when no LLM is configured or the call fails.
    """
    metrics = reflection.metrics if isinstance(reflection.metrics, dict) else {}
    source_plan = (
        db.query(models.WeeklyPlan).filter_by(id=metrics.get("planId")).first()
        if metrics.get("planId")
        else None
    )
    if source_plan is None or not isinstance(source_plan.goals, dict):
        raise LookupError("Source plan not found for this reflection")

    source_goals = source_plan.goals
    subject_code = source_goals.get("subject_code")
    answers = {a.get("questionId"): a for a in (metrics.get("answers") or [])}

    outcomes_answer = answers.get("next_week_outcomes") or {}
    outcomes = [item.strip() for item in (outcomes_answer.get("items") or []) if item.strip()]

    previous_week_start = source_goals.get("week_start")
    base_monday = (
        date.fromisoformat(previous_week_start)
        if previous_week_start
        else monday_of(date.today())
    )
    next_monday = base_monday + timedelta(days=7)
    sessions = source_goals.get("preferred_sessions") or ["EVENING"]

    if outcomes:
        tasks: list[GeneratedTask] = []
        for index, outcome in enumerate(outcomes):
            llm_tasks, _trace = _llm_generated_tasks(
                db, subject_code=subject_code or "", goal_text=outcome
            )
            generated = llm_tasks or _generic_templates(outcome)
            for task in generated:
                task.key = f"{task.key}_{index}"
            tasks.extend(generated)
    else:
        task_meta = source_goals.get("task_meta") or {}
        prior_rows = (
            db.query(models.StudyTask)
            .join(models.ScheduleBlock, models.ScheduleBlock.id == models.StudyTask.schedule_block_id)
            .join(models.DailyPlan, models.DailyPlan.id == models.ScheduleBlock.daily_plan_id)
            .filter(models.DailyPlan.weekly_plan_id == source_plan.id)
            .order_by(models.ScheduleBlock.start_time)
            .all()
        )
        if not prior_rows:
            raise ValueError("Previous plan has no tasks to carry forward")
        tasks = [
            GeneratedTask(
                key=task_meta.get(task.id, {}).get("key") or task.id,
                title=task.title,
                estimated_minutes=task.planned_minutes,
                weekday=block.start_time.weekday(),
                priority=task.priority,
                source_refs=tuple(task_meta.get(task.id, {}).get("source_refs") or ()),
                source_fact=task_meta.get(task.id, {}).get("source_fact"),
                suggestion_reason=task_meta.get(task.id, {}).get("suggestion_reason") or "",
            )
            for task, block, _daily in prior_rows
        ]

    changes: list[dict] = []
    reflection_insight: str | None = None
    if metrics.get("studentConfirmed"):
        suggestion, _trace = build_next_week_suggestion(
            facts=metrics.get("facts") or {},
            answers=metrics.get("answers") or [],
        )
        if suggestion is not None:
            multiplier = suggestion.estimated_minutes_multiplier
            if multiplier != 1.0:
                for task in tasks:
                    adjusted = int(task.estimated_minutes * multiplier)
                    task.estimated_minutes = max(15, (adjusted // 15) * 15)
                changes.append(
                    {
                        "adjustment": "reflection_insight",
                        "field": "estimatedMinutes",
                        "before": "Ước tính chưa điều chỉnh",
                        "after": (
                            "Tăng nhẹ thời lượng" if multiplier > 1.0 else "Giảm nhẹ thời lượng"
                        ),
                        "reason": suggestion.summary,
                    }
                )
            reflection_insight = suggestion.summary

    discard_drafts_for_week(db, student_id, next_monday)

    capacity_minutes = _capacity_minutes(None, source_plan.study_hours_allocated or 8.0)
    plan_id = f"plan_{uuid.uuid4().hex[:8]}"
    plan = models.WeeklyPlan(
        id=plan_id,
        student_id=student_id,
        week_number=academic_week_number(db, student_id, next_monday),
        goals={
            "kind": PLAN_KIND,
            "statement": source_goals.get("statement"),
            "subject_code": subject_code,
            "status": "DRAFT",
            "week_start": next_monday.isoformat(),
            "capacity_minutes": capacity_minutes,
            "planned_minutes": sum(t.estimated_minutes for t in tasks),
            "preferred_sessions": sessions,
            "availability": [],
            "planner_version": PLANNER_VERSION,
            "provenance": prov.ai_suggested(PLANNER_VERSION),
            "task_meta": {},
            "created_from_reflection_id": reflection.id,
            "reflection_changes": changes,
            "reflection_insight": reflection_insight,
        },
        study_hours_allocated=round(capacity_minutes / 60.0, 2),
    )
    db.add(plan)
    db.flush()
    task_meta = _persist_tasks(db, plan=plan, tasks=tasks, monday=next_monday, sessions=sessions)
    goals = dict(plan.goals)
    goals["task_meta"] = task_meta
    plan.goals = goals
    db.flush()
    return plan


def is_plan_acceptable_this_week(plan: models.WeeklyPlan, today: date) -> bool:
    """a46db63 §6.3.5 — current week, next week, or the semester's suggested
    week-start (snapped to Monday)."""
    goals = plan.goals if isinstance(plan.goals, dict) else {}
    current_monday = monday_of(today)
    week_start = goals.get("week_start")
    if not week_start:
        return plan.week_number == current_monday.isocalendar().week
    try:
        planned_monday = monday_of(date.fromisoformat(str(week_start)))
    except ValueError:
        return False
    return planned_monday in (current_monday, current_monday + timedelta(days=7))
