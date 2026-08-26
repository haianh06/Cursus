"""Assemble a compact "what's going on with this student right now" context
block for the chat orchestrator's STATE-aware answers (kế hoạch/rủi ro/phản
tư/lịch tuần). Every field here is read through the SAME resolvers the
Dashboard/Planner/Reflection/Risk screens already use — this service never
re-derives or re-scores anything itself, it only assembles what already
exists so the chatbot's answer about "kế hoạch tuần này của tôi" can never
disagree with what the student sees on those screens.
"""

from __future__ import annotations

from datetime import date

from sqlalchemy.orm import Session

from src.db import models
from src.services.academic.academic_calendar import current_week_for_student
from src.services.academic.timetable_service import TimetableService, monday_of
from src.services.ai.plan_builder import plan_kind, resolve_current_plan, serialize_plan
from src.services.ai.reflection_engine import serialize_reflection
from src.services.risk_signal_service import weekly_plan_completion

_MAX_RISKS = 5


class StudentContextService:
    def __init__(self, db: Session) -> None:
        self._db = db

    def build(self, student_id: str) -> dict:
        current_week = current_week_for_student(self._db, student_id)
        plan, plan_superseded = resolve_current_plan(
            self._db, student_id=student_id, week_number=current_week, with_superseded=True
        )
        plan_summary = self._plan_summary(plan, plan_superseded)

        risks = (
            self._db.query(models.RiskSignal)
            .filter_by(student_id=student_id, resolved_at=None)
            .order_by(models.RiskSignal.generated_at.desc())
            .limit(_MAX_RISKS)
            .all()
        )
        risk_summary = [
            {
                "riskType": r.risk_type,
                "riskLevel": r.risk_level,
                "recommendedAction": r.recommended_action,
                "generatedAt": r.generated_at.isoformat(),
            }
            for r in risks
        ]

        latest_reflection = (
            self._db.query(models.WeeklyReflection)
            .filter_by(student_id=student_id)
            .order_by(models.WeeklyReflection.week_number.desc())
            .first()
        )
        reflection_summary = serialize_reflection(latest_reflection) if latest_reflection else None

        timetable = TimetableService(self._db).get_week(
            student_id=student_id, week_start=monday_of(date.today())
        )

        return {
            "currentWeek": current_week,
            "plan": plan_summary,
            "openRisks": risk_summary,
            "latestReflection": reflection_summary,
            "timetableThisWeek": timetable,
            "text": self._render_text(
                current_week=current_week,
                plan_summary=plan_summary,
                risk_summary=risk_summary,
                reflection_summary=reflection_summary,
                timetable=timetable,
            ),
        }

    def _plan_summary(self, plan, superseded: bool) -> dict | None:
        if plan is None:
            return None
        completed, total = weekly_plan_completion(self._db, plan.id)
        serialized = serialize_plan(self._db, plan)
        return {
            "planKind": plan_kind(plan),
            "weekNumber": plan.week_number,
            "goal": serialized.get("goal"),
            "status": serialized.get("status"),
            "completedTasks": completed,
            "totalTasks": total,
            "completionRate": round(completed / total, 3) if total else None,
            "supersededByAnotherPlan": superseded,
        }

    @staticmethod
    def _render_text(
        *, current_week: int, plan_summary: dict | None, risk_summary: list[dict],
        reflection_summary: dict | None, timetable: dict,
    ) -> str:
        lines = [f"Tuần học hiện tại: Tuần {current_week}."]

        if plan_summary is None:
            lines.append("Sinh viên CHƯA có kế hoạch tuần này.")
        else:
            rate = plan_summary["completionRate"]
            rate_text = f"{round(rate * 100)}%" if rate is not None else "chưa có task"
            lines.append(
                f"Kế hoạch tuần {plan_summary['weekNumber']} (loại: {plan_summary['planKind']}, "
                f"trạng thái: {plan_summary['status']}): mục tiêu \"{plan_summary['goal'] or 'chưa đặt'}\", "
                f"đã hoàn thành {plan_summary['completedTasks']}/{plan_summary['totalTasks']} task ({rate_text})."
            )
            if plan_summary["supersededByAnotherPlan"]:
                lines.append("Lưu ý: có một kế hoạch khác cho cùng tuần này đã bị thay thế bởi kế hoạch trên.")

        if risk_summary:
            risk_lines = "; ".join(
                f"{r['riskType']} (mức {r['riskLevel']})" for r in risk_summary
            )
            lines.append(f"Cảnh báo rủi ro đang mở: {risk_lines}.")
        else:
            lines.append("Không có cảnh báo rủi ro nào đang mở.")

        if reflection_summary:
            metrics = reflection_summary.get("metrics") or {}
            lines.append(
                f"Phản tư gần nhất (tuần {reflection_summary.get('weekNumber')}): "
                f"tỉ lệ hoàn thành {metrics.get('completionRate', 'N/A')}%, "
                f"nhóm {metrics.get('band', 'N/A')}."
            )
        else:
            lines.append("Sinh viên chưa viết Phản tư tuần nào.")

        block_count = len(timetable.get("blocks") or [])
        lines.append(
            f"Lịch tuần này ({timetable.get('weekStart')} → {timetable.get('weekEnd')}): {block_count} mục."
        )

        return "\n".join(lines)
