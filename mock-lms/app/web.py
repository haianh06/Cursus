from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter, Depends, Form, HTTPException, Request
from fastapi.responses import RedirectResponse
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db import get_db
from app.models import PlatformAssignment, PlatformCourse
from app.sso import (
    SESSION_COOKIE_NAME,
    decode_state,
    exchange_code,
    require_admin,
    require_identity,
    _sign_session,
    STATE_COOKIE_NAME,
)

router = APIRouter(tags=["web"])
# cache_size=0: Jinja2 3.1.x's Environment.cache (an LRUCache) hits a genuine
# `TypeError: cannot use 'tuple' as a dict key (unhashable type: 'dict')` under this
# stack's Python 3.14.7 + Starlette 1.4.1 combo specifically when templates are first
# loaded from FastAPI's request threadpool (reproducible: fails via uvicorn, does not
# fail in a single-threaded script). Disabling the cache skips the buggy code path
# entirely; fine for this deliberately tiny, low-traffic mock UI.
import jinja2  # noqa: E402

_env = jinja2.Environment(
    loader=jinja2.FileSystemLoader("app/templates"),
    autoescape=jinja2.select_autoescape(),
    cache_size=0,
)
from fastapi.templating import Jinja2Templates  # noqa: E402

templates = Jinja2Templates(env=_env)


@router.get("/")
def root():
    return RedirectResponse(url="/courses")


@router.get("/sso/callback")
async def sso_callback(request: Request, code: str, state: str):
    cookie_nonce = request.cookies.get(STATE_COOKIE_NAME)
    nonce, return_to = decode_state(state)
    if not cookie_nonce or cookie_nonce != nonce:
        raise HTTPException(status_code=400, detail="sso_state_mismatch")

    identity = await exchange_code(code)
    session_token = _sign_session(
        {
            "user_id": identity["user_id"],
            "role": identity["role"],
            "name": identity["name"],
            "email": identity["email"],
        }
    )
    response = RedirectResponse(url=return_to or "/courses")
    response.delete_cookie(STATE_COOKIE_NAME)
    response.set_cookie(
        SESSION_COOKIE_NAME,
        session_token,
        max_age=3600,
        httponly=True,
        samesite="lax",
    )
    return response


@router.get("/courses")
def courses_page(
    request: Request,
    db: Session = Depends(get_db),
    identity: dict = Depends(require_identity),
):
    courses = db.scalars(select(PlatformCourse).order_by(PlatformCourse.code)).all()
    # Grouped by term, not one flat unordered grid -- a real course catalog
    # (Canvas's "All Courses" filter, and the FPT reference screens this app
    # is modelled on) always organises by semester/kỳ first.
    by_semester: dict[str, list[PlatformCourse]] = {}
    for course in courses:
        by_semester.setdefault(course.semester, []).append(course)
    semesters = sorted(
        by_semester.items(),
        key=lambda item: int(item[0]) if item[0].isdigit() else 999,
    )
    # Starlette here requires the newer `(request, name, context)` signature -- the older
    # `(name, {"request": request, ...})` style silently shifts arguments (name ends up
    # holding the context dict) instead of erroring on call, so this isn't optional style.
    return templates.TemplateResponse(
        request,
        "courses.html",
        {"courses": courses, "semesters": semesters, "identity": identity},
    )


@router.get("/courses/{code}")
def course_detail_page(
    code: str,
    request: Request,
    db: Session = Depends(get_db),
    identity: dict = Depends(require_identity),
):
    course = db.scalar(select(PlatformCourse).where(PlatformCourse.code == code))
    if not course:
        raise HTTPException(status_code=404, detail="course_not_found")
    assignments = sorted(course.assignments, key=lambda a: a.due_at)
    return templates.TemplateResponse(
        request,
        "course_detail.html",
        {
            "course": course,
            "assignments": assignments,
            "now": datetime.utcnow(),
            "identity": identity,
        },
    )


@router.post("/courses/{code}/assignments/{assignment_id}/due-date")
def update_due_date(
    code: str,
    assignment_id: str,
    due_at: str = Form(...),
    db: Session = Depends(get_db),
    identity: dict = Depends(require_admin),
):
    assignment = db.get(PlatformAssignment, assignment_id)
    if not assignment or assignment.course.code != code:
        raise HTTPException(status_code=404, detail="assignment_not_found")
    try:
        assignment.due_at = datetime.strptime(due_at, "%Y-%m-%d")
    except ValueError as exc:
        raise HTTPException(status_code=400, detail="invalid_due_at_format") from exc
    assignment.updated_at = datetime.utcnow()
    db.commit()
    return RedirectResponse(url=f"/courses/{code}", status_code=303)
