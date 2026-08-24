-- Fix: audit_logs has no organization column at all -- any ADMIN can read
-- every other organization's audit log (docs/PENDING_DECISIONS.md #2,
-- mục 9 ý2 of PROJECT_CONTEXT.md, found 22/08 while building the Audit log
-- tab, escalated then, fixed now).
--
-- WHAT THIS FIXES: `GET /api/v1/audit/events` (the Admin Console "Audit log"
-- tab) currently returns every organization's history mixed together,
-- because the underlying table has no way to tell them apart. The backend
-- code that reads this table (src/api/audit.py, src/repositories/
-- audit_repository.py) has already been updated to filter by organization
-- -- but that filter has nothing to filter ON until this column exists.
--
-- WHAT THIS SCRIPT DOES:
--   1. Adds a nullable `organization_id` column to `audit_logs`
--      (nullable on purpose -- some rows, like an audit log written before
--      an actor's account existed, may never resolve to an org).
--   2. Backfills every existing row from its actor's *current* organization
--      (best-effort: if a user has since moved to a different org, old
--      events attributed to them backfill to their org *today*, not
--      whatever org they were in when the event actually happened -- there
--      is no way to recover the true historical org from data this table
--      never stored).
--   3. Adds an index on the new column (every read of this table will now
--      filter by it).
--
-- This does NOT touch `alembic_version` (same already-known, separate
-- problem as every other script in this folder -- see PROJECT_CONTEXT.md
-- mục 9 ý8). Safe to run more than once: step 1 checks "does this column
-- already exist?" first, step 2 only fills rows that are still NULL.
--
-- ============================================================================
-- HOW TO RUN THIS (step by step, no SQL knowledge assumed):
--   1. Open https://supabase.com/dashboard and select this project.
--   2. In the left sidebar, click "SQL Editor".
--   3. Click "+ New query".
--   4. Copy this ENTIRE file's contents and paste them into the editor.
--   5. Click "Run" (or press Ctrl+Enter).
--   6. You should see "Success. No rows returned" (or similar) at the
--      bottom. If you see a red error message instead, stop and share the
--      exact error text before doing anything else (do not re-run blindly).
--   7. To confirm the fix worked: run the 2 CHECK queries at the very
--      bottom of this file (select them and click "Run" on just that
--      selection) -- the first should show a number greater than 0 rows
--      now have an organization_id; the second should show 0 (no admin
--      account currently lacks an organization, so nobody should be
--      getting a 404 from the new fail-closed check in src/api/audit.py).
--   8. Reload the Cursus app, log in as an Admin from one organization, and
--      confirm the Audit log tab no longer shows another organization's
--      events (e.g. logins from student_ethan/inst_demo, if those belong
--      to a different org than the one you're testing with).
-- ============================================================================


-- 1) Add the column (skips silently if it already exists).
ALTER TABLE audit_logs
    ADD COLUMN IF NOT EXISTS organization_id VARCHAR REFERENCES organizations(id) ON DELETE CASCADE;

-- 2) Backfill from each row's actor's current organization. Rows with no
--    actor_user_id (system events) or whose actor no longer exists stay
--    NULL -- fine, they are excluded from every organization's view rather
--    than shown to everyone (fail closed, matches the code's own default).
UPDATE audit_logs
SET organization_id = users.organization_id
FROM users
WHERE audit_logs.actor_user_id = users.id
  AND audit_logs.organization_id IS NULL
  AND users.organization_id IS NOT NULL;

-- 3) Index -- every read of this table filters by this column now.
CREATE INDEX IF NOT EXISTS ix_audit_logs_organization_id ON audit_logs (organization_id);


-- ============================================================================
-- CHECK 1 -- how many rows got an organization_id after the backfill
-- (compare against the total row count to see how many stayed NULL).
-- ============================================================================
-- SELECT
--     count(*) FILTER (WHERE organization_id IS NOT NULL) AS with_org,
--     count(*) FILTER (WHERE organization_id IS NULL) AS still_null,
--     count(*) AS total
-- FROM audit_logs;

-- ============================================================================
-- CHECK 2 -- any ADMIN account with no organization would now get a 404
-- from the Audit log tab (fail-closed check in src/api/audit.py) instead of
-- silently seeing every organization's data. This should return 0 rows.
-- ============================================================================
-- SELECT id, email FROM users WHERE role = 'ADMIN' AND organization_id IS NULL;
