"""Weekly-plan generation grounded in real course content (Blueprint §2.1).

Two entry points:

``generate``            build a draft week for an assignment.
``generate_from_reflection``  build next week's draft, applying only the
                        adjustments the student explicitly confirmed.

Design rules taken straight from the docs:

* AI proposes, the student confirms — nothing here ever flips a plan to
  ``APPROVED`` on its own.
* Every task carries provenance. Durations are ``ai_suggested`` and must be
  rendered as "Ước tính của Curi"; anything shown as "theo syllabus" must come
  from ``source_refs`` pointing at a real ingested chunk.
* Per-task metadata lives in ``WeeklyPlan.goals['task_meta']`` (a JSON column
  that already exists) rather than in new columns — Gate 2 must not require a
  DB migration.
"""

from __future__ import annotations

import logging
import uuid
from dataclasses import dataclass
from datetime import date, datetime, time, timedelta
from pathlib import Path

from sqlalchemy.orm import Session

from src.db import models
from src.repositories.chunk_repository import ChunkRepository
from src.schemas.plan import LlmPlanPayload
from src.services.academic.timetable_service import monday_of
from src.services.ai.reflection_suggestion import build_next_week_suggestion
from src.services.core import provenance as prov
from src.services.core.llm import get_llm, has_configured_llm
from src.services.mock import gate2_demo
from src.services.rag.retrieval_service import RetrievalService

logger = logging.getLogger(__name__)

PLANNER_VERSION = "curi_planner_v1"
PLAN_PROMPT_PATH = Path(__file__).resolve().parents[2] / "prompts" / "plan_v1.md"

SESSION_CLOCK: dict[str, tuple[int, int]] = {
    "MORNING": (8, 0),
    "AFTERNOON": (14, 0),
    "EVENING": (19, 30),
}

# Adjustment vocabulary the Reflect step can emit and the planner understands.
# Anything not in here is stored on the reflection but ignored by the planner
# (so a free-text priority note can never silently mutate a schedule).
SUPPORTED_ADJUSTMENTS: dict[str, str] = {
    "split_diagram_tasks": "Chia task sơ đồ use-case thành các bước nhỏ",
    "increase_diagram_estimate": "Tăng thời lượng ước tính cho phần sơ đồ",
    "keep_buffer_day": "Giữ Chủ nhật làm ngày dự phòng",
    "keep_time_slots": "Giữ nguyên khung giờ đã hiệu quả",
    "repeat_task_split": "Lặp lại cách chia nhỏ task của tuần trước",
    "increase_estimates": "Tăng thời lượng ước tính chung 20%",
    "reduce_load": "Giảm tải: bỏ bớt task ưu tiên thấp",
    "single_priority": "Chỉ tập trung một mục tiêu duy nhất",
    "request_help": "Ghi nhận cần hỗ trợ từ giảng viên",
}

# Sub-steps used when `split_diagram_tasks` is confirmed (Blueprint §7 /
# demo script: 1 task 120' becomes 4 subtasks totalling 225').
DIAGRAM_SUBTASKS: tuple[tuple[str, int], ...] = (
    ("Liệt kê actor và mục tiêu hệ thống", 45),
    ("Vẽ nháp use-case chính", 60),
    ("Bổ sung quan hệ include/extend", 60),
    ("Rà soát sơ đồ với nhóm và chỉnh sửa", 60),
)


@dataclass
class GeneratedTask:
    key: str
    title: str
    estimated_minutes: int
    weekday: int
    priority: str
    deliverable: str | None
    source_refs: tuple[str, ...]
    source_fact: str | None
    suggestion_reason: str
    derived_from: str | None = None


