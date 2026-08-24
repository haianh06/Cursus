"""Deterministic rule-based risk scoring (Blueprint §4.1).

The score is a plain sum of fixed rule weights computed from observable task
and event data. No LLM is involved and none may be: an LLM may only add
interpretive prose *around* an already-computed score, never change it. That
is what makes the number explainable to a lecturer and testable in CI.

Rules, evaluated over a 7-day window:

    late >= 2 tasks .................. +2   OVERDUE_TASKS_2_PLUS
    completion < 40% ................. +2   COMPLETION_BELOW_40
    same task deferred >= 2 times ..... +1   TASK_DEFERRED_2_PLUS
    deadline < 48h and not started .... +1   DUE_WITHIN_48H_NOT_STARTED
    inactive 7 days ................... +2   INACTIVE_7_DAYS

    0–2 normal · 3–4 watch · >=5 needs support
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timedelta

from sqlalchemy.orm import Session

from src.db import models
from src.repositories.risk_policy_repository import RiskPolicyRepository
from src.services.core import provenance as prov

RULES_VERSION = "risk_rules_v1"
WINDOW_DAYS = 7

# mục 14.1 "Missingness" -- a distinct severity label, never persisted as an
# open alert (see RiskEngine.persist_assessment), never mapped to the
# "normal/watch/needs_support" bands used elsewhere.
INSUFFICIENT_DATA_SEVERITY = "insufficient_data"

# code -> (points, human-readable rule text). Points here are DEFAULTS only —
# once a RiskPolicy row exists (mục 14.1), `RiskEngine` scores with that
# policy's `signal_weights`/`signal_thresholds` instead. RULE_CATALOG still
# supplies the rule text (that doesn't change per-policy) and is the fallback
# used before any policy has ever been published. Use `current_rule_catalog()`
# below, not this dict directly, anywhere a UI needs to show *current* points.
RULE_CATALOG: dict[str, tuple[int, str]] = {
    "OVERDUE_TASKS_2_PLUS": (2, "Trễ từ 2 task trong 7 ngày"),
    "COMPLETION_BELOW_40": (2, "Tỷ lệ hoàn thành dưới 40%"),
    "TASK_DEFERRED_2_PLUS": (1, "Dời cùng một task ít nhất 2 lần"),
    "DUE_WITHIN_48H_NOT_STARTED": (1, "Deadline dưới 48 giờ và chưa bắt đầu"),
    "INACTIVE_7_DAYS": (2, "Không có hoạt động nào trong 7 ngày"),
}

DEFAULT_SIGNAL_WEIGHTS: dict[str, int] = {
    code: points for code, (points, _text) in RULE_CATALOG.items()
}

# Trigger thresholds for the 4 signals that have a tunable comparison value.
# INACTIVE_7_DAYS has none of its own — it is a plain "any activity in the
# assessment window?" check tied to WINDOW_DAYS, which mục 14.1 does not ask
# to be admin-tunable (it is the *window*, not a score threshold).
DEFAULT_SIGNAL_THRESHOLDS: dict[str, float] = {
    "OVERDUE_TASKS_2_PLUS": 2,
    "COMPLETION_BELOW_40": 0.4,
    "TASK_DEFERRED_2_PLUS": 2,
    "DUE_WITHIN_48H_NOT_STARTED": 48,
}

DEFAULT_SEVERITY_BANDS: tuple[tuple[int, str, str], ...] = (
    (0, "normal", "LOW"),
    (3, "watch", "MEDIUM"),
    (5, "needs_support", "HIGH"),
)


def _load_active_policy(
    db: Session,
) -> tuple[dict[str, int], dict[str, float], tuple[tuple[int, str, str], ...], int | None]:
    """(weights, thresholds, severity_bands, policy_version) — falls back to
    the hardcoded defaults above if no RiskPolicy has been published yet
    (fresh/test DBs), so existing behaviour never breaks for lack of a row."""
    policy = RiskPolicyRepository(db).get_active()
    if policy is None:
        return dict(DEFAULT_SIGNAL_WEIGHTS), dict(DEFAULT_SIGNAL_THRESHOLDS), DEFAULT_SEVERITY_BANDS, None
    bands = tuple(tuple(band) for band in policy.severity_bands)
    return dict(policy.signal_weights), dict(policy.signal_thresholds), bands, policy.policy_version


def current_rule_catalog(db: Session) -> dict[str, tuple[int, str]]:
    """RULE_CATALOG shape (code -> (points, text)) but with the *active*
    policy's points merged in — what any UI listing "how scoring works"
    should read from, instead of the static RULE_CATALOG constant."""
    weights, _thresholds, _bands, _version = _load_active_policy(db)
    return {
        code: (weights.get(code, points), text) for code, (points, text) in RULE_CATALOG.items()
    }

_DONE = "COMPLETED"
_OPEN_STATUSES = {"TODO", "IN_PROGRESS", "DEFERRED", "MISSED"}


@dataclass(frozen=True)
class Signal:
    code: str
    value: float
    points: int
    detail: str

    def as_dict(self) -> dict:
        return {
            "code": self.code,
            "value": self.value,
            "points": self.points,
            "rule": RULE_CATALOG[self.code][1],
            "detail": self.detail,
        }


@dataclass
class RiskAssessment:
    student_id: str
    section_id: str
    score: int
    severity: str
    risk_level: str
    signals: list[Signal] = field(default_factory=list)
    facts: dict = field(default_factory=dict)
    assignment_id: str | None = None
    policy_version: int | None = None

    def as_dict(self) -> dict:
        return {
            "studentId": self.student_id,
            "sectionId": self.section_id,
            "assignmentId": self.assignment_id,
            "score": self.score,
            "severity": self.severity,
            "riskLevel": self.risk_level,
            "signals": [signal.as_dict() for signal in self.signals],
            "facts": self.facts,
            "generatedBy": RULES_VERSION,
            "policyVersion": self.policy_version,
            "formula": " + ".join(
                f"{signal.code}(+{signal.points})" for signal in self.signals
            )
            or "no_signal",
            "provenance": prov.system_derived(RULES_VERSION),
        }


def severity_for(
    score: int, bands: tuple[tuple[int, str, str], ...] = DEFAULT_SEVERITY_BANDS
) -> tuple[str, str]:
    """Map a score onto (severity, legacy risk_level)."""
    severity, level = "normal", "LOW"
    for threshold, band, legacy in bands:
        if score >= threshold:
            severity, level = band, legacy
    return severity, level


class RiskEngine:
    """Computes risk from real task/event rows. Pure read + optional persist.

    Scores with the active `RiskPolicy` (mục 14.1) unless `policy_override`
    is given — the Admin Console preview endpoint uses that to dry-run a
    *proposed* policy against real students without publishing it or
    persisting anything.
    """

    def __init__(
        self,
        db: Session,
        *,
        now: datetime | None = None,
        policy_override: tuple[dict[str, int], dict[str, float], tuple[tuple[int, str, str], ...]]
        | None = None,
    ) -> None:
        self._db = db
        self._now = now or datetime.now()
        if policy_override is not None:
            self._weights, self._thresholds, self._severity_bands = policy_override
            self._policy_version = None
        else:
            self._weights, self._thresholds, self._severity_bands, self._policy_version = (
                _load_active_policy(db)
            )
        # Populated only by `preload()` -- every per-student helper below
        # falls back to its original single-student query when this is None,
        # so behaviour for any caller that never preloads (policy preview,
        # `refresh_student` on one student, tests) is byte-for-byte unchanged.
        self._preloaded: bool = False
        self._tasks_cache: dict[str, tuple[list[models.StudyTask], dict[str, datetime]]] = {}
        self._events_cache: dict[str, list[models.ProgressEvent]] = {}
        self._deadline_cache: dict[str, tuple[float | None, str | None]] = {}
        self._user_cache: dict[str, models.User | None] = {}

    def preload(self, student_ids: list[str]) -> None:
        """Batch-fetch every per-student row `assess()` would otherwise query
        one student at a time -- 4-5 round trips per student against a
        pooled remote Postgres, which is what made the instructor dashboard
        take 4-6s for just 5 students (verified 23/08). Purely additive: does
        not change any scoring logic, only where the same rows come from."""
        ids = list(dict.fromkeys(student_ids))  # de-dup, keep order; safe on []
        if not ids:
            self._preloaded = True
            return

        task_rows = (
            self._db.query(
                models.StudyTask, models.ScheduleBlock.end_time, models.WeeklyPlan.student_id
            )
            .join(models.ScheduleBlock, models.ScheduleBlock.id == models.StudyTask.schedule_block_id)
            .join(models.DailyPlan, models.DailyPlan.id == models.ScheduleBlock.daily_plan_id)
            .join(models.WeeklyPlan, models.WeeklyPlan.id == models.DailyPlan.weekly_plan_id)
            .filter(models.WeeklyPlan.student_id.in_(ids))
            .all()
        )
        for student_id in ids:
            self._tasks_cache[student_id] = ([], {})
        for task, end_time, student_id in task_rows:
            tasks, scheduled = self._tasks_cache[student_id]
            tasks.append(task)
            scheduled[task.id] = end_time

        events = (
            self._db.query(models.ProgressEvent)
            .filter(models.ProgressEvent.student_id.in_(ids))
            .all()
        )
        for student_id in ids:
            self._events_cache[student_id] = []
        for event in events:
            if event.student_id in self._events_cache:
                self._events_cache[event.student_id].append(event)

        assignment_rows = (
            self._db.query(models.Assignment, models.Enrollment.student_id)
            .join(models.Enrollment, models.Enrollment.section_id == models.Assignment.section_id)
            .filter(models.Enrollment.student_id.in_(ids))
            .all()
        )
        override_rows = (
            self._db.query(models.AssignmentOverride)
            .filter(models.AssignmentOverride.student_id.in_(ids))
            .all()
        )
        overrides_by_student: dict[str, dict[str, datetime]] = {sid: {} for sid in ids}
        for row in override_rows:
            overrides_by_student.setdefault(row.student_id, {})[row.assignment_id] = row.due_date_override

        assignments_by_student: dict[str, list[models.Assignment]] = {sid: [] for sid in ids}
        for assignment, student_id in assignment_rows:
            assignments_by_student.setdefault(student_id, []).append(assignment)

        for student_id in ids:
            overrides = overrides_by_student.get(student_id, {})
            upcoming = [
                (a.id, overrides.get(a.id, a.due_date))
                for a in assignments_by_student.get(student_id, [])
                if overrides.get(a.id, a.due_date) >= self._now
            ]
            if not upcoming:
                self._deadline_cache[student_id] = (None, None)
            else:
                assignment_id, due = min(upcoming, key=lambda item: item[1])
                delta = due - self._now
                self._deadline_cache[student_id] = (delta.total_seconds() / 3600.0, assignment_id)

        users = self._db.query(models.User).filter(models.User.id.in_(ids)).all()
        self._user_cache = {user.id: user for user in users}
        for student_id in ids:
            self._user_cache.setdefault(student_id, None)

        self._preloaded = True

    # ── computation ──────────────────────────────────────────────────
    def assess(self, *, student_id: str, section_id: str) -> RiskAssessment:
        window_start = self._now - timedelta(days=WINDOW_DAYS)
        tasks, scheduled = self._tasks_with_schedule(student_id)
        events = (
            self._events_cache.get(student_id, [])
            if self._preloaded
            else self._db.query(models.ProgressEvent)
            .filter(models.ProgressEvent.student_id == student_id)
            .all()
        )

        signals: list[Signal] = []

        total = len(tasks)
        completed = sum(1 for task in tasks if task.status == _DONE)
        completion = (completed / total) if total else 0.0

        # ── late >= 2 tasks ──
        overdue = [
            task
            for task in tasks
            if task.status in _OPEN_STATUSES
            and (due := scheduled.get(task.id)) is not None
            and due < self._now
        ]
        if len(overdue) >= self._thresholds["OVERDUE_TASKS_2_PLUS"]:
            signals.append(
                Signal(
                    code="OVERDUE_TASKS_2_PLUS",
                    value=len(overdue),
                    points=self._weights["OVERDUE_TASKS_2_PLUS"],
                    detail=f"{len(overdue)} task đã qua ngày dự kiến mà chưa hoàn thành",
                )
            )

        # ── completion below threshold ──
        if total > 0 and completion < self._thresholds["COMPLETION_BELOW_40"]:
            signals.append(
                Signal(
                    code="COMPLETION_BELOW_40",
                    value=round(completion, 3),
                    points=self._weights["COMPLETION_BELOW_40"],
                    detail=f"Hoàn thành {completed}/{total} task ({completion:.0%})",
                )
            )

        # ── same task deferred >= threshold times ──
        defer_counts: dict[str, int] = {}
        for event in events:
            if event.event_type == "TASK_DEFERRED" and event.task_id:
                defer_counts[event.task_id] = defer_counts.get(event.task_id, 0) + 1
        repeat_deferred = max(defer_counts.values()) if defer_counts else 0
        if repeat_deferred >= self._thresholds["TASK_DEFERRED_2_PLUS"]:
            signals.append(
                Signal(
                    code="TASK_DEFERRED_2_PLUS",
                    value=repeat_deferred,
                    points=self._weights["TASK_DEFERRED_2_PLUS"],
                    detail=f"Một task bị dời {repeat_deferred} lần",
                )
            )

        # ── deadline < 48h and not started ──
        # "Chưa bắt đầu" is read as: work still remains and none of the
        # remaining tasks has been picked up (nothing IN_PROGRESS, no
        # TASK_STARTED event). A task finished earlier in the week does not
        # cancel the signal — the unfinished part is what is at risk.
        hours_left, assignment_id = self._nearest_deadline_hours(student_id)
        remaining = [task for task in tasks if task.status != _DONE]
        started_ids = {
            event.task_id for event in events if event.event_type == "TASK_STARTED"
        }
        not_started = bool(remaining) and not any(
            task.status == "IN_PROGRESS" or task.id in started_ids for task in remaining
        )
        due_within_hours = self._thresholds["DUE_WITHIN_48H_NOT_STARTED"]
        if hours_left is not None and 0 <= hours_left < due_within_hours and not_started:
            signals.append(
                Signal(
                    code="DUE_WITHIN_48H_NOT_STARTED",
                    value=round(hours_left, 1),
                    points=self._weights["DUE_WITHIN_48H_NOT_STARTED"],
                    detail=(
                        f"Deadline còn {hours_left:.0f} giờ, chưa bắt đầu task nào"
                    ),
                )
            )

        # ── inactive 7 days ── (window itself is not policy-tunable, see
        # DEFAULT_SIGNAL_THRESHOLDS comment above; only its point value is)
        recent = [event for event in events if event.occurred_at >= window_start]
        if tasks and not recent:
            signals.append(
                Signal(
                    code="INACTIVE_7_DAYS",
                    value=WINDOW_DAYS,
                    points=self._weights["INACTIVE_7_DAYS"],
                    detail="Không ghi nhận hoạt động học tập nào trong 7 ngày",
                )
            )

        score = sum(signal.points for signal in signals)
        severity, level = severity_for(score, self._severity_bands)

        # mục 14.1 "Missingness": a brand-new student (or one with zero
        # recorded tasks) can't have any signal fire, so score always lands
        # in the lowest band -- but that must not be presented the same as
        # "normal, observed and fine". Only overrides the *label* on an
        # already-lowest-band result: a genuinely new student who somehow
        # already has real signals (e.g. an overdue task on day 2) keeps
        # that real severity, this never suppresses an actual finding.
        if severity == "normal" and self._insufficient_data(student_id, total):
            severity = INSUFFICIENT_DATA_SEVERITY

        return RiskAssessment(
            student_id=student_id,
            section_id=section_id,
            assignment_id=assignment_id,
            score=score,
            severity=severity,
            risk_level=level,
            signals=signals,
            policy_version=self._policy_version,
            facts={
                "totalTasks": total,
                "completedTasks": completed,
                "completionRate": round(completion, 3),
                "overdueTasks": len(overdue),
                "maxDeferCount": repeat_deferred,
                "hoursToDeadline": round(hours_left, 1) if hours_left is not None else None,
                # ISO string, not a datetime — this dict is persisted into a
                # JSON column and returned over the API.
                "lastActivityAt": (
                    max(event.occurred_at for event in events).isoformat()
                    if events
                    else None
                ),
                "windowDays": WINDOW_DAYS,
            },
        )

    # ── persistence ──────────────────────────────────────────────────
    def refresh_section(self, *, section_id: str) -> list[models.RiskSignal]:
        """Recompute every enrolled student's risk row for one section.

        Rows already closed by a lecturer (resolved) are left alone so an
        intervention is not silently undone by the next dashboard load.
        """
        student_ids = [
            row[0]
            for row in self._db.query(models.Enrollment.student_id)
            .filter(models.Enrollment.section_id == section_id)
            .all()
        ]
        self.preload(student_ids)
        rows: list[models.RiskSignal] = []
        for student_id in student_ids:
            row = self.refresh_student(student_id=student_id, section_id=section_id)
            if row is not None:
                rows.append(row)
        self._db.commit()
        return rows

    def refresh_student(
        self, *, student_id: str, section_id: str
    ) -> models.RiskSignal | None:
        assessment = self.assess(student_id=student_id, section_id=section_id)
        return self.persist_assessment(assessment)

    def persist_assessment(
        self, assessment: RiskAssessment
    ) -> models.RiskSignal | None:
        """Write an already-computed assessment to `risk_signals`.

        Split out from `refresh_student` so a caller that already has the
        assessment (e.g. the instructor dashboard, which needs it for the
        roster anyway) can persist it without paying for a second `assess()`
        pass — each pass is ~6 DB round trips, and against a pooled remote
        Postgres that duplication alone used to add several seconds per
        dashboard load.
        """
        student_id = assessment.student_id
        section_id = assessment.section_id
        existing = (
            self._db.query(models.RiskSignal)
            .filter_by(student_id=student_id, section_id=section_id)
            .order_by(models.RiskSignal.generated_at.desc())
            .first()
        )

        if assessment.severity in ("normal", INSUFFICIENT_DATA_SEVERITY):
            # Below the "watch" band there is no alert to show -- and
            # "insufficient_data" (mục 14.1) is never a real finding to
            # begin with, so it gets the identical no-alert treatment. Keep
            # any resolved history; drop a stale open row. Checked on the
            # already-computed severity label (not a hardcoded "score < 3")
            # so this stays correct if a policy moves the watch-band
            # threshold.
            if existing and existing.resolved_at is None:
                self._db.delete(existing)
                self._db.flush()
            return None

        payload = assessment.as_dict()
        recommended = _recommended_action(assessment)
        if existing is not None and existing.resolved_at is None:
            existing.risk_level = assessment.risk_level
            existing.risk_type = _risk_type(assessment)
            existing.policy_version = assessment.policy_version
            existing.triggered_rules = {
                "version": RULES_VERSION,
                "score": assessment.score,
                "severity": assessment.severity,
                "signals": payload["signals"],
                "formula": payload["formula"],
            }
            existing.evidence = payload["facts"] | {"signals": payload["signals"]}
            existing.recommended_action = recommended
            existing.assignment_id = assessment.assignment_id
            self._db.flush()
            return existing
        if existing is not None and existing.resolved_at is not None:
            return existing

        row = models.RiskSignal(
            id=f"alert_{uuid.uuid4().hex[:10]}",
            student_id=student_id,
            section_id=section_id,
            assignment_id=assessment.assignment_id,
            risk_type=_risk_type(assessment),
            risk_level=assessment.risk_level,
            policy_version=assessment.policy_version,
            triggered_rules={
                "version": RULES_VERSION,
                "score": assessment.score,
                "severity": assessment.severity,
                "signals": payload["signals"],
                "formula": payload["formula"],
            },
            evidence=payload["facts"] | {"signals": payload["signals"]},
            recommended_action=recommended,
            generated_at=self._now,
        )
        self._db.add(row)
        self._db.flush()
        return row

    # ── helpers ──────────────────────────────────────────────────────
    def _insufficient_data(self, student_id: str, total_tasks: int) -> bool:
        """True if this student is too new to trust a "normal" reading:
        zero tasks ever, or an account created less than WINDOW_DAYS ago.
        Account age is a proxy, not the literal "7 days of task data" mục
        14.1 describes -- neither WeeklyPlan nor StudyTask carries its own
        created_at (a schema change, out of scope here), and account
        creation is the closest signal already available. Temporal-leakage
        safe: compares against `self._now` (the same clock every other
        signal in `assess()` uses), never wall-clock `datetime.now()`.
        """
        if total_tasks == 0:
            return True
        user = (
            self._user_cache.get(student_id)
            if self._preloaded
            else self._db.query(models.User).filter_by(id=student_id).first()
        )
        if user is None or user.created_at is None:
            return False
        return (self._now - user.created_at).days < WINDOW_DAYS

    def _tasks_with_schedule(
        self, student_id: str
    ) -> tuple[list[models.StudyTask], dict[str, datetime]]:
        """Tasks + their schedule-block end time in one round trip.

        Previously two near-identical queries (same 3 joins) — merged
        because each round trip to the pooled remote Postgres costs real
        latency, and `assess()` runs this per student per dashboard load.
        """
        if self._preloaded:
            return self._tasks_cache.get(student_id, ([], {}))
        rows = (
            self._db.query(models.StudyTask, models.ScheduleBlock.end_time)
            .join(
                models.ScheduleBlock,
                models.ScheduleBlock.id == models.StudyTask.schedule_block_id,
            )
            .join(
                models.DailyPlan,
                models.DailyPlan.id == models.ScheduleBlock.daily_plan_id,
            )
            .join(
                models.WeeklyPlan,
                models.WeeklyPlan.id == models.DailyPlan.weekly_plan_id,
            )
            .filter(models.WeeklyPlan.student_id == student_id)
            .all()
        )
        tasks = [task for task, _end_time in rows]
        scheduled = {task.id: end_time for task, end_time in rows}
        return tasks, scheduled

    def _nearest_deadline_hours(
        self, student_id: str
    ) -> tuple[float | None, str | None]:
        if self._preloaded:
            return self._deadline_cache.get(student_id, (None, None))
        rows = (
            self._db.query(models.Assignment)
            .join(
                models.Enrollment,
                models.Enrollment.section_id == models.Assignment.section_id,
            )
            .filter(models.Enrollment.student_id == student_id)
            .all()
        )
        # A per-student due-date override (extension, or a demo fixture that
        # needs a deterministic "36 hours left") wins over the section date.
        overrides = {
            row.assignment_id: row.due_date_override
            for row in self._db.query(models.AssignmentOverride)
            .filter(models.AssignmentOverride.student_id == student_id)
            .all()
        }
        upcoming = [
            (row.id, overrides.get(row.id, row.due_date))
            for row in rows
            if overrides.get(row.id, row.due_date) >= self._now
        ]
        if not upcoming:
            return None, None
        assignment_id, due = min(upcoming, key=lambda item: item[1])
        delta = due - self._now
        return delta.total_seconds() / 3600.0, assignment_id


def _risk_type(assessment: RiskAssessment) -> str:
    codes = {signal.code for signal in assessment.signals}
    if "INACTIVE_7_DAYS" in codes:
        return "ABANDONMENT"
    if "DUE_WITHIN_48H_NOT_STARTED" in codes:
        return "LATE_SUBMISSION"
    if "COMPLETION_BELOW_40" in codes:
        return "WEEKLY_GOAL_FAILURE"
    return "ACADEMIC_DECLINE"


def _recommended_action(assessment: RiskAssessment) -> str:
    """Templated, deterministic prose. An LLM may later rewrite this text —
    it must never touch ``assessment.score``."""
    if assessment.severity == "needs_support":
        return (
            "Chủ động liên hệ sinh viên trong 24 giờ tới để hỏi trở ngại cụ thể "
            "và thống nhất một mốc nhỏ có thể làm được trước deadline."
        )
    return (
        "Theo dõi thêm một tuần. Nếu tuần sau vẫn còn task trễ, hãy mời sinh "
        "viên trao đổi ngắn sau giờ học."
    )
