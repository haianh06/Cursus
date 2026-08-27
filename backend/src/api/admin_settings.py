"""Admin settings — demo mode / auto risk alerts / default semester (mục 6.5).

One row per organization (`AdminSettingsRepository.ensure_seeded` pattern via
`get_for_org`), not a single global toggle — consistent with every other
admin-scoped resource in this codebase being organization-scoped.
"""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from src.api.auth import get_current_user_from_token
from src.db.connection import get_db
from src.db.models import AdminSettings, User, UserRole
from src.repositories.admin_settings_repository import AdminSettingsRepository
from src.repositories.audit_repository import AuditRepository
from src.schemas.admin_schemas import AdminSettingsOut, AdminSettingsUpdateRequest
from src.security.authorization import require_roles
from src.services.core.audit_service import AuditService

router = APIRouter(
    prefix="/admin/settings",
    tags=["admin"],
    dependencies=[Depends(require_roles(UserRole.ADMIN))],
)


def get_admin_settings_repository(db: Session = Depends(get_db)) -> AdminSettingsRepository:
    return AdminSettingsRepository(db)


def _serialize(settings: AdminSettings) -> dict:
    return {
        "demoModeEnabled": settings.demo_mode_enabled,
        "autoRiskAlertsEnabled": settings.auto_risk_alerts_enabled,
        "defaultSemester": settings.default_semester,
        "updatedAt": settings.updated_at.isoformat(),
        "updatedBy": settings.updated_by,
    }


@router.get("", response_model=AdminSettingsOut)
def get_settings(
    current_user: User = Depends(get_current_user_from_token),
    repository: AdminSettingsRepository = Depends(get_admin_settings_repository),
    db: Session = Depends(get_db),
):
    settings = repository.get_for_org(current_user.organization_id)
    db.commit()  # persist the lazily-created default row, if this was the first read
    return _serialize(settings)


@router.patch("", response_model=AdminSettingsOut)
async def update_settings(
    payload: AdminSettingsUpdateRequest,
    current_user: User = Depends(get_current_user_from_token),
    repository: AdminSettingsRepository = Depends(get_admin_settings_repository),
    db: Session = Depends(get_db),
):
    settings = repository.update_for_org(
        current_user.organization_id,
        demo_mode_enabled=payload.demoModeEnabled,
        auto_risk_alerts_enabled=payload.autoRiskAlertsEnabled,
        default_semester=payload.defaultSemester,
        actor_user_id=current_user.id,
    )
    await AuditService(AuditRepository(db)).log_event(
        event_type="admin_settings_updated",
        decision="ALLOW",
        actor_user_id=current_user.id,
        resource_type="ADMIN_SETTINGS",
        resource_id=current_user.organization_id,
        metadata=payload.model_dump(exclude_none=True),
        commit=False,
    )
    db.commit()
    db.refresh(settings)
    return _serialize(settings)
