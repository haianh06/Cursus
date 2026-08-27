from fastapi import APIRouter, Depends, HTTPException

from src.agents.graph import agent
from src.api.auth import get_current_user_from_token
from src.db import models
from src.db.models import User
from src.schemas.chat import ChatRequest, ChatResponse
from src.security.authorization import require_roles

router = APIRouter()


@router.post(
    "/chat",
    response_model=ChatResponse,
    dependencies=[Depends(require_roles(models.UserRole.STUDENT))],
)
async def chat(
    request: ChatRequest,
    _current_user: User = Depends(get_current_user_from_token),
) -> ChatResponse:
    """Chat với AI agent — chỉ sinh viên (STUDENT)."""
    try:
        result = await agent.ainvoke({"query": request.message})
        return ChatResponse(
            response=result.get("response", ""),
            analysis=result.get("analysis", ""),
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/status")
async def agent_status():
    """Kiểm tra trạng thái agent."""
    return {"status": "ready", "agent": "LangGraph Agent v1.0"}
