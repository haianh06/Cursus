"""Student semester setup: pick active courses + weekly time slots for a term."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from src.api.auth import get_current_user_from_token
from src.db import models
from src.db.connection import get_db
from src.db.models import User
from src.repositories.semester_repository import SemesterRepository
from src.schemas.semester import (
    CatalogResponse,
    CreateSemesterRequest,
    CreateSemesterResponse,
    SemesterListResponse,
    SemesterOut,
    SemesterStatusResponse,
)
from src.security.authorization import require_roles
from src.services.academic.semester_service import SemesterService

router = APIRouter(
    prefix="/student/semesters",
    tags=["student-semesters"],
    dependencies=[Depends(require_roles(models.UserRole.STUDENT))],
)


def get_semester_service(db: Session = Depends(get_db)) -> SemesterService:
    return SemesterService(SemesterRepository(db))


@router.get("/catalog", response_model=CatalogResponse)
def get_course_catalog(
    current_user: User = Depends(get_current_user_from_token),
    service: SemesterService = Depends(get_semester_service),
) -> CatalogResponse:
    return CatalogResponse(courses=service.catalog(organization_id=current_user.organization_id))


@router.get("/status", response_model=SemesterStatusResponse)
def get_semester_status(
    current_user: User = Depends(get_current_user_from_token),
    service: SemesterService = Depends(get_semester_service),
) -> SemesterStatusResponse:
    payload = service.status(student_id=current_user.id, organization_id=current_user.organization_id)
    return SemesterStatusResponse(**payload)


@router.get("", response_model=SemesterListResponse)
def list_semesters(
    current_user: User = Depends(get_current_user_from_token),
    service: SemesterService = Depends(get_semester_service),
) -> SemesterListResponse:
    payload = service.list_semesters(current_user.id)
    return SemesterListResponse(**payload)


@router.post("", response_model=CreateSemesterResponse, status_code=status.HTTP_201_CREATED)
def create_semester(
    payload: CreateSemesterRequest,
    current_user: User = Depends(get_current_user_from_token),
    service: SemesterService = Depends(get_semester_service),
) -> CreateSemesterResponse:
    try:
        created = service.create(
            student_id=current_user.id,
            organization_id=current_user.organization_id,
            name=payload.name,
            start_date=payload.start_date,
            end_date=payload.end_date,
            course_ids=payload.course_ids,
            weekly_slots=[slot.model_dump() for slot in payload.weekly_slots],
            exceptions=[item.model_dump() for item in payload.exceptions],
            require_term=False,
        )
    except LookupError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    return CreateSemesterResponse(**created)


@router.get("/{semester_id}", response_model=SemesterOut)
def get_semester(
    semester_id: str,
    current_user: User = Depends(get_current_user_from_token),
    service: SemesterService = Depends(get_semester_service),
) -> SemesterOut:
    try:
        payload = service.get(student_id=current_user.id, semester_id=semester_id)
    except LookupError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    return SemesterOut(**payload)


@router.patch("/{semester_id}", response_model=CreateSemesterResponse)
def update_semester(
    semester_id: str,
    payload: CreateSemesterRequest,
    current_user: User = Depends(get_current_user_from_token),
    service: SemesterService = Depends(get_semester_service),
) -> CreateSemesterResponse:
    try:
        updated = service.update(
            student_id=current_user.id,
            organization_id=current_user.organization_id,
            semester_id=semester_id,
            name=payload.name,
            start_date=payload.start_date,
            end_date=payload.end_date,
            course_ids=payload.course_ids,
            weekly_slots=[slot.model_dump() for slot in payload.weekly_slots],
            exceptions=[item.model_dump() for item in payload.exceptions],
            require_term=False,
        )
    except LookupError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    return CreateSemesterResponse(**updated)
