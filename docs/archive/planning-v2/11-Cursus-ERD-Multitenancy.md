# 11 — Cursus ERD & Multi-tenancy (RLS)

Status: **Implemented** (2026-08-12). Companion to `10-Cursus-Auth-Onboarding-Sandbox-Spec.md`.

## 1. Why this exists

Cursus moved from a single implicit tenant (everything = FPT University) to a
tenant-aware data model with exactly two seeded organizations today
(`fpt-university` / production, `cursus-demo` / sandbox), no self-service org
creation, no org switcher. This doc records the schema, the migration/backfill
that was actually run, and — most importantly — a real finding about RLS
effectiveness in this deployment that should not get lost.

## 2. New/changed tables

```
organizations
  id, name, slug (unique), kind ('production'|'sandbox'), created_at

organization_memberships          -- explicit membership record (audit trail)
  id, user_id (FK users.id, unique today), organization_id (FK), role, created_at

org_invites                       -- the only way into the system besides provisioning
  id, organization_id (FK), email, full_name, role, invited_by_user_id (FK users.id, nullable),
  token_hash (unique), expires_at, used_at, revoked_at, created_at

access_requests                   -- public lead-gen form, no auth
  id, institution_name, contact_name, email, role_interested, message, created_at

users            + organization_id (FK organizations.id, NOT NULL — live DB)
courses          + organization_id (FK organizations.id, NOT NULL — live DB)
programs         + organization_id (FK organizations.id, NOT NULL — live DB)
curriculum_versions + organization_id (FK organizations.id, NOT NULL — live DB)
```

> **ORM vs. DB note:** the migration sets all 4 columns `NOT NULL` in Postgres.
> `src/db/models.py` intentionally keeps the SQLAlchemy declarations
> (`Mapped[str | None]`, `nullable=True`) looser than that, so the test
> suite's SQLite schema (built from these same ORM classes via
> `Base.metadata.create_all`) doesn't reject the many existing test fixtures
> that create `User`/`Course` rows without an org — rewriting all of those
> fixtures was out of scope for this pass. Every real code path that creates
> these rows (register, `provision_organization.py`, `seed_demo_accounts.py`)
> always sets `organization_id` regardless of what the ORM permits.

`course_sections`, `enrollments`, `assignments`, `weekly_plans`,
`weekly_reflections`, `risk_signals`, and the rest of the ~45 other tables
**did not** get a new column. They reach organization scoping transitively
through their existing FK to `courses` or `users` (e.g.
`course_sections.course_id → courses.organization_id`,
`enrollments.student_id → users.organization_id`). Adding `organization_id`
to all ~45 tables was deliberately out of scope — every real leakage path
(a course, a section, a user, an invite) is closed through these 4 root
tables; the rest inherit correctness through their existing FKs and would
be redundant denormalization for no additional protection.

```
organizations 1───* users
organizations 1───* organization_memberships ──1 users
organizations 1───* org_invites
organizations 1───* courses ──* course_sections ──* enrollments ──1 users(student)
organizations 1───* programs
organizations 1───* curriculum_versions ──* courses
```

## 3. Migration that was run

`migrations/versions/20260812_organizations_and_tenancy.py`, against the real
Supabase Postgres DB, additive-only:

1. Created the 4 new tables.
2. Added `organization_id` as **nullable** on the 4 root tables.
3. Seeded exactly 2 rows in `organizations`.
4. Backfilled every pre-existing row (11 users, 4 courses, 1 program, 1
   curriculum version at migration time) into `fpt-university` — safe,
   because 100% of existing data genuinely belonged to that one institution.
5. Backfilled one `organization_memberships` row per pre-existing user.
6. Verified zero remaining NULLs, then set `organization_id NOT NULL` on all 4.
7. Enabled RLS and created a same-shaped policy on each of the 4 tables:
   ```sql
   ALTER TABLE <table> ENABLE ROW LEVEL SECURITY;
   CREATE POLICY org_isolation_<table> ON <table>
     USING (organization_id = current_setting('app.current_org_id', true));
   ```

`downgrade()` is symmetric: drops the policies, the NOT NULL constraints, the
4 columns, and the 4 new tables. **No row in any pre-existing table is ever
deleted** by either direction of this migration.

`cursus-demo` was then populated via `provision_organization.py cursus-demo
"Cursus Demo University" sandbox --admin-email demo.admin@cursusdemo.local
--admin-name "Demo Admin"`, which also seeds `demo.student@cursusdemo.local`
and `demo.instructor@cursusdemo.local` — the 3 accounts
`POST /auth/demo-session` logs a visitor into.

## 4. ⚠️ RLS effectiveness finding — read before relying on this

The app's `DATABASE_URL` connects to Postgres as the `postgres` role (Supabase
pooler connection string). Verified directly:

```sql
SELECT rolname, rolsuper, rolbypassrls FROM pg_roles WHERE rolname = current_user;
-- ('postgres', false, true)
```

`rolbypassrls = true` means **Postgres skips RLS policy evaluation entirely**
for every query this connection makes — the policies created in step 7 above
are syntactically correct and will activate for free the moment the
connection uses a non-bypassing role, but **today they enforce nothing**.

**The real, currently-active enforcement boundary is application-layer
`organization_id` filtering**, exercised by:
- `OrgInviteRepository.list_for_org(organization_id)` / `AdminConsole`'s
  Invites tab — an admin only ever sees/revokes their own org's invites
  (tested: `tests/test_security/test_tenant_isolation.py::test_admin_cannot_list_another_orgs_invites`,
  `::test_admin_cannot_revoke_another_orgs_invite`).
- `AuthService.register` assigning `organization_id` from the invite record,
  never from client input (tested:
  `::test_register_assigns_organization_from_invite_not_client`).
- `POST /auth/demo-session` only ever authenticating the 3 accounts inside
  `cursus-demo`, looked up by fixed, hardcoded email — there is no code path
  where a demo session could resolve to a `fpt-university` user.

**Known gap, not yet closed:** existing student/instructor data endpoints
(courses, enrollments, plans, dashboards) are **not yet org-filtered** at the
application layer either — they were single-tenant by construction before
this pivot and haven't been touched. This is safe today only because there is
exactly one production tenant; it becomes a real gap the moment a second
production organization is provisioned. Tracked as a fast-follow, intentionally
not attempted in this pass per explicit scope guidance (protecting the
higher-priority eval/guardrail/HITL/monitoring workstreams from schedule risk).

**Recommended remediation (not done here — infra/ops change, out of scope for
a feature-dev pass):** provision a least-privilege Postgres role for the app
connection without `BYPASSRLS`, granting only the privileges the app actually
needs; rotate `DATABASE_URL` to use it. At that point the RLS policies already
in place become the real defense-in-depth layer they were written to be.

## 5. Test coverage

`tests/test_security/test_tenant_isolation.py`:
- Cross-org invite listing/revocation isolation (app-layer, real assertions).
- Registration assigns org from the invite, not the client.
- Repository-level unit test for `OrgInviteRepository.list_for_org`.
- A diagnostic test that asserts the BYPASSRLS finding on Postgres (skipped on
  the SQLite test DB, where the concept doesn't apply) — written as an
  `xfail` with the reason above, so if the connection role is ever fixed this
  test starts failing loudly (an `xfail` that unexpectedly passes) instead of
  the gap silently going unnoticed.
