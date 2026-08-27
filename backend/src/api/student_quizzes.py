"""Student-facing surface for instructor-authored quizzes.

QuizService already had list_for_student/get_for_student/submit (written
alongside the instructor-side quiz CRUD in src/api/instructor.py), but no
router ever called them -- an instructor could create, publish, and grade a
quiz, but no student could ever see or take one. This file is that missing
wiring, nothing new at the service layer.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from src.api.auth import get_current_user_from_token
from src.db import models
from src.db.connection import get_db
from src.repositories.quiz_repository import QuizRepository
from src.security.authorization import require_roles
from src.services.quiz_service import QuizService

router = APIRouter(
    prefix="/student/quizzes",
    tags=["student-quizzes"],
    dependencies=[Depends(require_roles(models.UserRole.STUDENT))],
)


class QuizSubmitRequest(BaseModel):
    answers: dict[str, str] = Field(default_factory=dict)


def get_quiz_service(db: Session = Depends(get_db)) -> QuizService:
    return QuizService(QuizRepository(db))


@router.get("")
def list_my_quizzes(
    current_user: models.User = Depends(get_current_user_from_token),
    service: QuizService = Depends(get_quiz_service),
):
    return service.list_for_student(student_id=current_user.id)


@router.get("/{quiz_id}")
def get_quiz(
    quiz_id: str,
    current_user: models.User = Depends(get_current_user_from_token),
    service: QuizService = Depends(get_quiz_service),
):
    try:
        return service.get_for_student(student_id=current_user.id, quiz_id=quiz_id)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc


@router.post("/{quiz_id}/submit")
def submit_quiz(
    quiz_id: str,
    payload: QuizSubmitRequest,
    current_user: models.User = Depends(get_current_user_from_token),
    service: QuizService = Depends(get_quiz_service),
):
    try:
        return service.submit(student_id=current_user.id, quiz_id=quiz_id, answers=payload.answers)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