def _templates_for_assignment(assignment: models.Assignment) -> list[GeneratedTask]:
    """Task skeleton for an assignment.

    The Gate-2 assignment has a hand-authored decomposition grounded in the
    syllabus sessions. Any other assignment falls back to a generic but still
    honestly-labelled decomposition (no fake citations).
    """
    if assignment.id == gate2_demo.PART1_ASSIGNMENT_ID:
        return [
            GeneratedTask(
                key=item.key,
                title=item.title,
                estimated_minutes=item.estimated_minutes,
                weekday=item.weekday,
                priority=item.priority,
                deliverable=item.deliverable,
                source_refs=item.source_refs,
                source_fact=item.source_fact,
                suggestion_reason=item.suggestion_reason,
            )
            for item in gate2_demo.PART1_TASK_TEMPLATES
        ]

    return [
        GeneratedTask(
            key="understand",
            title=f"Đọc đề và tiêu chí chấm: {assignment.title}",
            estimated_minutes=30,
            weekday=0,
            priority="HIGH",
            deliverable=None,
            source_refs=(),
            source_fact=None,
            suggestion_reason="Hiểu tiêu chí chấm trước khi bắt tay làm.",
        ),
        GeneratedTask(
            key="outline",
            title="Phác thảo hướng giải quyết",
            estimated_minutes=60,
            weekday=1,
            priority="HIGH",
            deliverable=None,
            source_refs=(),
            source_fact=None,
            suggestion_reason="Có khung trước giúp phần thực thi không bị lạc hướng.",
        ),
        GeneratedTask(
            key="build",
            title="Thực hiện phần nội dung chính",
            estimated_minutes=120,
            weekday=3,
            priority="MEDIUM",
            deliverable=None,
            source_refs=(),
            source_fact=None,
            suggestion_reason="Phần chiếm nhiều thời gian nhất, cần block liền mạch.",
        ),
        GeneratedTask(
            key="review",
            title="Rà soát theo tiêu chí chấm",
            estimated_minutes=45,
            weekday=5,
            priority="MEDIUM",
            deliverable=None,
            source_refs=(),
            source_fact=None,
            suggestion_reason="Tự chấm trước khi nộp để không mất điểm hình thức.",
        ),
        GeneratedTask(
            key="submit",
            title="Hoàn thiện và nộp bài",
            estimated_minutes=20,
            weekday=6,
            priority="HIGH",
            deliverable=None,
            source_refs=(),
            source_fact=None,
            suggestion_reason="Chừa ngày cuối làm buffer.",
        ),
    ]


def _subject_code_for_assignment(db: Session, assignment: models.Assignment) -> str | None:
    section = (
        db.query(models.CourseSection)
        .filter(models.CourseSection.id == assignment.section_id)
        .first()
    )
    if section is None:
        return None
    course = db.query(models.Course).filter(models.Course.id == section.course_id).first()
    return course.code if course else None


def _llm_generated_tasks(
    db: Session, assignment: models.Assignment
) -> tuple[list[GeneratedTask] | None, dict]:
    """Real LLM decomposition for non-demo assignments, grounded in retrieved
    syllabus chunks. Returns (None, trace) (caller falls back to the generic
    template) when no API key is configured, retrieval finds nothing, or the
    LLM call fails/says the context is insufficient — never raises.

    `trace` (P0#8, mục 9 ý8 — Option B, PENDING_DECISIONS.md #1) distinguishes
    *why* a fallback happened, so a demo re-run doesn't quietly muddle "quota
    exhausted"/"model said no"/"nothing to retrieve" into one unlabeled
    fallback:
      - `retrieval_empty`: True only if `RetrievalService.retrieve()` itself
        returned nothing — i.e. there was no source material to ground an
        LLM call in at all, so the LLM was never even invoked.
      - `llm_success`: True only if the LLM was actually called AND returned
        usable, sufficient-context tasks. False for every other reason
        (no key configured, no subject code, empty retrieval, insufficient
        context, empty task list, or an exception) — the caller combines
        this with `retrieval_empty` to tell "the LLM failed/declined" apart
        from "there was nothing to give it".

    The Gate-2 demo assignment never reaches this path (see `generate()`) —
    its task list stays the hand-authored, fully deterministic template so the
    rehearsed demo cannot be destabilized by an LLM response.
    """
    if not has_configured_llm():
        return None, {"retrieval_empty": False, "llm_success": False}

    subject_code = _subject_code_for_assignment(db, assignment)
    if not subject_code:
        return None, {"retrieval_empty": False, "llm_success": False}

    query = f"{assignment.title}\n{assignment.description or ''}".strip()
    retrieved = RetrievalService(ChunkRepository(db)).retrieve(
        subject_code=subject_code, question=query
    )
    if not retrieved:
        return None, {"retrieval_empty": True, "llm_success": False}

    try:
        system_prompt = PLAN_PROMPT_PATH.read_text(encoding="utf-8")
        context_blocks = [
            f"[{item.chunk.chunk_id}] {item.chunk.source_label}\n{item.chunk.text}"
            for item in retrieved
        ]
        user_prompt = (
            f"Assignment: {assignment.title}\n"
            f"Description: {assignment.description or '(no description)'}\n"
            f"Due date: {assignment.due_date.isoformat()}\n\n"
            "Syllabus context chunks:\n" + "\n\n".join(context_blocks)
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
                deliverable=task.deliverable,
                source_refs=tuple(cid for cid in task.source_chunk_ids if cid in allowed_ids),
                source_fact=None,
                suggestion_reason=task.suggestion_reason,
            )
            for task in payload.tasks
        ]
        if not tasks:
            return None, {"retrieval_empty": False, "llm_success": False}
        return tasks, {"retrieval_empty": False, "llm_success": True}
    except Exception:
        logger.exception("llm_plan_generation_failed assignment_id=%s", assignment.id)
        return None, {"retrieval_empty": False, "llm_success": False}


