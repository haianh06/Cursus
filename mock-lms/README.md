# Mock LMS

A standalone mock external LMS ("Platform" in LTI terms) used to demonstrate that Cursus
("Tool") integrates with a real external system over a real REST API + OAuth, not shared
data in Cursus's own database. See `docs/PROJECT_CONTEXT.md` mục 6.6 in the main repo for
the full spec this implements.

This app does not import anything from the main Cursus codebase (`src/`, `frontend/`). It
has its own database (SQLite file, `mock_lms.db`), its own OAuth signing key, and its own
minimal server-rendered UI.

## Quick start

```bash
cd mock-lms
pip install -r requirements.txt   # already satisfied if using the main repo's .venv
python scripts/seed_courses.py       # loads 36 real course codes from docs/planning/v2/data
python scripts/seed_assignments.py   # generates synthetic assignments/deadlines (see script docstring)
python scripts/seed_curriculum.py    # loads curriculum programs + prerequisite graph (generated
                                      # from the real catalog, see script docstring) and full
                                      # syllabus detail (CLOs/sessions/materials/questions/
                                      # assessments) for CSI106 + SWE202c
python scripts/seed_syllabi_from_chunks.py   # loads real CLOs + session plans for the other
                                              # 42 courses from docs/planning/v2/data/chunks_*.json
                                              # -- run this AFTER seed_curriculum.py (it skips
                                              # CSI106/SWE202c, which that script owns)
python scripts/create_oauth_client.py --name cursus --client-id cursus-tool   # prints a client_secret once

# Build the web UI once (or after changing anything in frontend/) --
# app/web.py serves the built output directly, there is no separate frontend server in prod.
cd frontend && npm install && npm run build && cd ..

uvicorn app.main:app --reload --reload-exclude "app/static/*" --port 9000
```

## Docker Compose

Từ thư mục gốc repository, `docker compose up --build -d` cũng build và chạy EduSync
như một service riêng (`edusync`). Service này tự build SPA, seed 36 course + 144
assignment + 44 syllabus, bootstrap OAuth client từ environment và lưu SQLite trong
Docker volume `edusync_data`. Backend Cursus gọi EduSync qua `http://edusync:9000`, còn
trình duyệt vẫn truy cập `http://localhost:9000`.

Trong chế độ Docker, SSO dùng hai URL có chủ đích: `CURSUS_BASE_URL=http://localhost:8000`
cho browser redirect và `CURSUS_INTERNAL_BASE_URL=http://backend:8000` cho server-to-server
code exchange. Không đổi `CURSUS_BASE_URL` thành hostname Docker vì browser không phân giải
được hostname nội bộ đó.

`--reload-exclude "app/static/*"` matters: without it, `--reload` also watches the frontend's
build output, and `npm run build`'s `emptyOutDir: true` deletes-then-recreates that directory --
a reload landing in that gap 404s every asset until you edit a `.py` file to trigger another
one. Excluding it means rebuilding the frontend never restarts the backend at all.

For frontend UI development with hot reload, run `cd frontend && npm run dev` (port 9001)
alongside `uvicorn` on port 9000 -- `frontend/vite.config.ts` proxies `/web-api` and `/sso` to
9000 so the dev server behaves the same as the production build.

Also make sure Cursus's own backend is running (`localhost:8000` by default) with
`MOCK_LMS_SSO_SHARED_SECRET` set to the same value as this app's own env var of the same
name -- see "Web UI auth" below, this is required now (no more standalone admin login).

Then:
- Browse `http://localhost:9000/courses` (banner + course list) and
  `http://localhost:9000/courses/<code>` (assignments, editable due dates) -- both require
  being logged into Cursus first (see "Web UI auth" below).
- `POST http://localhost:9000/oauth/token` with
  `grant_type=client_credentials&client_id=...&client_secret=...` to get a bearer token, then
  call `GET /api/v1/courses` / `GET /api/v1/courses/{code}/assignments` with
  `Authorization: Bearer <token>`.

## Web UI architecture

