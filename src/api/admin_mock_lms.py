"""Admin Mock LMS sync endpoints (mục 6.6 PROJECT_CONTEXT.md).

Kept in its own router (mirrors `admin_risk_policy.py`) rather than folded into
`admin.py` -- same admin-only auth, mounted separately in `src/main.py`.
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from src.api.auth import get_current_user_from_token
from src.db.connection import get_db
from src.db.models import MockLmsSyncVersion, User, UserRole
from src.repositories.audit_repository import AuditRepository
from src.schemas.admin_schemas import (
    MockLmsSyncPreviewResponse,
    MockLmsSyncPublishRequest,
    MockLmsSyncRollbackRequest,
    MockLmsSyncVersionOut,
)
from src.security.authorization import require_roles
from src.services.core.audit_service import AuditService
from src.services.core.mock_lms_sync_service import MockLmsSyncService, MockLmsSyncValidationError

router = APIRouter(
    prefix="/admin/mock-lms",
    tags=["admin"],
    dependencies=[Depends(require_roles(UserRole.ADMIN))],
)


def get_mock_lms_sync_service(db: Session = Depends(get_db)) -> MockLmsSyncService:
    return MockLmsSyncService(db)


def _serialize(version: MockLmsSyncVersion) -> dict:
    return {
        "syncVersion": version.sync_version,
        "payload": version.payload,
        "reason": version.reason,
        "rolledBackFrom": version.rolled_back_from,
        "createdBy": version.created_by,
        "createdAt": version.created_at.isoformat(),
    }


@router.get("/history", response_model=list[MockLmsSyncVersionOut])
def get_sync_history(service: MockLmsSyncService = Depends(get_mock_lms_sync_service)):
    return [_serialize(v) for v in service.list_history()]


@router.post("/sync/preview", response_model=MockLmsSyncPreviewResponse)
def preview_sync(service: MockLmsSyncService = Depends(get_mock_lms_sync_service)):
    try:
        return service.preview()
    except Exception as exc:  # Mock LMS unreachable, bad OAuth creds, etc.
        raise HTTPException(status_code=502, detail=str(exc)) from exc


@router.post("/sync/publish", response_model=MockLmsSyncVersionOut)
async def publish_sync(
    payload: MockLmsSyncPublishRequest,
    current_user: User = Depends(get_current_user_from_token),
    service: MockLmsSyncService = Depends(get_mock_lms_sync_service),
    db: Session = Depends(get_db),
):
    try:
        version = service.publish(reason=payload.reason, actor_user_id=current_user.id)
        await AuditService(AuditRepository(db)).log_event(
            event_type="mock_lms_sync_published",
            decision="ALLOW",
            actor_user_id=current_user.id,
            resource_type="MOCK_LMS_SYNC",
            resource_id=str(version.sync_version),
            metadata={"reason": payload.reason, "changedCount": len(version.payload)},
            commit=False,
        )
        db.commit()
        db.refresh(version)
    except MockLmsSyncValidationError as exc:
        db.rollback()
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception:
        db.rollback()
        raise
    return _serialize(version)


@router.post("/sync/{version}/rollback", response_model=MockLmsSyncVersionOut)
async def rollback_sync(
    version: int,
    payload: MockLmsSyncRollbackRequest,
    current_user: User = Depends(get_current_user_from_token),
    service: MockLmsSyncService = Depends(get_mock_lms_sync_service),
    db: Session = Depends(get_db),
):
    try:
        result = service.rollback(
            target_version=version, reason=payload.reason, actor_user_id=current_user.id
        )
        await AuditService(AuditRepository(db)).log_event(
            event_type="mock_lms_sync_rolled_back",
            decision="ALLOW",
            actor_user_id=current_user.id,
            resource_type="MOCK_LMS_SYNC",
            resource_id=str(result.sync_version),
            metadata={"reason": payload.reason, "rolledBackFrom": version},
            commit=False,
        )
        db.commit()
        db.refresh(result)
    except MockLmsSyncValidationError as exc:
        db.rollback()
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except LookupError as exc:
        db.rollback()
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except Exception:
        db.rollback()
        raise
    return _serialize(result)
