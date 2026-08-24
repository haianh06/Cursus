from fastapi import Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from src.api.auth import get_current_user_from_token
from src.db.connection import get_db
from src.db.models import User, UserRole
from src.repositories.ownership_repository import OwnershipRepository


async def require_weekly_plan_owner(
    request: Request,
    current_user: User = Depends(get_current_user_from_token),
    db: Session = Depends(get_db),
) -> None:
    """Ownership guard for routes that carry `plan_id` in the JSON body
    (rather than a path parameter). Reads the raw request body instead of
    declaring a typed `Body(...)` field so it does not interfere with the
    route's own Pydantic body model (Starlette caches the request body, so
    both can read it independently)."""
    body = await request.json()
    plan_id = body.get("plan_id") if isinstance(body, dict) else None
    if not plan_id:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="plan_id is required",
        )

    ownership = OwnershipRepository(db)
    if not ownership.student_owns_weekly_plan(current_user.id, plan_id):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Weekly plan not found",
        )


async def require_conversation_owner(
    conversation_id: str,
    current_user: User = Depends(get_current_user_from_token),
    db: Session = Depends(get_db),
) -> None:
    ownership = OwnershipRepository(db)
    if not ownership.student_owns_conversation(current_user.id, conversation_id):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Conversation not found",
        )


async def require_study_task_owner(
    task_id: str,
    current_user: User = Depends(get_current_user_from_token),
    db: Session = Depends(get_db),
) -> None:
    ownership = OwnershipRepository(db)
    if not ownership.student_owns_study_task(current_user.id, task_id):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Study task not found",
        )


async def require_student_course_access(
    course_id: str,
    current_user: User = Depends(get_current_user_from_token),
    db: Session = Depends(get_db),
) -> None:
    ownership = OwnershipRepository(db)
    if not ownership.student_has_course_access(current_user.id, course_id):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Course not found",
        )


async def require_student_assignment_access(
    assignment_id: str,
    current_user: User = Depends(get_current_user_from_token),
    db: Session = Depends(get_db),
) -> None:
    ownership = OwnershipRepository(db)
    if not ownership.student_has_assignment_access(current_user.id, assignment_id):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Assignment not found",
        )


async def require_instructor_student_owner(
    student_id: str,
    current_user: User = Depends(get_current_user_from_token),
    db: Session = Depends(get_db),
) -> None:
    if _role_to_string(current_user.role) == UserRole.ADMIN.value:
        return

    ownership = OwnershipRepository(db)
    if not ownership.instructor_owns_student(current_user.id, student_id):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Student not found",
        )


async def require_instructor_assignment_owner(
    assignment_id: str,
    current_user: User = Depends(get_current_user_from_token),
    db: Session = Depends(get_db),
) -> None:
    if _role_to_string(current_user.role) == UserRole.ADMIN.value:
        return

    ownership = OwnershipRepository(db)
    if not ownership.instructor_owns_assignment(current_user.id, assignment_id):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Assignment not found",
        )


async def require_instructor_risk_owner(
    risk_id: str,
    current_user: User = Depends(get_current_user_from_token),
    db: Session = Depends(get_db),
) -> None:
    if _role_to_string(current_user.role) == UserRole.ADMIN.value:
        return

    ownership = OwnershipRepository(db)
    if not ownership.instructor_owns_risk(current_user.id, risk_id):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Risk case not found",
        )


async def require_instructor_guardrail_owner(
    case_id: str,
    current_user: User = Depends(get_current_user_from_token),
    db: Session = Depends(get_db),
) -> None:
    """Ten tham so PHAI khop dung voi ten path param cua route dang gan
    dependency nay ({case_id} trong @router.post("/guardrail-reviews/{case_id}"))
    — FastAPI resolve dependency path-param theo ten, khong theo vi tri."""
    if _role_to_string(current_user.role) == UserRole.ADMIN.value:
        return

    ownership = OwnershipRepository(db)
    if not ownership.instructor_owns_guardrail_event(current_user.id, case_id):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Guardrail case not found",
        )


def _role_to_string(role: str | UserRole) -> str:
    if isinstance(role, UserRole):
        return role.value
    return role
