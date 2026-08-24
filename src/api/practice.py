"""Course practice sets: student request/view, instructor review.

Two role scopes live in one file (matches the develop reference at
`src/api/practice.py` conceptually) but as two routers, because a single
`require_roles(...)` router-level dependency cannot express "students hit
these paths, instructors/admins hit those" — see `student_router` /
`instructor_router` below. Both are mounted from `src/main.py`.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from src.api.auth import get_current_user_from_token
from src.db import models
from src.db.connection import get_db
from src.repositories.practice_set_repository import PracticeSetRepository
from src.schemas.practice import (
    PracticeItemUpdateRequest,
    PracticeRequest,
    PracticeReviewRequest,
    PracticeSetOut,
)
from src.security.authorization import require_roles
from src.services.academic.practice_set_service import PracticeSetService

student_router = APIRouter(
    prefix="/student/practice",
    tags=["student-practice"],
    dependencies=[Depends(require_roles(models.UserRole.STUDENT))],
)

instructor_router = APIRouter(
    prefix="/instructor/practice",
    tags=["instructor-practice"],
    dependencies=[Depends(require_roles(models.UserRole.INSTRUCTOR, models.UserRole.ADMIN))],
)


def get_service(db: Session = Depends(get_db)) -> PracticeSetService:
    return PracticeSetService(db, PracticeSetRepository(db))


# ── Student surface ─────────────────────────────────────────────────────


@student_router.get("", response_model=PracticeSetOut)
def get_practice(
    course_code: str,
    week_number: int,
    current_user: models.User = Depends(get_current_user_from_token),
    service: PracticeSetService = Depends(get_service),
) -> PracticeSetOut:
    try:
        payload = service.get_for_student(
            student_id=current_user.id, course_code=course_code, week_number=week_number
        )
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return PracticeSetOut(**payload)


@student_router.post("/request", response_model=PracticeSetOut, status_code=202)
def request_practice(
    payload: PracticeRequest,
    current_user: models.User = Depends(get_current_user_from_token),
    service: PracticeSetService = Depends(get_service),
) -> PracticeSetOut:
    try:
        result = service.request_for_student(
            student_id=current_user.id,
            course_code=payload.courseCode,
            week_number=payload.weekNumber,
            language=payload.language,
        )
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return PracticeSetOut(**result)


# ── Instructor surface ──────────────────────────────────────────────────


@instructor_router.get("", response_model=list[PracticeSetOut])
def list_practice_sets(
    status: str | None = None,
    current_user: models.User = Depends(get_current_user_from_token),
    service: PracticeSetService = Depends(get_service),
) -> list[PracticeSetOut]:
    rows = service.list_for_instructor(
        user_id=current_user.id,
        role=current_user.role,
        organization_id=current_user.organization_id,
        status=status,
    )
    return [PracticeSetOut(**row) for row in rows]


@instructor_router.get("/{set_id}", response_model=PracticeSetOut)
def get_practice_set(
    set_id: str,
    current_user: models.User = Depends(get_current_user_from_token),
    service: PracticeSetService = Depends(get_service),
) -> PracticeSetOut:
    try:
        row = service.get_for_instructor(
            user_id=current_user.id,
            role=current_user.role,
            organization_id=current_user.organization_id,
            set_id=set_id,
        )
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return PracticeSetOut(**row)


@instructor_router.patch("/{set_id}/items/{item_id}", response_model=PracticeSetOut)
def update_practice_item(
    set_id: str,
    item_id: str,
    payload: PracticeItemUpdateRequest,
    current_user: models.User = Depends(get_current_user_from_token),
    service: PracticeSetService = Depends(get_service),
) -> PracticeSetOut:
    try:
        row = service.update_item(
            user_id=current_user.id,
            role=current_user.role,
            organization_id=current_user.organization_id,
            set_id=set_id,
            item_id=item_id,
            prompt=payload.prompt,
            options=payload.options,
            correct_key=payload.correctKey,
            answer=payload.answer,
            explanation=payload.explanation,
            source_label=payload.sourceLabel,
        )
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return PracticeSetOut(**row)


@instructor_router.post("/{set_id}/review", response_model=PracticeSetOut)
def review_practice_set(
    set_id: str,
    payload: PracticeReviewRequest,
    current_user: models.User = Depends(get_current_user_from_token),
    service: PracticeSetService = Depends(get_service),
) -> PracticeSetOut:
    try:
        row = service.review(
            user_id=current_user.id,
            role=current_user.role,
            organization_id=current_user.organization_id,
            set_id=set_id,
            decision=payload.decision,
        )
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return PracticeSetOut(**row)


@instructor_router.post("/{set_id}/regenerate", response_model=PracticeSetOut)
def regenerate_practice_set(
    set_id: str,
    current_user: models.User = Depends(get_current_user_from_token),
    service: PracticeSetService = Depends(get_service),
) -> PracticeSetOut:
    try:
        row = service.regenerate(
            user_id=current_user.id,
            role=current_user.role,
            organization_id=current_user.organization_id,
            set_id=set_id,
        )
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return PracticeSetOut(**row)
