"""Admin Console "Overview" dashboard route — ported from the `chung`
branch's design (see docs/branch-audit/chung-admin-frontend.md section 2.1),
scoped to the calling admin's own organization."""
from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from src.api.auth import get_current_user_from_token
from src.db import models
from src.db.connection import get_db
from src.security.authorization import require_permission, require_roles
from src.security.permissions import Permission, Resource
from src.services.core.admin_overview_service import build_overview, build_work_queue

router = APIRouter(
    prefix="/admin",
    tags=["admin-overview"],
    dependencies=[
        Depends(require_roles(models.UserRole.ADMIN)),
        Depends(require_permission(Resource.KPI, Permission.READ)),
    ],
)


@router.get("/overview")
def get_admin_overview(
    current_user: models.User = Depends(get_current_user_from_token),
    db: Session = Depends(get_db),
):
    return build_overview(db, organization_id=current_user.organization_id)


@router.get("/work-queue")
def get_admin_work_queue(
    current_user: models.User = Depends(get_current_user_from_token),
    db: Session = Depends(get_db),
):
    return {"items": build_work_queue(db, organization_id=current_user.organization_id)}
