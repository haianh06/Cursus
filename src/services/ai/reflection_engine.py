"""Adaptive weekly reflection (Blueprint §2.3 and the §2 question table).

Reflect is not an emoji picker. The flow is:

1. show the student the *real* facts from their task events (no judgement),
2. pick the question set from the completion band,
3. let them explain the cause in their own words,
4. let them pick **structured** adjustments,
5. build a memory preview they can edit/delete before confirming,
6. only confirmed adjustments reach next week's plan.

Question sets by band (Blueprint §2 table):

    >= 80%   what kept your rhythm?          keep buffer / keep slots / repeat split
    30-79%   what drifted most and why?      increase estimate / split / change day
    <  30%   biggest obstacle this week?     reduce load / one priority / ask for help
    always   what to prioritise next week?   free-text
"""

from __future__ import annotations

import logging
import uuid
from datetime import UTC, datetime
from pathlib import Path

from sqlalchemy.orm import Session

from src.db import models
from src.schemas.reflection import LlmReflectionSummaryPayload
from src.services.ai.plan_builder import SUPPORTED_ADJUSTMENTS
from src.services.core import provenance as prov
from src.services.core.llm import get_llm, has_configured_llm

logger = logging.getLogger(__name__)

REFLECTION_VERSION = "reflection_v1"
REFLECTION_PROMPT_PATH = Path(__file__).resolve().parents[2] / "prompts" / "reflection_v1.md"

BAND_HIGH = "high"        # >= 80%
BAND_MID = "mid"          # 30-79%
BAND_LOW = "low"          # < 30%

REASON_CODES: tuple[tuple[str, str], ...] = (
    ("underestimated_time", "Ước tính thiếu thời gian"),
    ("unclear_requirements", "Chưa rõ yêu cầu đề bài"),
    ("blocked_by_group", "Phụ thuộc nhóm/bạn học"),
    ("competing_deadline", "Bị deadline môn khác chen ngang"),
    ("low_energy", "Sức khoẻ / năng lượng thấp"),
    ("procrastination", "Trì hoãn, khó bắt đầu"),
)


def band_for(completion_rate: float) -> str:
    if completion_rate >= 0.8:
        return BAND_HIGH
    if completion_rate >= 0.3:
        return BAND_MID
    return BAND_LOW


def _adjustment(code: str) -> dict:
    return {"code": code, "label": SUPPORTED_ADJUSTMENTS[code]}


QUESTION_SETS: dict[str, list[dict]] = {
    BAND_HIGH: [
        {
            "id": "q_success",
            "type": "text",
            "prompt": "Điều gì giúp bạn giữ được nhịp tuần này?",
            "placeholder": "VD: giữ Chủ nhật làm ngày dự phòng nên không bị dồn.",
            "adjustments": [
                _adjustment("keep_buffer_day"),
                _adjustment("keep_time_slots"),
                _adjustment("repeat_task_split"),
            ],
        }
    ],
    BAND_MID: [
        {
            "id": "q_variance",
            "type": "text_with_reason",
            "prompt": "Việc nào lệch kế hoạch nhất và vì sao?",
            "placeholder": "VD: sơ đồ use-case mất gấp đôi thời gian dự kiến.",
            "reasonCodes": [
                {"code": code, "label": label} for code, label in REASON_CODES
            ],
            "adjustments": [
                _adjustment("increase_diagram_estimate"),
                _adjustment("split_diagram_tasks"),
                _adjustment("keep_buffer_day"),
            ],
        }
    ],
    BAND_LOW: [
        {
            "id": "q_obstacle",
            "type": "text_with_reason",
            "prompt": "Trở ngại lớn nhất tuần này là gì?",
            "placeholder": "VD: bị ốm hai ngày nên không mở bài ra được.",
            "reasonCodes": [
                {"code": code, "label": label} for code, label in REASON_CODES
            ],
            "adjustments": [
                _adjustment("reduce_load"),
                _adjustment("single_priority"),
                _adjustment("request_help"),
            ],
        }
    ],
}

