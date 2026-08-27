"""Admin-facing risk policy management (mục 14.1 PROJECT_CONTEXT.md).

Validation + preview live here rather than in the route so they stay unit
-testable without spinning up FastAPI, matching how `guardrail_rules.py` /
`GuardrailRuleRepository` split responsibilities.
"""

from __future__ import annotations

from sqlalchemy.orm import Session

from src.db import models
from src.repositories.risk_policy_repository import RiskPolicyRepository
from src.services.ai.risk_engine import DEFAULT_SEVERITY_BANDS, RiskEngine

REQUIRED_SIGNAL_CODES = frozenset(
    {
        "OVERDUE_TASKS_2_PLUS",
        "COMPLETION_BELOW_40",
        "TASK_DEFERRED_2_PLUS",
        "DUE_WITHIN_48H_NOT_STARTED",
        "INACTIVE_7_DAYS",
        "SELF_REPORTED_HIGH_STRESS",
    }
)
# Signals with a tunable trigger threshold. INACTIVE_7_DAYS has none of its
# own (see risk_engine.py comment) so it is excluded here on purpose.
REQUIRED_THRESHOLD_CODES = frozenset(
    {"OVERDUE_TASKS_2_PLUS", "COMPLETION_BELOW_40", "TASK_DEFERRED_2_PLUS", "DUE_WITHIN_48H_NOT_STARTED"}
)

WEIGHT_BOUNDS: dict[str, tuple[float, float]] = {code: (0, 5) for code in REQUIRED_SIGNAL_CODES}
THRESHOLD_BOUNDS: dict[str, tuple[float, float]] = {
    "OVERDUE_TASKS_2_PLUS": (1, 10),
    "COMPLETION_BELOW_40": (0.05, 0.95),
    "TASK_DEFERRED_2_PLUS": (1, 10),
    "DUE_WITHIN_48H_NOT_STARTED": (1, 168),
}
_EXPECTED_BAND_SHAPE = (("normal", "LOW"), ("watch", "MEDIUM"), ("needs_support", "HIGH"))


class RiskPolicyValidationError(ValueError):
    pass


def validate_policy_input(
    signal_weights: dict, signal_thresholds: dict, severity_bands: list
) -> None:
    if set(signal_weights) != REQUIRED_SIGNAL_CODES:
        raise RiskPolicyValidationError(
            f"signal_weights must have exactly these codes: {sorted(REQUIRED_SIGNAL_CODES)}"
        )
    if set(signal_thresholds) != REQUIRED_THRESHOLD_CODES:
        raise RiskPolicyValidationError(
            f"signal_thresholds must have exactly these codes: {sorted(REQUIRED_THRESHOLD_CODES)}"
        )
    for code, value in signal_weights.items():
        low, high = WEIGHT_BOUNDS[code]
        if not isinstance(value, (int, float)) or isinstance(value, bool) or not (low <= value <= high):
            raise RiskPolicyValidationError(f"{code} weight must be a number in [{low}, {high}]")
    for code, value in signal_thresholds.items():
        low, high = THRESHOLD_BOUNDS[code]
        if not isinstance(value, (int, float)) or isinstance(value, bool) or not (low <= value <= high):
            raise RiskPolicyValidationError(f"{code} threshold must be a number in [{low}, {high}]")

    if len(severity_bands) != 3:
        raise RiskPolicyValidationError("severity_bands must have exactly 3 bands")
    for (threshold, band, legacy), (expected_band, expected_legacy) in zip(
        severity_bands, _EXPECTED_BAND_SHAPE, strict=True
    ):
        if band != expected_band or legacy != expected_legacy:
            raise RiskPolicyValidationError(
                "severity_bands must be ordered normal/LOW, watch/MEDIUM, needs_support/HIGH"
            )
        if not isinstance(threshold, (int, float)) or isinstance(threshold, bool):
            raise RiskPolicyValidationError(f"{band} threshold must be a number")
    normal_t, watch_t, needs_support_t = (band[0] for band in severity_bands)
    if normal_t != 0:
        raise RiskPolicyValidationError("normal band must start at 0")
    if not (1 <= watch_t < needs_support_t <= 20):
        raise RiskPolicyValidationError(
            "watch threshold must be >=1 and strictly below needs_support (<=20) — "
            "e.g. watch=1 would make almost any single signal 'need support', which "
            "mục 14.1 explicitly calls out as an unreasonable threshold"
        )


