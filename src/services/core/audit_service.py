import uuid
from datetime import UTC, datetime

from src.db.models import AuditLog
from src.repositories.audit_repository import AuditRepository
from src.security.request_context import get_correlation_id, get_request_id


class AuditService:
    def __init__(self, audit_logs: AuditRepository) -> None:
        self._audit_logs = audit_logs

    async def log_event(
        self,
        *,
        event_type: str,
        decision: str,
        actor_user_id: str | None = None,
        resource_type: str | None = None,
        resource_id: str | None = None,
        ip_address: str | None = None,
        user_agent: str | None = None,
        metadata: dict | None = None,
        commit: bool = True,
    ) -> AuditLog | None:
        metadata_info = metadata or {}
        request_id = get_request_id()
        correlation_id = get_correlation_id()
        if request_id:
            metadata_info = {**metadata_info, "request_id": request_id}
        if correlation_id:
            metadata_info = {**metadata_info, "correlation_id": correlation_id}
        return self._audit_logs.add(
            AuditLog(
                id=f"audit_{uuid.uuid4().hex}",
                actor_user_id=actor_user_id,
                organization_id=self._audit_logs.get_org_for_user(actor_user_id),
                event_type=event_type,
                resource_type=resource_type,
                resource_id=resource_id,
                decision=decision,
                ip_address=ip_address,
                user_agent=user_agent,
                metadata_info=metadata_info,
                created_at=_utc_now_naive(),
            ),
            commit=commit,
        )

    async def list_events(
        self,
        *,
        event_type: str | None = None,
        actor_user_id: str | None = None,
        organization_id: str | None = None,
        limit: int = 100,
    ) -> list[AuditLog]:
        safe_limit = max(1, min(limit, 500))
        return self._audit_logs.list_events(
            event_type=event_type,
            actor_user_id=actor_user_id,
            organization_id=organization_id,
            limit=safe_limit,
        )


def _utc_now_naive() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)
