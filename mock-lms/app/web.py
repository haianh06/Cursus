from __future__ import annotations

from datetime import datetime
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import FileResponse, RedirectResponse
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db import get_db
from app.models import PlatformAssignment, PlatformCourse
from app.sso import (
    SESSION_COOKIE_NAME,
    decode_state,
    exchange_code,
    require_admin,
    require_admin_json,
    require_identity,
    require_identity_json,
    _sign_session,
    STATE_COOKIE_NAME,
)

router = APIRouter(tags=["web"])

# Built by `npm run build` in frontend/ (vite.config.ts outDir) — see
# frontend/README or the main mock-lms/README.md "Web UI" section.
_FRONTEND_DIST = Path(__file__).resolve().parent / "static" / "dist"


def _serialize_assignment(a: PlatformAssignment) -> dict:
    return {
        "id": a.id,
        "name": a.name,
        "description": a.description,
        "dueAt": a.due_at.isoformat(),
        "pointsPossible": a.points_possible,
        "updatedAt": a.updated_at.isoformat(),
        "isPastDue": a.due_at < datetime.utcnow(),
    }


def _serialize_course_detail(course: PlatformCourse) -> dict:
    assignments = sorted(course.assignments, key=lambda a: a.due_at)
    return {
        "code": course.code,
        "name": course.name,
        "semester": course.semester,
        "credit": course.credit,
        "assignments": [_serialize_assignment(a) for a in assignments],
    }


@router.get("/")
def root():
    return RedirectResponse(url="/courses")


@router.get("/sso/refresh")
def sso_refresh(next: str = "/courses"):
    """Entry point for every link INTO Mock LMS from Cursus (Topbar, Admin
    Console) — always clears any cached mock_lms_session first, then lands
    on `next`, which re-triggers the full SSO handshake there (see
    require_identity below) against whichever Cursus account/demo role is
    *currently* logged in.

    Without this, clicking straight into /courses trusts a cached session
    cookie for up to SESSION_TTL_SECONDS even after the visitor switched to
    a different Cursus account (e.g. the demo role switcher) in the same
    browser -- two different origins, so Cursus has no way to clear this
    app's cookie itself when that happens. Mock LMS is explicitly a
    low-traffic demo tool (see README), so paying one extra redirect round
    trip on every entry click to always be correct is the right trade-off
    here, not a cached-then-occasionally-stale session.
    """
    # `next` is caller-supplied (Cursus's Topbar link) -- restrict to an
    # in-app relative path so this can't be turned into an open redirect.
    safe_next = next if next.startswith("/") and not next.startswith("//") else "/courses"
    response = RedirectResponse(url=safe_next)
    response.delete_cookie(SESSION_COOKIE_NAME)
    return response


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


# ── Page routes — gate on SSO identity, then hand off to the React SPA ──────
# Every route below serves the *same* built index.html; the SPA itself reads
# window.location.pathname (see frontend/src/App.tsx) to decide what to
# render, and fetches real data from the /web-api/* routes further down.
# Keeping the gate here (not client-side) means an unauthenticated visitor
# never even receives the app shell, matching the old Jinja templates'
# behavior exactly.
#
# `/courses` is the FLM-style landing hub (features dashboard); everything
# else the SPA can navigate to (curriculum browser, prerequisite map,
# syllabus search/details, the assignment/due-date list) lives under
# `/courses/...` and is caught by the `{rest:path}` route below rather than
# enumerating each screen's path here twice (once in FastAPI, once in the
# SPA's own router in frontend/src/App.tsx).


def _serve_spa_shell() -> FileResponse:
    index_html = _FRONTEND_DIST / "index.html"
    if not index_html.exists():
        # Distinct from a build serving a stale/missing asset (app/main.py's
        # StaticFiles mount 404s that case per-request) -- this is "nobody
        # has ever run the build", a one-time dev setup step, not a runtime
        # error. Says so plainly instead of a bare 500 with a stack trace.
        raise HTTPException(
            status_code=503,
            detail=(
                "Frontend not built yet. Run: cd mock-lms/frontend && "
                "npm install && npm run build -- see mock-lms/README.md."
            ),
        )
    response = FileResponse(index_html)
    response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
    response.headers["Pragma"] = "no-cache"
    response.headers["Expires"] = "0"
    return response


@router.get("/courses")
def courses_page(identity: dict = Depends(require_identity)):
    return _serve_spa_shell()


@router.get("/courses/{rest:path}")
def courses_subpage(rest: str, identity: dict = Depends(require_identity)):
    return _serve_spa_shell()


# ── JSON API for the SPA — session-cookie authenticated, distinct from the
# OAuth-bearer-token /api/v1/* routes in app/platform_api.py that Cursus's backend
# calls. Never used by Cursus itself. ───────────────────────────────────────

web_api_router = APIRouter(prefix="/web-api", tags=["web-api"])


@web_api_router.get("/me")
def get_me(identity: dict = Depends(require_identity_json)):
    return {
        "userId": identity["user_id"],
        "role": identity["role"],
        "name": identity["name"],
        "email": identity["email"],
    }


@web_api_router.get("/courses")
def list_courses_web(
    db: Session = Depends(get_db),
    _identity: dict = Depends(require_identity_json),
):
    courses = db.scalars(select(PlatformCourse).order_by(PlatformCourse.code)).all()
    return [
        {
            "code": c.code,
            "name": c.name,
            "semester": c.semester,
            "credit": c.credit,
            "assignmentCount": len(c.assignments),
        }
        for c in courses
    ]


@web_api_router.get("/courses/{code}")
def get_course_web(
    code: str,
    db: Session = Depends(get_db),
    _identity: dict = Depends(require_identity_json),
):
    course = db.scalar(select(PlatformCourse).where(PlatformCourse.code == code))
    if not course:
        raise HTTPException(status_code=404, detail="course_not_found")
    return _serialize_course_detail(course)


class UpdateDueDateBody(BaseModel):
    due_at: str  # "YYYY-MM-DD"


@web_api_router.post("/courses/{code}/assignments/{assignment_id}/due-date")
def update_due_date_web(
    code: str,
    assignment_id: str,
    body: UpdateDueDateBody,
    db: Session = Depends(get_db),
    _identity: dict = Depends(require_admin_json),
):
    assignment = db.get(PlatformAssignment, assignment_id)
    if not assignment or assignment.course.code != code:
        raise HTTPException(status_code=404, detail="assignment_not_found")
    try:
        assignment.due_at = datetime.strptime(body.due_at, "%Y-%m-%d")
    except ValueError as exc:
        raise HTTPException(status_code=400, detail="invalid_due_at_format") from exc
    assignment.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(assignment)
    return _serialize_course_detail(assignment.course)
