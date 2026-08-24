"""Admin risk-policy versioning endpoints (mục 14.1 PROJECT_CONTEXT.md).

Kept in its own router (mirrors `admin.academic_router`) rather than folded
into the already-large `admin.py` — same admin-only auth, mounted separately
in `src/main.py`.
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from src.api.auth import get_current_user_from_token
from src.db.connection import get_db
from src.db.models import RiskPolicy, User, UserRole
from src.repositories.audit_repository import AuditRepository
from src.schemas.admin_schemas import (
    RiskPolicyDraft,
    RiskPolicyOut,
    RiskPolicyPreviewResponse,
    RiskPolicyPublishRequest,
    RiskPolicyRollbackRequest,
)
from src.security.authorization import require_permission, require_roles
from src.security.permissions import Permission, Resource
from src.services.core.audit_service import AuditService
from src.services.core.risk_policy_service import (
    RiskPolicyService,
    RiskPolicyValidationError,
    default_policy_payload,
)

router = APIRouter(
    prefix="/admin/risk-policy",
    tags=["admin"],
    dependencies=[Depends(require_roles(UserRole.ADMIN))],
)


def get_risk_policy_service(db: Session = Depends(get_db)) -> RiskPolicyService:
    return RiskPolicyService(db)


def _serialize(policy: RiskPolicy) -> dict:
    return {
        "policyVersion": policy.policy_version,
        "effectiveFrom": policy.effective_from.isoformat(),
        "signalWeights": policy.signal_weights,
        "signalThresholds": policy.signal_thresholds,
        "severityBands": [list(band) for band in policy.severity_bands],
        "reason": policy.reason,
        "rolledBackFrom": policy.rolled_back_from,
        "createdBy": policy.created_by,
        "createdAt": policy.created_at.isoformat(),
    }


@router.get("", response_model=RiskPolicyOut, dependencies=[Depends(require_permission(Resource.RISK, Permission.READ))])
def get_active_policy(service: RiskPolicyService = Depends(get_risk_policy_service)):
    active = service.get_active()
    return _serialize(active) if active is not None else default_policy_payload()


@router.get(
    "/history",
    response_model=list[RiskPolicyOut],
    dependencies=[Depends(require_permission(Resource.RISK, Permission.READ))],
)
def get_policy_history(service: RiskPolicyService = Depends(get_risk_policy_service)):
    return [_serialize(policy) for policy in service.list_history()]


@router.post(
    "/preview",
    response_model=RiskPolicyPreviewResponse,
    dependencies=[Depends(require_permission(Resource.RISK, Permission.MANAGE))],
)
def preview_policy(
    payload: RiskPolicyDraft,
    service: RiskPolicyService = Depends(get_risk_policy_service),
):
    try:
        return service.preview(
            signal_weights=payload.signalWeights,
            signal_thresholds=payload.signalThresholds,
            severity_bands=[list(band) for band in payload.severityBands],
        )
    except RiskPolicyValidationError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post(
    "",
    response_model=RiskPolicyOut,
    dependencies=[Depends(require_permission(Resource.RISK, Permission.MANAGE))],
)
async def publish_policy(
    payload: RiskPolicyPublishRequest,
    current_user: User = Depends(get_current_user_from_token),
    service: RiskPolicyService = Depends(get_risk_policy_service),
    db: Session = Depends(get_db),
):
    try:
        policy = service.publish(
            signal_weights=payload.signalWeights,
            signal_thresholds=payload.signalThresholds,
            severity_bands=[list(band) for band in payload.severityBands],
            reason=payload.reason,
            actor_user_id=current_user.id,
        )
        await AuditService(AuditRepository(db)).log_event(
            event_type="risk_policy_published",
            decision="ALLOW",
            actor_user_id=current_user.id,
            resource_type="RISK_POLICY",
            resource_id=str(policy.policy_version),
            metadata={"reason": payload.reason, "signalWeights": payload.signalWeights},
            commit=False,
        )
        db.commit()
        db.refresh(policy)
    except RiskPolicyValidationError as exc:
        db.rollback()
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception:
        db.rollback()
        raise
    return _serialize(policy)


@router.post(
    "/{version}/rollback",
    response_model=RiskPolicyOut,
    dependencies=[Depends(require_permission(Resource.RISK, Permission.MANAGE))],
)
async def rollback_policy(
    version: int,
    payload: RiskPolicyRollbackRequest,
    current_user: User = Depends(get_current_user_from_token),
    service: RiskPolicyService = Depends(get_risk_policy_service),
    db: Session = Depends(get_db),
):
    try:
        policy = service.rollback(
            target_version=version, reason=payload.reason, actor_user_id=current_user.id
        )
        await AuditService(AuditRepository(db)).log_event(
            event_type="risk_policy_rolled_back",
            decision="ALLOW",
            actor_user_id=current_user.id,
            resource_type="RISK_POLICY",
            resource_id=str(policy.policy_version),
            metadata={"reason": payload.reason, "rolledBackFrom": version},
            commit=False,
        )
        db.commit()
        db.refresh(policy)
    except RiskPolicyValidationError as exc:
        db.rollback()
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except LookupError as exc:
        db.rollback()
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except Exception:
        db.rollback()
        raise
    return _serialize(policy)
