import uuid
from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from src.db.connection import get_db
from src.db.models import AccessRequest
from src.repositories.access_request_repository import AccessRequestRepository
from src.schemas.public_schemas import (
    AccessRequestAck,
    CreateAccessRequestRequest,
    LandingChatReply,
    LandingChatRequest,
)
from src.services.core import landing_chat_service, rate_limiter

router = APIRouter(prefix="/public", tags=["public"])

# Landing chat calls a real LLM per request (cost-bearing) and needs zero
# auth to reach -- a tighter, IP-keyed cap on top of the app-wide
# RateLimitMiddleware, same reasoning as the 8/day cap on Instructor document
# uploads (src/services/core/instructor_document_request_service.py).
LANDING_CHAT_LIMIT_PER_HOUR = 15


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


@router.post("/landing-chat", response_model=LandingChatReply)
async def landing_chat(payload: LandingChatRequest, request: Request) -> LandingChatReply:
    """No auth required -- the landing page's chat bubble (bottom-right,
    anonymous visitors). Scoped strictly to marketing/product Q&A in
    landing_chat_service.py's system prompt, zero access to any student
    data or course retrieval, since this is reachable with zero auth."""
    client_ip = request.client.host if request.client else "unknown"
    allowed, retry_after = await rate_limiter.allow(
        f"landing_chat:{client_ip}", limit=LANDING_CHAT_LIMIT_PER_HOUR, window_seconds=3600,
    )
    if not allowed:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"Too many questions -- try again in {retry_after}s",
        )
    try:
        result = landing_chat_service.answer(payload.question)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    return LandingChatReply(answer=result["answer"], generated_by_llm=result["generatedByLlm"])