`frontend/` is a React + TypeScript + Vite app (Tailwind for styling) — it is a
**human-facing skin only**, not a second integration surface: it talks to this app's own
session-cookie-authenticated `/web-api/*` routes (`app/web.py`, `app/curriculum_api.py`), never
to Cursus directly, and Cursus never talks to it either. `app/main.py` mounts `frontend`'s build
output (`app/static/dist/`, gitignored, rebuild locally) as static files; `GET /courses` and
`GET /courses/<rest:path>` in `app/web.py` gate on the same SSO identity as before and then just
serve that build's `index.html` — the SPA does its own client-side routing (`frontend/src/App.tsx`)
between screens: a role-aware features hub, the curriculum program browser, the prerequisite
learning-path graph, syllabus search + detail (materials/CLOs/session plan/question bank/
assessment structure — real seeded rows, see `scripts/seed_curriculum.py`, not a second copy
of the OAuth API's course list), and the original assignment/due-date list+editor. The
OAuth-protected JSON API Cursus's backend actually calls (`GET /api/v1/courses`,
`GET /api/v1/courses/<code>/assignments` in `app/platform_api.py`) is completely separate and untouched
by any of this.

## Web UI auth

**[SỬA 23/08]** The single shared HTTP Basic Auth admin account (added 22/08) is gone.
`/courses` and `/courses/<code>` now identify the viewer via **Cursus's own login**, not a
parallel Mock LMS account -- a scoped, single-use code exchange (loosely OIDC-shaped, not
full LTI 1.3 launch, see `docs/PROJECT_CONTEXT.md` mục 6.6/15 for why that's still a separate
stretch goal):

1. Visiting any `/courses*` page without a valid Mock LMS session redirects the browser to
   Cursus's `GET /api/v1/auth/sso/mock-lms/authorize`.
2. If the browser has a valid Cursus login cookie, Cursus mints a short-lived (60s),
   single-use code and redirects back here to `/sso/callback`.
3. This app's backend calls Cursus's `POST /api/v1/auth/sso/mock-lms/token`
   **server-to-server** (never from the browser) with that code plus the shared secret
   below, gets back `{user_id, role, name, email}`, and issues its **own** session cookie
   (`mock_lms_session`, JWT signed with this app's own `MOCK_LMS_JWT_SECRET` -- never
   Cursus's signing key).
4. Not logged into Cursus at all -> a plain blocking page, no silent fallback to open access.

Role from that session controls what you can do:
- **STUDENT / INSTRUCTOR** -- view only (`/courses`, `/courses/<code>`).
- **ADMIN** -- view + edit due dates (the form `POST` route requires `role == ADMIN`).

Env vars (put these in **both** the main repo's `.env` and this app's own env, same value):
- `MOCK_LMS_SSO_SHARED_SECRET` -- proves the `/token` caller is really this app's server, not
  a random client guessing codes. Not a user password.
- `CURSUS_BASE_URL` (this app's env, default `http://localhost:8000`) -- where to send/exchange
  codes. **Must be `localhost`, not `127.0.0.1`** -- Cursus's frontend logs in via
  `localhost:8000` (see `frontend/.env` `VITE_API_URL`), so its session cookie is scoped to
  that exact host; the browser will not send it to a `127.0.0.1` request even on the same
  machine, which just silently looks like "not logged in".
- `MOCK_LMS_PUBLIC_URL` (this app's env, default `http://localhost:9000`) -- this app's own
  callback URL, must be in Cursus's `MOCK_LMS_SSO_ALLOWED_REDIRECT_PREFIXES`.

The OAuth-protected JSON API (`/api/v1/courses`, `/api/v1/courses/<code>/assignments`) is
unaffected -- it already required a Bearer token and is what Cursus's own
`src/integrations/mock_lms_client.py` calls, never the web UI, and none of the SSO code above
touches it.

## Why SQLite

Per the approved plan, a separate SQLite file is the cheapest way to satisfy "own datastore,
genuinely separate from Cursus's Postgres" for this scope. Swappable for Postgres later
without changing the SQLAlchemy models if the course later needs it.
