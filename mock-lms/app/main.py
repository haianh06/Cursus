from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles

from app import models  # noqa: F401  -- registers tables on Base.metadata
from app.curriculum_api import router as curriculum_router
from app.platform_api import router as api_router
from app.db import Base, ENGINE
from app.oauth import router as oauth_router
from app.sso import _NeedsLogin, build_authorize_redirect
from app.web import router as web_router, web_api_router

app = FastAPI(title="Mock LMS")

# Built by `cd frontend && npm run build` (see ../README.md). Assets are
# fingerprinted by Vite and referenced via base: '/static/dist/'
# (frontend/vite.config.ts), so this mount just needs to exist -- app/web.py
# serves index.html itself for the actual /courses* page routes.
#
# check_dir=False: a plain `if _STATIC_DIST.exists(): app.mount(...)` here
# would decide once, at import time, whether static files are servable at
# all -- and `npm run build`'s `emptyOutDir: true` deletes-then-recreates
# this directory, so a `uvicorn --reload` restart landing in that gap
# (dist/ momentarily missing mid-build) would skip the mount for the
# process's entire lifetime, 404-ing every asset until the *next* reload.
# check_dir=False makes the mount itself unconditional and per-request --
# it 404s a missing file instead of never existing as a route at all.
_STATIC_DIST = Path(__file__).resolve().parent / "static" / "dist"
app.mount(
    "/static/dist",
    StaticFiles(directory=_STATIC_DIST, check_dir=False),
    name="static-dist",
)


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
app.include_router(web_api_router)
app.include_router(curriculum_router)
app.include_router(oauth_router)
app.include_router(api_router)
