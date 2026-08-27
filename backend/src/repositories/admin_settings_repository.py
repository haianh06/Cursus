from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy.orm import Session

from src.db.models import AdminSettings

_DEFAULT_SEMESTER = "Fall2026"


def _now() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


class AdminSettingsRepository:
    def __init__(self, db: Session) -> None:
        self._db = db

    def get_for_org(self, organization_id: str) -> AdminSettings:
        """Lazily creates the row on first access — same pattern as
        `GuardrailRuleRepository.ensure_seeded()`, so a fresh organization
        never 404s here, it just gets the documented defaults."""
        settings = (
            self._db.query(AdminSettings).filter_by(organization_id=organization_id).first()
        )
        if settings is None:
            settings = AdminSettings(
                organization_id=organization_id,
                demo_mode_enabled=False,
                auto_risk_alerts_enabled=True,
                default_semester=_DEFAULT_SEMESTER,
                updated_at=_now(),
            )
            self._db.add(settings)
            self._db.flush()
        return settings

    def update_for_org(
        self,
        organization_id: str,
        *,
        demo_mode_enabled: bool | None = None,
        auto_risk_alerts_enabled: bool | None = None,
        default_semester: str | None = None,
        actor_user_id: str | None,
    ) -> AdminSettings:
        settings = self.get_for_org(organization_id)
        if demo_mode_enabled is not None:
            settings.demo_mode_enabled = demo_mode_enabled
        if auto_risk_alerts_enabled is not None:
            settings.auto_risk_alerts_enabled = auto_risk_alerts_enabled
        if default_semester is not None:
            settings.default_semester = default_semester
        settings.updated_at = _now()
        settings.updated_by = actor_user_id
        self._db.flush()
        return settings
