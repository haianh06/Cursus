# `GET /api/v1/audit/events` returns audit events across ALL organizations

- **Status:** ✅ FULLY RESOLVED 22/08, late that same night — code/migration/tests done, AND the user ran `scripts/sql/add_audit_log_org_scoping_22aug.sql` on the Supabase Dashboard themselves. Verified via the script's own CHECK queries: 420/446 rows now have `organization_id`; the remaining 26 are all `LOGIN_FAILED` with a NULL actor (anonymous failed logins — correctly excluded from every org's view, not a bug); 0 Admin accounts lack an organization. Live re-verification after: all 3 roles log in with zero 500s, Admin Console Audit Log tab shows real, correctly-scoped data. Full writeup: `docs/PENDING_DECISIONS.md` #2. Evidence: `docs/evidence/screenshots/2026-08-22_late-night-verification/`.
- **Related finding surfaced while verifying this fix:** running with the column still missing meant `AuditService.log_event(commit=True)` crashed with a 500 on ANY caller, including `POST /auth/login` — not just the Audit Log tab showing wrong data, but every login on the real Supabase dev DB failing outright. Fixed independently of the SQL: `AuditRepository.add()` now catches a `commit=True` write failure, rolls back, and logs it instead of raising, so an audit-trail write failure can never take down a primary flow again (see the commit message on that fix, and `docs/PENDING_DECISIONS.md` #2 for the full story).
- **Found by:** investigation while building the Admin Console Audit Log UI (mục 6.5), reading `src/api/audit.py` to know what fields/filters to build the frontend against.
- **Severity:** Low-Medium. Not student grades/chat content, but it's a real cross-tenant leak: login failures, guardrail overrides, risk-policy/Mock-LMS publishes, and any other audited action are visible to any ADMIN of any organization, not just their own. Every other `/admin/*` endpoint in this codebase (courses, kpi, invites, users) is carefully scoped to `current_user.organization_id` — this one is the outlier.

## Root cause

`AuditLog` (`src/db/models.py:224-239`) has no `organization_id` column at all. `GET /audit/events` (`src/api/audit.py:26-38`) filters only by `event_type`/`actor_user_id`/`limit` — there is no organization dimension to filter by even if the route wanted to. `AuditRepository`/`AuditService` (used by every `audit_service.log_event(...)` call site across the codebase) never receives or stores an org id either.

## Why not fixed tonight

Fixing this properly means: adding `organization_id` to `AuditLog`, a migration, backfilling existing rows (many have no obvious org — e.g. failed logins for an email that was never a valid account), and updating every `audit_service.log_event(...)` call site to pass it. That is a schema/architecture decision, explicitly out of scope for this session's guardrails (no new DB schema decisions without the user's sign-off; no touching the Supabase dev DB, whose migration chain is already diverged). See `docs/PENDING_DECISIONS.md` #2 for the options.

## What shipped anyway

The Admin Console "Audit Log" tab (this same commit) was still built against the existing endpoint as asked — the API already exposes this data today with or without a frontend for it, so not building the UI would not have closed the gap, only delayed a requested feature. The tab has no special handling for this issue; it shows exactly what the API returns.