def apply_adjustments(
    tasks: list[GeneratedTask], adjustments: list[str]
) -> tuple[list[GeneratedTask], list[dict]]:
    """Apply confirmed reflection adjustments. Returns (tasks, change log).

    The change log is what the UI renders as the before/after proof that the
    reflection actually moved the plan.
    """
    confirmed = [item for item in adjustments if item in SUPPORTED_ADJUSTMENTS]
    changes: list[dict] = []
    result = list(tasks)

    if "increase_diagram_estimate" in confirmed:
        for task in result:
            if task.key in {"use_case"} or "sơ đồ" in task.title.lower():
                before = task.estimated_minutes
                task.estimated_minutes = int(round(before * 1.5))
                changes.append(
                    {
                        "adjustment": "increase_diagram_estimate",
                        "taskKey": task.key,
                        "field": "estimatedMinutes",
                        "before": before,
                        "after": task.estimated_minutes,
                        "reason": "Tuần trước sơ đồ vượt ước tính nên tăng thời lượng.",
                    }
                )

    if "split_diagram_tasks" in confirmed:
        expanded: list[GeneratedTask] = []
        for task in result:
            if task.key == "use_case" or "sơ đồ" in task.title.lower():
                for index, (title, minutes) in enumerate(DIAGRAM_SUBTASKS, start=1):
                    expanded.append(
                        GeneratedTask(
                            key=f"{task.key}_{index}",
                            title=f"{title}",
                            estimated_minutes=minutes,
                            weekday=min(6, task.weekday - 2 + index),
                            priority=task.priority,
                            deliverable=task.deliverable,
                            source_refs=task.source_refs,
                            source_fact=task.source_fact,
                            suggestion_reason=(
                                "Bước nhỏ tách ra từ task sơ đồ theo điều chỉnh "
                                "bạn xác nhận ở phản tư tuần trước."
                            ),
                            derived_from=task.key,
                        )
                    )
                changes.append(
                    {
                        "adjustment": "split_diagram_tasks",
                        "taskKey": task.key,
                        "field": "tasks",
                        "before": f"1 task · {task.estimated_minutes} phút",
                        "after": (
                            f"{len(DIAGRAM_SUBTASKS)} task nhỏ · "
                            f"{sum(item[1] for item in DIAGRAM_SUBTASKS)} phút"
                        ),
                        "reason": "Bạn chọn chia nhỏ phần sơ đồ ở bước phản tư.",
                    }
                )
            else:
                expanded.append(task)
        result = expanded

    if "increase_estimates" in confirmed:
        for task in result:
            before = task.estimated_minutes
            task.estimated_minutes = int(round(before * 1.2))
            changes.append(
                {
                    "adjustment": "increase_estimates",
                    "taskKey": task.key,
                    "field": "estimatedMinutes",
                    "before": before,
                    "after": task.estimated_minutes,
                    "reason": "Bạn chọn tăng thời lượng ước tính chung 20%.",
                }
            )

    if "reduce_load" in confirmed or "single_priority" in confirmed:
        keep = [task for task in result if task.priority == "HIGH"]
        dropped = [task for task in result if task.priority != "HIGH"]
        if keep and dropped:
            changes.append(
                {
                    "adjustment": (
                        "single_priority" if "single_priority" in confirmed else "reduce_load"
                    ),
                    "taskKey": None,
                    "field": "tasks",
                    "before": f"{len(result)} task",
                    "after": f"{len(keep)} task ưu tiên cao",
                    "reason": "Bạn chọn giảm tải cho tuần sau.",
                }
            )
            result = keep

    if "keep_buffer_day" in confirmed:
        moved = 0
        for task in result:
            if task.weekday == 6 and task.key != "submit":
                task.weekday = 5
                moved += 1
        changes.append(
            {
                "adjustment": "keep_buffer_day",
                "taskKey": None,
                "field": "scheduledDate",
                "before": "Chủ nhật có task thường",
                "after": "Chủ nhật chỉ còn buffer + nộp bài",
                "reason": "Bạn xác nhận giữ Chủ nhật làm ngày dự phòng.",
            }
        )
        if moved == 0:
            changes[-1]["before"] = "Chủ nhật đã trống"
            changes[-1]["after"] = "Giữ nguyên Chủ nhật làm buffer"

    return result, changes


