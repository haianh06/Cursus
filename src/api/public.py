import uuid
from datetime import UTC, datetime

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from src.db.connection import get_db
from src.db.models import AccessRequest
from src.repositories.access_request_repository import AccessRequestRepository
from src.schemas.public_schemas import AccessRequestAck, CreateAccessRequestRequest

router = APIRouter(prefix="/public", tags=["public"])


@router.post(
    "/access-requests",
    response_model=AccessRequestAck,
    status_code=status.HTTP_201_CREATED,
)
async def create_access_request(
    payload: CreateAccessRequestRequest,
    db: Session = Depends(get_db),
) -> AccessRequestAck:
    """No auth required — the landing page 'Yêu cầu quyền truy cập cho tổ
    chức' lead form. Rate-limited by the app-wide RateLimitMiddleware. Does
    not create any account or grant any access by itself; an admin reviews
    submissions and issues invites separately."""
    AccessRequestRepository(db).add(
        AccessRequest(
            id=f"accreq_{uuid.uuid4().hex}",
            institution_name=payload.institution_name.strip(),
            contact_name=payload.contact_name.strip(),
            email=payload.email.strip().lower(),
            role_interested=payload.role_interested,
            message=payload.message,
            created_at=datetime.now(UTC).replace(tzinfo=None),
        )
    )
    return AccessRequestAck()