UNIVERSAL_QUESTION: dict = {
    "id": "q_next_priority",
    "type": "text",
    "prompt": "Tuần sau bạn muốn ưu tiên điều gì?",
    "placeholder": "VD: nộp Part 1 sớm một ngày để còn thời gian sửa.",
    "adjustments": [],
}


class ReflectionEngine:
    def __init__(self, db: Session) -> None:
        self._db = db

    # ── facts ────────────────────────────────────────────────────────
    def facts_for_plan(self, plan: models.WeeklyPlan) -> dict:
        """Evidence summary built purely from task rows + progress events."""
        rows = (
            self._db.query(models.StudyTask)
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
        task_ids = [task.id for task in rows]
        events = (
            self._db.query(models.ProgressEvent)
            .filter(models.ProgressEvent.task_id.in_(task_ids))
            .all()
            if task_ids
            else []
        )

        completed = [task for task in rows if task.status == "COMPLETED"]
        deferred = [task for task in rows if task.status == "DEFERRED"]
        estimated = sum(task.planned_minutes for task in rows)
        actual = sum(task.actual_minutes or 0 for task in rows)
        completion = round(len(completed) / len(rows), 3) if rows else 0.0

        over_estimate = [
            {
                "taskId": task.id,
                "title": task.title,
                "estimatedMinutes": task.planned_minutes,
                "actualMinutes": task.actual_minutes,
                "deltaMinutes": (task.actual_minutes or 0) - task.planned_minutes,
            }
            for task in rows
            if task.actual_minutes and task.actual_minutes > task.planned_minutes
        ]

        defer_reasons: dict[str, int] = {}
        for event in events:
            if event.event_type == "TASK_DEFERRED":
                code = (event.payload or {}).get("reason_code") or "unspecified"
                defer_reasons[code] = defer_reasons.get(code, 0) + 1

        return {
            "planId": plan.id,
            "weekNumber": plan.week_number,
            "totalTasks": len(rows),
            "completedTasks": len(completed),
            "deferredTasks": len(deferred),
            "estimatedMinutes": estimated,
            "actualMinutes": actual,
            "completionRate": completion,
            "overEstimateTasks": over_estimate,
            "deferReasons": defer_reasons,
            "provenance": prov.system_derived("reflection_facts_v1"),
        }

    # ── questionnaire ────────────────────────────────────────────────
    def questionnaire(self, facts: dict) -> dict:
        band = band_for(float(facts.get("completionRate") or 0.0))
        questions = [dict(item) for item in QUESTION_SETS[band]]
        questions.append(dict(UNIVERSAL_QUESTION))
        return {
            "band": band,
            "bandLabel": {
                BAND_HIGH: "Hoàn thành ≥ 80%",
                BAND_MID: "Hoàn thành 30–79%",
                BAND_LOW: "Hoàn thành < 30%",
            }[band],
            "questions": questions,
            "version": REFLECTION_VERSION,
        }

    # ── memory preview ───────────────────────────────────────────────
    def build_summary(self, *, facts: dict, answers: list[dict], adjustments: list[str]) -> str:
        """Deterministic, template-based summary — no LLM needed.

        The student edits this text before it is stored, so it is a draft, not
        a claim made by the system on their behalf.
        """
        lines = [
            f"Tuần {facts.get('weekNumber')}: hoàn thành "
            f"{facts.get('completedTasks')}/{facts.get('totalTasks')} task "
            f"({round(float(facts.get('completionRate') or 0) * 100)}%), "
            f"dời {facts.get('deferredTasks')} task.",
        ]
        estimated = facts.get("estimatedMinutes") or 0
        actual = facts.get("actualMinutes") or 0
        if actual and estimated:
            lines.append(
                f"Thời gian thực tế {actual} phút so với ước tính {estimated} phút."
            )
        for answer in answers:
            text = (answer.get("answer") or "").strip()
            if text:
                lines.append(f"Ghi nhận: {text}")
            reason = answer.get("reasonCode")
            if reason:
                label = dict(REASON_CODES).get(reason, reason)
                lines.append(f"Nguyên nhân đã chọn: {label}.")
        confirmed = [item for item in adjustments if item in SUPPORTED_ADJUSTMENTS]
        if confirmed:
            lines.append(
                "Điều chỉnh cho tuần sau: "
                + "; ".join(SUPPORTED_ADJUSTMENTS[item] for item in confirmed)
                + "."
            )
        return " ".join(lines)

    def build_summary_llm(
        self, *, facts: dict, answers: list[dict], adjustments: list[str]
    ) -> tuple[str, dict]:
        """LLM-drafted summary for the *preview* endpoint only — the student
        always reviews/edits this before it is saved. Falls back to the
        deterministic `build_summary` on any error or when no API key is
        configured; never raises. `save_reflection`'s own fallback stays on
        `build_summary` directly (not this method) so a saved reflection can
        never depend on an LLM call succeeding.

        Returns (summary, trace) — P0#8 (mục 9 ý8, Option B,
        docs/PENDING_DECISIONS.md #1). `trace["retrieval_empty"]` is always
        False here: unlike `plan_builder`'s LLM path, this service does not
        retrieve syllabus chunks at all (the prompt is built entirely from
        `facts`/`answers`/`adjustments`, already computed from the plan) —
        kept in the trace shape for consistency across all 3 services rather
        than fabricating meaning for a step that doesn't exist here.
        """
        confirmed = [item for item in adjustments if item in SUPPORTED_ADJUSTMENTS]
        deterministic = self.build_summary(facts=facts, answers=answers, adjustments=confirmed)

        if not has_configured_llm():
            return deterministic, {"llm_attempted": False, "llm_success": False, "retrieval_empty": False}

        try:
            system_prompt = REFLECTION_PROMPT_PATH.read_text(encoding="utf-8")
            adjustment_labels = [SUPPORTED_ADJUSTMENTS[item] for item in confirmed]
            user_prompt = (
                f"Facts: {facts}\n"
                f"Student answers: {answers}\n"
                f"Confirmed adjustments for next week: {adjustment_labels}\n"
            )
            llm = get_llm().with_structured_output(LlmReflectionSummaryPayload)
            payload = llm.invoke(
                [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ]
            )
            if not isinstance(payload, LlmReflectionSummaryPayload):
                payload = LlmReflectionSummaryPayload.model_validate(payload)
            summary = payload.summary.strip()
            if summary:
                return summary, {"llm_attempted": True, "llm_success": True, "retrieval_empty": False}
            return deterministic, {"llm_attempted": True, "llm_success": False, "retrieval_empty": False}
        except Exception:
            logger.exception("llm_reflection_summary_failed plan_week=%s", facts.get("weekNumber"))
            return deterministic, {"llm_attempted": True, "llm_success": False, "retrieval_empty": False}

    def preview(self, plan: models.WeeklyPlan) -> dict:
        facts = self.facts_for_plan(plan)
        questionnaire = self.questionnaire(facts)
        return {
            "planId": plan.id,
            "weekNumber": plan.week_number,
            "facts": facts,
            **questionnaire,
            "adjustmentCatalog": [
                {"code": code, "label": label}
                for code, label in SUPPORTED_ADJUSTMENTS.items()
            ],
            "existing": self._existing_payload(plan),
        }

    def _existing_payload(self, plan: models.WeeklyPlan) -> dict | None:
        row = (
            self._db.query(models.WeeklyReflection)
            .filter_by(student_id=plan.student_id, week_number=plan.week_number)
            .first()
        )
        return serialize_reflection(row) if row else None

    # ── persistence ──────────────────────────────────────────────────
    def save(
        self,
        *,
        plan: models.WeeklyPlan,
        answers: list[dict],
        adjustments: list[str],
        summary: str | None,
        student_confirmed: bool,
        share_with_advisor: bool,
    ) -> models.WeeklyReflection:
        facts = self.facts_for_plan(plan)
        confirmed_adjustments = [
            item for item in adjustments if item in SUPPORTED_ADJUSTMENTS
        ]
        summary_provided = bool((summary or "").strip())
        final_summary = (summary or "").strip() or self.build_summary(
            facts=facts, answers=answers, adjustments=confirmed_adjustments
        )

        row = (
            self._db.query(models.WeeklyReflection)
            .filter_by(student_id=plan.student_id, week_number=plan.week_number)
            .first()
        )
        metrics = {
            "version": REFLECTION_VERSION,
            "planId": plan.id,
            "facts": facts,
            "answers": answers,
            "adjustments": confirmed_adjustments,
            "studentConfirmed": bool(student_confirmed),
            "shareWithAdvisor": bool(share_with_advisor),
            "band": band_for(float(facts.get("completionRate") or 0.0)),
            # Legacy keys kept so older dashboard reads do not break.
            "completionRate": round(float(facts.get("completionRate") or 0.0) * 100, 1),
            "hoursPlanned": round((facts.get("estimatedMinutes") or 0) / 60.0, 1),
            "hoursActual": round((facts.get("actualMinutes") or 0) / 60.0, 1),
            "provenance": prov.user_entered("reflection_form"),
            # P0#8 trace (mục 9 ý8, Option B, docs/PENDING_DECISIONS.md #1).
            # `save()` itself NEVER calls the LLM by design (see this class's
            # `build_summary_llm` docstring) — llm_attempted/llm_success are
            # always False here, not because of a failure, but because this
            # path structurally never attempts one. The only place an LLM
            # touches a reflection is the separate, non-persisting
            # `/reflections/preview-summary` endpoint; its own trace is
            # returned in that response, not threaded through to here, since
            # the student may freely edit or replace that draft before
            # saving. `fallback_used` reflects THIS call's own behavior:
            # True when the client sent no summary text at all, so the
            # deterministic `build_summary` template was used instead.
            "llm_attempted": False,
            "llm_success": False,
            "fallback_used": not summary_provided,
            "retrieval_empty": False,
        }

        if row is None:
            row = models.WeeklyReflection(
                id=f"ref_{uuid.uuid4().hex[:8]}",
                student_id=plan.student_id,
                week_number=plan.week_number,
                content=final_summary,
                generated_at=datetime.now(UTC).replace(tzinfo=None),
                metrics=metrics,
            )
            self._db.add(row)
        else:
            row.content = final_summary
            row.metrics = metrics
            row.generated_at = datetime.now(UTC).replace(tzinfo=None)

        # Mark the plan as reflected so the PDR stepper can move on.
        goals = dict(plan.goals or {})
        goals["status"] = "REFLECTED" if student_confirmed else goals.get("status", "DRAFT")
        goals["reflection_id"] = row.id
        plan.goals = goals

        self._db.commit()
        return row


def serialize_reflection(row: models.WeeklyReflection) -> dict:
    metrics = row.metrics if isinstance(row.metrics, dict) else {}
    return {
        "id": row.id,
        "weekNumber": row.week_number,
        "planId": metrics.get("planId"),
        "summary": row.content,
        "content": row.content,
        "facts": metrics.get("facts") or {},
        "answers": metrics.get("answers") or [],
        "adjustments": metrics.get("adjustments") or [],
        "adjustmentLabels": [
            SUPPORTED_ADJUSTMENTS[item]
            for item in (metrics.get("adjustments") or [])
            if item in SUPPORTED_ADJUSTMENTS
        ],
        "band": metrics.get("band"),
        "studentConfirmed": bool(metrics.get("studentConfirmed")),
        "shareWithAdvisor": bool(metrics.get("shareWithAdvisor")),
        "metrics": metrics,
        "generatedAt": row.generated_at.isoformat(),
        "provenance": metrics.get("provenance") or prov.user_entered("reflection_form"),
    }
