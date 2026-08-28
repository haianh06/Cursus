"""Admin Console "Chi phí AI" — đường đọc bảng `ai_usage`.

Vế "chi phí" của PLO 5 ("giám sát cơ bản: độ trễ / lỗi / chi phí"). Dữ liệu đã
được `AIUsageCallback` ghi sẵn qua một cửa duy nhất là `get_llm()`; route này
không tính toán gì ngoài việc gom lại — logic nằm ở
`src/services/core/ai_usage_service.py`, theo đúng cách `admin_overview.py`
tách route mỏng khỏi service.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from src.api.auth import get_current_user_from_token
from src.db import models
from src.db.connection import get_db
from src.security.authorization import require_permission, require_roles
from src.security.permissions import Permission, Resource
from src.services.core.ai_usage_service import ALLOWED_DAYS, DEFAULT_DAYS, build_ai_usage_report

router = APIRouter(
    prefix="/admin",
    tags=["admin-ai-usage"],
    dependencies=[
        Depends(require_roles(models.UserRole.ADMIN)),
        Depends(require_permission(Resource.KPI, Permission.READ)),
    ],
)


@router.get("/ai-usage")
def get_admin_ai_usage(
    days: int = Query(DEFAULT_DAYS, description=f"Cửa sổ thời gian, một trong {ALLOWED_DAYS}"),
    current_user: models.User = Depends(get_current_user_from_token),
    db: Session = Depends(get_db),
):
    return build_ai_usage_report(db, organization_id=current_user.organization_id, days=days)
