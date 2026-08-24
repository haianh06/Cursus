from __future__ import annotations

from fastapi import FastAPI, Request

from app import models  # noqa: F401  -- registers tables on Base.metadata
from app.api import router as api_router
from app.db import Base, ENGINE
from app.oauth import router as oauth_router
from app.sso import _NeedsLogin, build_authorize_redirect
from app.web import router as web_router

app = FastAPI(title="Mock LMS")


@app.on_event("startup")
def _ensure_schema() -> None:
    Base.metadata.create_all(bind=ENGINE)


@app.get("/health")
def health():
    return {"status": "ok"}


@app.exception_handler(_NeedsLogin)
def _needs_login_handler(request: Request, exc: _NeedsLogin):
    return build_authorize_redirect(exc.return_to)


app.include_router(web_router)
app.include_router(oauth_router)
app.include_router(api_router)