class PlanBuilder:
    def __init__(self, db: Session) -> None:
        self._db = db

    # ── generation ───────────────────────────────────────────────────
    def generate(
        self,
        *,
        student_id: str,
        assignment: models.Assignment,
        available_hours: float,
        preferred_sessions: list[str] | None = None,
        availability: list[dict] | None = None,
        week_start: date | None = None,
        adjustments: list[str] | None = None,
        source_reflection_id: str | None = None,
        goal: str | None = None,
    ) -> models.WeeklyPlan:
        monday = monday_of(week_start or date.today())
        sessions = [
            str(item).strip().upper()
            for item in (preferred_sessions or ["EVENING"])
            if str(item).strip()
        ] or ["EVENING"]

        if assignment.id == gate2_demo.PART1_ASSIGNMENT_ID:
            # Demo-critical path: always the hand-authored deterministic
            # template, never the LLM — see _llm_generated_tasks docstring.
            tasks = _templates_for_assignment(assignment)
            trace = {
                "llm_attempted": False,
                "llm_success": False,
                "fallback_used": False,
                "retrieval_empty": False,
            }
        else:
            llm_tasks, llm_trace = _llm_generated_tasks(self._db, assignment)
            tasks = llm_tasks or _templates_for_assignment(assignment)
            trace = {
                "llm_attempted": True,
                "llm_success": llm_trace["llm_success"],
                "fallback_used": llm_tasks is None,
                "retrieval_empty": llm_trace["retrieval_empty"],
            }
        tasks, changes = apply_adjustments(tasks, adjustments or [])

        reflection_insight: str | None = None
        if source_reflection_id:
            tasks, changes, reflection_insight = self._apply_reflection_insight(
                tasks, changes, source_reflection_id
            )

        capacity_minutes = self._capacity_minutes(availability, available_hours)
        plan_id = f"plan_{uuid.uuid4().hex[:8]}"
        planned_minutes = sum(task.estimated_minutes for task in tasks)

        plan = models.WeeklyPlan(
            id=plan_id,
            student_id=student_id,
            week_number=monday.isocalendar().week,
            goals={
                "statement": goal or f"Hoàn thành {assignment.title}",
                "status": "DRAFT",
                "week_start": monday.isoformat(),
                "assignment_id": assignment.id,
                "capacity_minutes": capacity_minutes,
                "planned_minutes": planned_minutes,
                "preferred_sessions": sessions,
                "availability": availability or [],
                "availability_provenance": prov.user_entered("availability_form"),
                "planner_version": PLANNER_VERSION,
                "fixture_version": gate2_demo.FIXTURE_VERSION,
                "created_from_reflection_id": source_reflection_id,
                "adjustments_applied": [
                    item for item in (adjustments or []) if item in SUPPORTED_ADJUSTMENTS
                ],
                "reflection_changes": changes,
                "reflection_insight": reflection_insight,
                "provenance": prov.ai_suggested(PLANNER_VERSION),
                "task_meta": {},
                # P0#8 trace (mục 9 ý8, Option B, PENDING_DECISIONS.md #1) —
                # see _llm_generated_tasks docstring for exact field meaning.
                "llm_attempted": trace["llm_attempted"],
                "llm_success": trace["llm_success"],
                "fallback_used": trace["fallback_used"],
                "retrieval_empty": trace["retrieval_empty"],
            },
            study_hours_allocated=round(capacity_minutes / 60.0, 2),
        )
        self._db.add(plan)
        self._db.flush()

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

            self._db.add(
                models.DailyPlan(
                    id=daily_id,
                    weekly_plan_id=plan_id,
                    date=datetime.combine(scheduled_day, time.min),
                    status="TODO",
                )
            )
            self._db.add(
                models.ScheduleBlock(
                    id=block_id,
                    daily_plan_id=daily_id,
                    start_time=start,
                    end_time=end,
                    activity_description=(
                        f"Khung giờ: {sessions[index % len(sessions)].lower()}"
                    ),
                )
            )
            self._db.add(
                models.StudyTask(
                    id=task_id,
                    schedule_block_id=block_id,
                    assignment_id=assignment.id,
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
                "deliverable": generated.deliverable,
                "source_refs": list(generated.source_refs),
                "source_fact": generated.source_fact,
                "suggestion_reason": generated.suggestion_reason,
                "derived_from": generated.derived_from,
                "provenance": prov.ai_suggested(PLANNER_VERSION),
                "estimate_provenance": prov.ai_suggested(PLANNER_VERSION),
                "defer_count": 0,
                "defer_reason": None,
            }

        goals = dict(plan.goals)
        goals["task_meta"] = task_meta
        plan.goals = goals
        self._db.flush()
        return plan

    def _capacity_minutes(
        self, availability: list[dict] | None, available_hours: float
    ) -> int:
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


# ── serialization: the single canonical plan shape ───────────────────────
def serialize_plan(db: Session, plan: models.WeeklyPlan) -> dict:
    goals = plan.goals if isinstance(plan.goals, dict) else {}
    task_meta: dict = goals.get("task_meta") or {}

    rows = (
        db.query(models.StudyTask, models.ScheduleBlock, models.DailyPlan)
        .join(
            models.ScheduleBlock,
            models.ScheduleBlock.id == models.StudyTask.schedule_block_id,
        )
        .join(
            models.DailyPlan,
            models.DailyPlan.id == models.ScheduleBlock.daily_plan_id,
        )
        .filter(models.DailyPlan.weekly_plan_id == plan.id)
        .order_by(models.ScheduleBlock.start_time)
        .all()
    )

    chunk_ids: set[str] = set()
    for meta in task_meta.values():
        chunk_ids.update(meta.get("source_refs") or [])
    sources = _sources_by_id(db, chunk_ids)

    tasks: list[dict] = []
    for task, block, daily in rows:
        meta = task_meta.get(task.id, {})
        refs = [sources[ref] for ref in (meta.get("source_refs") or []) if ref in sources]
        tasks.append(
            {
                "id": task.id,
                "key": meta.get("key"),
                "title": task.title,
                "description": task.title,
                "assignmentId": task.assignment_id,
                "deliverable": meta.get("deliverable"),
                "scheduledDate": meta.get("scheduled_date")
                or daily.date.date().isoformat(),
                "scheduledBlock": block.activity_description,
                "startTime": block.start_time.isoformat(),
                "estimatedMinutes": task.planned_minutes,
                "actualMinutes": task.actual_minutes,
                "priority": task.priority,
                "status": task.status,
                "deferCount": meta.get("defer_count") or task.rescheduled_count or 0,
                "deferReason": meta.get("defer_reason"),
                "deferReasonLabel": meta.get("defer_reason_label"),
                "derivedFrom": meta.get("derived_from"),
                "sourceFact": meta.get("source_fact"),
                "sourceRefs": refs,
                "suggestionReason": meta.get("suggestion_reason"),
                "rationale": meta.get("suggestion_reason") or "Cần thiết cho tiến độ.",
                "provenance": meta.get("provenance") or prov.ai_suggested(PLANNER_VERSION),
                "estimateProvenance": meta.get("estimate_provenance")
                or prov.ai_suggested(PLANNER_VERSION),
            }
        )

    planned = sum(item["estimatedMinutes"] for item in tasks)
    capacity = int(goals.get("capacity_minutes") or round((plan.study_hours_allocated or 0) * 60))
    completed = sum(1 for item in tasks if item["status"] == "COMPLETED")

    assignment = None
    assignment_id = goals.get("assignment_id") or (
        tasks[0]["assignmentId"] if tasks else None
    )
    if assignment_id:
        assignment = db.query(models.Assignment).filter_by(id=assignment_id).first()

    warnings: list[str] = []
    if capacity and planned > capacity:
        warnings.append(
            f"Tổng thời lượng dự kiến ({planned} phút) vượt quỹ thời gian rảnh "
            f"({capacity} phút). Hãy bớt hoặc dời một task trước khi xác nhận."
        )

    deadline_payload = None
    deadline_days = None
    if assignment is not None:
        due = assignment.due_date
        delta = due - datetime.now()
        deadline_days = max(0, delta.days)
        deadline_payload = {
            "assignmentId": assignment.id,
            "title": assignment.title,
            "dueAt": due.isoformat(),
            "hoursLeft": round(delta.total_seconds() / 3600.0, 1),
            "deliverables": gate2_demo.deliverables_payload()
            if assignment.id == gate2_demo.PART1_ASSIGNMENT_ID
            else [],
            "provenance": prov.simulated(assignment.id),
        }

    return {
        "id": plan.id,
        "studentId": plan.student_id,
        "assignmentId": assignment_id or "",
        "subjectCode": goals.get("subject_code"),
        "goalText": goals.get("statement"),
        "weekNumber": plan.week_number,
        "weekStart": goals.get("week_start"),
        "goal": goals.get("statement"),
        "status": _plan_status(plan),
        "tasks": tasks,
        "assignment": deadline_payload,
        "capacityMinutes": capacity,
        "availableMinutes": capacity,
        "plannedMinutes": planned,
        "totalEstimatedMinutes": planned,
        "overCapacity": bool(capacity and planned > capacity),
        "completedTasks": completed,
        "totalTasks": len(tasks),
        "completionRate": round(completed / len(tasks), 3) if tasks else 0.0,
        "deadlineDistanceDays": deadline_days if deadline_days is not None else 5,
        "assumptions": [
            "Thời lượng từng task là ước tính của Curi, không phải số liệu trong syllabus.",
            "Kế hoạch chỉ là đề xuất — bạn sửa và bấm xác nhận thì mới có hiệu lực.",
        ],
        "warnings": warnings,
        "createdFromReflectionId": goals.get("created_from_reflection_id"),
        "adjustmentsApplied": goals.get("adjustments_applied") or [],
        "reflectionChanges": goals.get("reflection_changes") or [],
        "availability": goals.get("availability") or [],
        "preferredSessions": goals.get("preferred_sessions") or [],
        "provenance": goals.get("provenance") or prov.ai_suggested(PLANNER_VERSION),
        "plannerVersion": goals.get("planner_version") or PLANNER_VERSION,
    }


def is_study_plan(plan: models.WeeklyPlan) -> bool:
    """True for a real weekly study plan.

    ``TimetableService`` creates a container ``WeeklyPlan`` with
    ``goals.kind == "timetable"`` just to hang self-study blocks off. It has no
    tasks and must never be shown as "this week's plan" — otherwise the
    Dashboard renders an empty confirmed plan instead of the "no plan yet"
    empty state, and the Planner refuses to offer a fresh draft.
    """
    goals = plan.goals if isinstance(plan.goals, dict) else {}
    return goals.get("kind") != "timetable"


def _plan_status(plan: models.WeeklyPlan) -> str:
    goals = plan.goals if isinstance(plan.goals, dict) else {}
    status = str(goals.get("status") or "DRAFT").upper()
    if status in {"APPROVED", "ACTIVE", "IN_PROGRESS"}:
        return "IN_PROGRESS"
    return status


def _sources_by_id(db: Session, chunk_ids: set[str]) -> dict[str, dict]:
    if not chunk_ids:
        return {}
    rows = (
        db.query(models.DocumentChunk, models.Document)
        .join(models.Document, models.Document.id == models.DocumentChunk.document_id)
        .filter(models.DocumentChunk.id.in_(list(chunk_ids)))
        .all()
    )
    result: dict[str, dict] = {}
    for chunk, document in rows:
        meta = chunk.metadata_info or {}
        result[chunk.id] = {
            "chunkId": chunk.id,
            "document": document.title,
            "documentId": document.id,
            "section": meta.get("section"),
            "sourceLabel": meta.get("source_label") or document.title,
            "excerpt": _excerpt(chunk.text),
            "provenance": meta.get("provenance") or prov.official(chunk.id),
        }
    return result


def _excerpt(text: str, *, limit: int = 320) -> str:
    cleaned = " ".join((text or "").split())
    if len(cleaned) <= limit:
        return cleaned
    return cleaned[:limit].rsplit(" ", 1)[0] + "…"
