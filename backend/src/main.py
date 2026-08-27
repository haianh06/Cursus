import logging
from contextlib import asynccontextmanager

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.api.admin import academic_router as admin_academic_router
from src.api.admin import router as admin_router
from src.api.admin_data_requests import router as admin_data_requests_router
from src.api.admin_instructor360 import router as admin_instructor360_router
from src.api.admin_mock_lms import router as admin_mock_lms_router
from src.api.admin_overview import router as admin_overview_router
from src.api.admin_people import router as admin_people_router
from src.api.admin_risk_policy import router as admin_risk_policy_router
from src.api.admin_sections import router as admin_sections_router
from src.api.admin_settings import router as admin_settings_router
from src.api.admin_student360 import router as admin_student360_router
from src.api.audit import router as audit_router
from src.api.auth import router as auth_router
from src.api.cursus_chat import router as cursus_chat_router

# canvas_router import intentionally disabled — see include_router call below
# for why (PROJECT_CONTEXT.md mục 6.6/9).
# from src.api.canvas_routes import router as canvas_router
from src.api.demo import router as demo_router
from src.api.instructor import router as instructor_router
from src.api.lecture_plan import router as lecture_plan_router
from src.api.mock_lms_sso import router as mock_lms_sso_router
from src.api.plans import router as plans_router
from src.api.practice import instructor_router as practice_instructor_router
from src.api.practice import student_router as practice_student_router
from src.api.public import router as public_router
from src.api.qa import router as qa_router
from src.api.routes import router
from src.api.self_study import router as self_study_router
from src.api.semester import router as semester_router
from src.api.student import router as student_router
from src.api.student_quizzes import router as student_quizzes_router
from src.config import get_settings
from src.db.connection import SessionLocal
from src.security.exception_handlers import register_exception_handlers
from src.security.logging import configure_logging
from src.security.middleware import (
    CsrfProtectionMiddleware,
    RateLimitMiddleware,
    RequestContextMiddleware,
    SecurityHeadersMiddleware,
)
from src.services.core.retention_service import run_retention

logger = logging.getLogger(__name__)


def _run_retention_job() -> None:
    db = SessionLocal()
    try:
        result = run_retention(db)
        logger.info("retention_job_completed %s", result)
    except Exception:
        logger.exception("retention_job_failed")
        db.rollback()
    finally:
        db.close()


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("application_starting")
    # Cursus Chat's ChatConversation/ChatActionProposal/ChatBriefingImpression
    # rows are only swept lazily on request today (cursus_chat.py::_cleanup);
    # a student who never comes back would otherwise leave rows forever.
    scheduler = AsyncIOScheduler()
    scheduler.add_job(_run_retention_job, "interval", hours=1, id="cursus_chat_retention", next_run_time=None)
    scheduler.start()
    app.state.scheduler = scheduler
    yield
    scheduler.shutdown(wait=False)
    logger.info("application_stopping")


app = FastAPI(
    title="AI20K Agent",
    description="AI Agent built with LangGraph",
    version="1.0.0",
    lifespan=lifespan,
)

settings = get_settings()
configure_logging(settings)
register_exception_handlers(app, settings)
# Inner middleware first; CORS must be outermost so OPTIONS preflight
# never falls through to route handlers as 405 Method Not Allowed.
app.add_middleware(SecurityHeadersMiddleware)
app.add_middleware(CsrfProtectionMiddleware, settings=settings)
app.add_middleware(RateLimitMiddleware, settings=settings)
app.add_middleware(RequestContextMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[origin.strip() for origin in settings.cors_origins.split(",") if origin.strip()],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router, prefix="/api/v1")
app.include_router(audit_router, prefix="/api/v1")
app.include_router(auth_router, prefix="/api/v1")
app.include_router(student_router, prefix="/api/v1")
app.include_router(cursus_chat_router, prefix="/api/v1")
app.include_router(plans_router, prefix="/api/v1")
app.include_router(qa_router, prefix="/api/v1")
app.include_router(instructor_router, prefix="/api/v1")
# canvas_router disabled 2026-08-20 (Phase 2b security cleanup, branch
# cleanup/repo-audit-20260820): exposed real Cursus PII (emails, grades,
# submissions) via Canvas-shaped JSON, gated only by Cursus's own admin
# session — not OAuth, not a separate datastore, and nothing in this repo
# ever called it as a client. Does not meet PROJECT_CONTEXT.md mục 6.6's
# Mock LMS bar (separate app/service, own UI, REST+OAuth) — that bar was
# raised after this file was written under the older ADR-005 plan. File
# kept on disk as a field-mapping reference for whenever the real Mock LMS
# gets built; router intentionally not mounted until then.
# app.include_router(canvas_router, prefix="/api/v1")
app.include_router(admin_router, prefix="/api/v1")
app.include_router(mock_lms_sso_router, prefix="/api/v1")
app.include_router(admin_student360_router, prefix="/api/v1")
app.include_router(admin_instructor360_router, prefix="/api/v1")
app.include_router(admin_data_requests_router, prefix="/api/v1")
app.include_router(admin_academic_router, prefix="/api/v1")
app.include_router(admin_risk_policy_router, prefix="/api/v1")
app.include_router(admin_mock_lms_router, prefix="/api/v1")
app.include_router(admin_settings_router, prefix="/api/v1")
app.include_router(admin_overview_router, prefix="/api/v1")
app.include_router(admin_people_router, prefix="/api/v1")
app.include_router(admin_sections_router, prefix="/api/v1")
app.include_router(public_router, prefix="/api/v1")
app.include_router(demo_router, prefix="/api/v1")
app.include_router(semester_router, prefix="/api/v1")
app.include_router(self_study_router, prefix="/api/v1")
app.include_router(practice_student_router, prefix="/api/v1")
app.include_router(practice_instructor_router, prefix="/api/v1")
app.include_router(student_quizzes_router, prefix="/api/v1")
app.include_router(lecture_plan_router, prefix="/api/v1")


@app.get("/health")
async def health():
    # Keep the probe payload minimal in production (no env leak).
    if settings.app_env == "production":
        return {"status": "ok"}
    return {"status": "ok", "env": settings.app_env}
