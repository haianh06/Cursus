from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy.orm import Session

from src.db.models import MockLmsSyncVersion


def _now() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


class MockLmsSyncRepository:
    """Mirrors RiskPolicyRepository's shape exactly (mục 6.6/14.1 pattern)."""

    def __init__(self, db: Session) -> None:
        self._db = db

    def get_latest(self) -> MockLmsSyncVersion | None:
        """Highest `sync_version` = most recently applied sync. No separate
        "is_active" flag -- versions are immutable and monotonically
        increasing, same discipline as RiskPolicy."""
        return (
            self._db.query(MockLmsSyncVersion)
            .order_by(MockLmsSyncVersion.sync_version.desc())
            .first()
        )

    def get_by_version(self, version: int) -> MockLmsSyncVersion | None:
        return self._db.query(MockLmsSyncVersion).filter_by(sync_version=version).first()

    def list_history(self) -> list[MockLmsSyncVersion]:
        return (
            self._db.query(MockLmsSyncVersion)
            .order_by(MockLmsSyncVersion.sync_version.desc())
            .all()
        )

    def create_version(
        self,
        *,
        payload: list,
        reason: str,
        created_by: str | None,
        rolled_back_from: int | None = None,
    ) -> MockLmsSyncVersion:
        version = MockLmsSyncVersion(
            payload=payload,
            reason=reason,
            rolled_back_from=rolled_back_from,
            created_by=created_by,
            created_at=_now(),
        )
        self._db.add(version)
        self._db.flush()
        return version
