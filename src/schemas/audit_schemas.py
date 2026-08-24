from pydantic import BaseModel


class AuditEventResponse(BaseModel):
    id: str
    actor_user_id: str | None
    event_type: str
    resource_type: str | None
    resource_id: str | None
    decision: str
    ip_address: str | None
    user_agent: str | None
    metadata: dict
    created_at: str
