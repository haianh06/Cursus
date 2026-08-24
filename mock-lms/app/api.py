from __future__ import annotations

import jwt
from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db import get_db
from app.models import PlatformAssignment, PlatformCourse
from app.security import decode_access_token

router = APIRouter(prefix="/api/v1", tags=["platform-api"])
_bearer = HTTPBearer()


def require_bearer_token(creds: HTTPAuthorizationCredentials = Depends(_bearer)) -> str:
    try:
        claims = decode_access_token(creds.credentials)
    except jwt.PyJWTError as exc:
        raise HTTPException(status_code=401, detail="invalid_token") from exc
    return claims["sub"]


@router.get("/courses")
def list_courses(
    db: Session = Depends(get_db),
    _client_id: str = Depends(require_bearer_token),
):
    courses = db.scalars(select(PlatformCourse).order_by(PlatformCourse.code)).all()
    return [
        {
            "id": c.id,
            "course_code": c.code,
            "name": c.name,
            "semester": c.semester,
            "credit": c.credit,
        }
        for c in courses
    ]


@router.get("/courses/{code}/assignments")
def list_assignments(
    code: str,
    db: Session = Depends(get_db),
    _client_id: str = Depends(require_bearer_token),
):
    course = db.scalar(select(PlatformCourse).where(PlatformCourse.code == code))
    if not course:
        raise HTTPException(status_code=404, detail="course_not_found")
    return [
        {
            "id": a.id,
            "name": a.name,
            "description": a.description,
            "due_at": a.due_at.isoformat(),
            "points_possible": a.points_possible,
            "updated_at": a.updated_at.isoformat(),
        }
        for a in course.assignments
    ]