def _as_band_tuples(severity_bands) -> tuple[tuple[int, str, str], ...]:
    return tuple(tuple(band) for band in severity_bands)


class RiskPolicyService:
    def __init__(self, db: Session) -> None:
        self._db = db
        self._repo = RiskPolicyRepository(db)

    def get_active(self) -> models.RiskPolicy | None:
        return self._repo.get_active()

    def list_history(self) -> list[models.RiskPolicy]:
        return self._repo.list_history()

    def preview(
        self, *, signal_weights: dict, signal_thresholds: dict, severity_bands: list
    ) -> dict:
        """Re-assesses every (student, section) pair that currently has a
        risk_signals row under both the active policy and the proposed one,
        and reports how many would change severity band. Nothing is
        persisted. Scope is "students with an existing alert row" (open or
        resolved) rather than the whole student body — a bounded, meaningful
        population without an expensive whole-org re-assessment."""
        validate_policy_input(signal_weights, signal_thresholds, severity_bands)

        pairs = (
            self._db.query(models.RiskSignal.student_id, models.RiskSignal.section_id)
            .distinct()
            .all()
        )

        active = self._repo.get_active()
        current_override = (
            (dict(active.signal_weights), dict(active.signal_thresholds), _as_band_tuples(active.severity_bands))
            if active is not None
            else None
        )
        current_engine = RiskEngine(self._db, policy_override=current_override)
        proposed_engine = RiskEngine(
            self._db,
            policy_override=(dict(signal_weights), dict(signal_thresholds), _as_band_tuples(severity_bands)),
        )

        changes = []
        for student_id, section_id in pairs:
            before = current_engine.assess(student_id=student_id, section_id=section_id)
            after = proposed_engine.assess(student_id=student_id, section_id=section_id)
            if before.severity != after.severity:
                changes.append(
                    {
                        "studentId": student_id,
                        "sectionId": section_id,
                        "beforeSeverity": before.severity,
                        "afterSeverity": after.severity,
                        "beforeScore": before.score,
                        "afterScore": after.score,
                    }
                )

        return {
            "totalEvaluated": len(pairs),
            "changedCount": len(changes),
            "changes": changes,
        }

    def publish(
        self,
        *,
        signal_weights: dict,
        signal_thresholds: dict,
        severity_bands: list,
        reason: str,
        actor_user_id: str | None,
    ) -> models.RiskPolicy:
        validate_policy_input(signal_weights, signal_thresholds, severity_bands)
        if not reason or not reason.strip():
            raise RiskPolicyValidationError("A reason is required to publish a new risk policy")
        return self._repo.create_version(
            signal_weights=signal_weights,
            signal_thresholds=signal_thresholds,
            severity_bands=severity_bands,
            reason=reason.strip(),
            created_by=actor_user_id,
        )

    def rollback(self, *, target_version: int, reason: str, actor_user_id: str | None) -> models.RiskPolicy:
        if not reason or not reason.strip():
            raise RiskPolicyValidationError("A reason is required to roll back a risk policy")
        target = self._repo.get_by_version(target_version)
        if target is None:
            raise LookupError(f"Unknown risk policy version: {target_version}")
        return self._repo.create_version(
            signal_weights=dict(target.signal_weights),
            signal_thresholds=dict(target.signal_thresholds),
            severity_bands=list(target.severity_bands),
            reason=reason.strip(),
            created_by=actor_user_id,
            rolled_back_from=target_version,
        )


def default_policy_payload() -> dict:
    """What a brand-new org (no RiskPolicy row yet) is effectively scoring
    with — used by the GET endpoint so the Admin Console always has
    something concrete to show, never a bare null."""
    from src.services.ai.risk_engine import DEFAULT_SIGNAL_THRESHOLDS, DEFAULT_SIGNAL_WEIGHTS

    return {
        "policyVersion": None,
        "effectiveFrom": None,
        "signalWeights": dict(DEFAULT_SIGNAL_WEIGHTS),
        "signalThresholds": dict(DEFAULT_SIGNAL_THRESHOLDS),
        "severityBands": [list(band) for band in DEFAULT_SEVERITY_BANDS],
        "reason": "No policy published yet — scoring with built-in defaults.",
        "rolledBackFrom": None,
        "createdBy": None,
        "createdAt": None,
    }
