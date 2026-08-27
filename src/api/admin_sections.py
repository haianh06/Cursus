"""Admin Console — quản trị lớp học (`/admin/sections`)."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from src.api.auth import get_current_user_from_token
from src.db import models
from src.db.connection import get_db
from src.repositories.audit_repository import AuditRepository
from src.schemas.admin_schemas import (
    RosterAddRequest,
    SectionCreateRequest,
    SectionOut,
    SectionUpdateRequest,
)
from src.security.authorization import require_permission, require_roles
from src.security.permissions import Permission, Resource
from src.services.core import admin_section_service as svc
from src.services.core.audit_service import AuditService

router = APIRouter(
    prefix="/admin/sections",
    tags=["admin-sections"],
    dependencies=[
        Depends(require_roles(models.UserRole.ADMIN)),
        Depends(require_permission(Resource.COURSE, Permission.MANAGE)),
    ],
)


def _org_or_404(current_user: models.User) -> str:
    if not current_user.organization_id:
        raise HTTPException(status_code=404, detail="organization_required")
    return current_user.organization_id


@router.get("")
def list_sections(
    current_user: models.User = Depends(get_current_user_from_token),
    db: Session = Depends(get_db),
):
    org = _org_or_404(current_user)
    # `svc.list_sections` returns plain snake_case dicts -- run each through
    # `SectionOut` and dump `by_alias` so the list response uses the same
    # camelCase field names (`courseCode`, `instructorId`, ...) as the
    # POST/PATCH responses below. Tasks 7 and 9 both key off those names.
    items = [
        SectionOut(**row).model_dump(by_alias=True)
        for row in svc.list_sections(db, organization_id=org)
    ]
    return {"items": items}


@router.get("/courses")
def list_available_courses(
    current_user: models.User = Depends(get_current_user_from_token),
    db: Session = Depends(get_db),
):
    """Course catalog for the "Thêm lớp" modal's môn dropdown.

    Not part of the original Task 6/7 contract: `create_section` needs a
    real `Course.id`, but the existing `GET /admin/courses` (Task-3-era) is
    built on curriculum-ingestion status and only ever exposes
    `subject_code`, never the DB id this needs, and it 404s/500s entirely
    when no curriculum has been ingested yet. The Course catalog is shared
    across organizations (see `academic_term_repository.list_courses`'s own
    docstring), so this mirrors `_course_belongs_to`'s rule instead of a
    plain org filter.
    """
    org = _org_or_404(current_user)
    courses = (
        db.query(models.Course)
        .filter(
            (models.Course.organization_id.is_(None))
            | (models.Course.organization_id == org)
        )
        .order_by(models.Course.code)
        .all()
    )
    return {"items": [{"id": c.id, "code": c.code, "name": c.name} for c in courses]}


@router.post("", response_model=SectionOut, status_code=status.HTTP_201_CREATED)
async def create_section(
    payload: SectionCreateRequest,
    current_user: models.User = Depends(get_current_user_from_token),
    db: Session = Depends(get_db),
):
    org = _org_or_404(current_user)
    try:
        created = svc.create_section(
            db,
            organization_id=org,
            course_id=payload.course_id,
            section_code=payload.section_code,
            term=payload.term,
            instructor_id=payload.instructor_id,
        )
    except svc.SectionNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    db.commit()
    await AuditService(AuditRepository(db)).log_event(
        event_type="admin_section_created",
        decision="ALLOW",
        actor_user_id=current_user.id,
        resource_type="COURSE_SECTION",
        resource_id=created["id"],
        metadata={"instructorId": created["instructor_id"]},
    )
    return SectionOut(**created)


@router.patch("/{section_id}", response_model=SectionOut)
async def update_section(
    section_id: str,
    payload: SectionUpdateRequest,
    current_user: models.User = Depends(get_current_user_from_token),
    db: Session = Depends(get_db),
):
    org = _org_or_404(current_user)
    try:
        updated = svc.update_section(
            db,
            organization_id=org,
            section_id=section_id,
            section_code=payload.section_code,
            term=payload.term,
            instructor_id=payload.instructor_id,
            # pydantic v2 với populate_by_name ghi TÊN FIELD vào model_fields_set,
            # không phải alias — nên chỉ kiểm "instructor_id". Cần phân biệt
            # "không gửi field này" (giữ nguyên GV) với "gửi null" (bỏ gán GV).
            instructor_field_present="instructor_id" in payload.model_fields_set,
        )
    except svc.SectionNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    db.commit()
    await AuditService(AuditRepository(db)).log_event(
        event_type="admin_section_updated",
        decision="ALLOW",
        actor_user_id=current_user.id,
        resource_type="COURSE_SECTION",
        resource_id=section_id,
        metadata={"instructorId": updated["instructor_id"]},
    )
    return SectionOut(**updated)


@router.delete("/{section_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_section(
    section_id: str,
    current_user: models.User = Depends(get_current_user_from_token),
    db: Session = Depends(get_db),
):
    org = _org_or_404(current_user)
    try:
        svc.delete_section(db, organization_id=org, section_id=section_id)
    except svc.SectionNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except svc.SectionInUseError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    db.commit()
    await AuditService(AuditRepository(db)).log_event(
        event_type="admin_section_deleted",
        decision="ALLOW",
        actor_user_id=current_user.id,
        resource_type="COURSE_SECTION",
        resource_id=section_id,
    )


@router.get("/{section_id}/roster")
def list_roster(
    section_id: str,
    current_user: models.User = Depends(get_current_user_from_token),
    db: Session = Depends(get_db),
):
    try:
        items = svc.list_roster(
            db, organization_id=_org_or_404(current_user), section_id=section_id
        )
    except svc.SectionNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return {"items": items}


@router.post("/{section_id}/roster", status_code=status.HTTP_201_CREATED)
async def add_to_roster(
    section_id: str,
    payload: RosterAddRequest,
    current_user: models.User = Depends(get_current_user_from_token),
    db: Session = Depends(get_db),
):
    try:
        svc.add_to_roster(
            db,
            organization_id=_org_or_404(current_user),
            section_id=section_id,
            student_id=payload.student_id,
        )
    except svc.SectionNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    db.commit()
    await AuditService(AuditRepository(db)).log_event(
        event_type="admin_enrollment_added",
        decision="ALLOW",
        actor_user_id=current_user.id,
        resource_type="ENROLLMENT",
        resource_id=f"{section_id}:{payload.student_id}",
    )
    return {"success": True}


@router.delete("/{section_id}/roster/{student_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_from_roster(
    section_id: str,
    student_id: str,
    current_user: models.User = Depends(get_current_user_from_token),
    db: Session = Depends(get_db),
):
    try:
        svc.remove_from_roster(
            db,
            organization_id=_org_or_404(current_user),
            section_id=section_id,
            student_id=student_id,
        )
    except svc.SectionNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    db.commit()
    await AuditService(AuditRepository(db)).log_event(
        event_type="admin_enrollment_removed",
        decision="ALLOW",
        actor_user_id=current_user.id,
        resource_type="ENROLLMENT",
        resource_id=f"{section_id}:{student_id}",
    )
