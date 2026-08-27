from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from src.api.auth import get_current_user_from_token
from src.db.connection import get_db
from src.db.models import AuditLog, User, UserRole
from src.repositories.audit_repository import AuditRepository
from src.schemas.audit_schemas import AuditEventResponse
from src.security.authorization import require_permission, require_roles
from src.security.permissions import Permission, Resource
from src.services.core.audit_service import AuditService

router = APIRouter(
    prefix="/audit",
    tags=["audit"],
    dependencies=[
        Depends(require_roles(UserRole.ADMIN)),
        Depends(require_permission(Resource.AUDIT, Permission.READ)),
    ],
)


def get_audit_service(db: Session = Depends(get_db)) -> AuditService:
    return AuditService(AuditRepository(db))


@router.get("/events", response_model=list[AuditEventResponse])
async def list_audit_events(
    event_type: str | None = None,
    actor_user_id: str | None = None,
    limit: int = Query(default=100, ge=1, le=500),
    current_user: User = Depends(get_current_user_from_token),
    audit_service: AuditService = Depends(get_audit_service),
) -> list[AuditEventResponse]:
    # mục 9 ý2 / PENDING_DECISIONS.md #2: this route used to have no
    # organization filter at all -- any ADMIN could read every other
    # organization's audit log. `require_roles(ADMIN)` above only checks the
    # role, never which organization; that check has to happen here, using
    # this specific admin's own current_user.organization_id.
    #
    # Fail closed, same pattern already applied to update_user_status()/
    # get_analytics() earlier tonight: an org-less ADMIN gets 404, never a
    # silent "organization_id is falsy so the filter is skipped" fallthrough
    # to every organization's log.
    if not current_user.organization_id:
        raise HTTPException(status_code=404, detail="No organization for this admin account")

    events = await audit_service.list_events(
        event_type=event_type,
        actor_user_id=actor_user_id,
        organization_id=current_user.organization_id,
        limit=limit,
    )
    return [_serialize_event(event) for event in events]


def _serialize_event(event: AuditLog) -> AuditEventResponse:
    return AuditEventResponse(
        id=event.id,
        actor_user_id=event.actor_user_id,
        event_type=event.event_type,
        resource_type=event.resource_type,
        resource_id=event.resource_id,
        decision=event.decision,
        ip_address=event.ip_address,
        user_agent=event.user_agent,
        metadata=event.metadata_info,
        created_at=event.created_at.isoformat(),
    )
