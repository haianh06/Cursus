from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy.orm import Session

from src.db.models import RiskPolicy


def _now() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


class RiskPolicyRepository:
    def __init__(self, db: Session) -> None:
        self._db = db

    def get_active(self) -> RiskPolicy | None:
        """Highest `policy_version` = current policy. Versions are immutable
        and monotonically increasing (mục 14.1) — there is no separate
        "is_active" flag to fall out of sync with the real max."""
        return (
            self._db.query(RiskPolicy)
            .order_by(RiskPolicy.policy_version.desc())
            .first()
        )

    def get_by_version(self, version: int) -> RiskPolicy | None:
        return self._db.query(RiskPolicy).filter_by(policy_version=version).first()

    def list_history(self) -> list[RiskPolicy]:
        return (
            self._db.query(RiskPolicy)
            .order_by(RiskPolicy.policy_version.desc())
            .all()
        )

    def create_version(
        self,
        *,
        signal_weights: dict,
        signal_thresholds: dict,
        severity_bands: list,
        reason: str,
        created_by: str | None,
        rolled_back_from: int | None = None,
    ) -> RiskPolicy:
        policy = RiskPolicy(
            effective_from=_now(),
            signal_weights=signal_weights,
            signal_thresholds=signal_thresholds,
            severity_bands=severity_bands,
            reason=reason,
            rolled_back_from=rolled_back_from,
            created_by=created_by,
            created_at=_now(),
        )
        self._db.add(policy)
        self._db.flush()
        return policy
