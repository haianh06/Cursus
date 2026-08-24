-- Sync the Supabase 'cursus' project (ref pufmbwclcvcbcxxbwbeb) schema up to
-- the current migration HEAD (20260904_guardrail_policy_ver), for the
-- Vercel+Render+Supabase deploy.
--
-- WHY THIS EXISTS: this DB's `alembic_version` points at a revision
-- ('20260821_self_study_sessions') that does not exist in this branch's
-- migration chain (see docs/PROJECT_CONTEXT.md mục 20 ý8/mục 9 ý8 for the full
-- history of this known, already-investigated gap). `alembic upgrade head`
-- cannot run against this DB until that is reconciled by hand in the
-- Dashboard -- so, following the exact same pattern already used in this repo
-- (scripts/sql/fix_missing_tables_22aug.sql, add_audit_log_org_scoping_22aug.sql),
-- this script recreates -- as plain, idempotent SQL -- everything that
-- migrations 20260826 through 20260904 would have added, without touching
-- `alembic_version` itself. Confirmed against a live diff (Alembic's
-- `compare_metadata` against this exact DB) on 2026-08-24: 6 tables + ~25
-- columns/indexes below were the actual gap; everything else already matched.
--
-- Deliberately NOT included here: a handful of index/constraint naming
-- differences and a few `nullable` flips the diff also reported (e.g. on
-- academic_terms/practice_sets/semester_* legacy indexes, and courses/
-- curriculum_versions/programs/users organization_id nullability). None of
-- those correspond to a missing feature or a known runtime error, unlike
-- everything below -- touching them blind on a DB with real user data is a
-- separate, lower-priority decision, not a blocker for this deploy.
--
-- Safe to run more than once (every step checks "does this already exist?").
--
-- HOW TO RUN: Supabase Dashboard -> project 'cursus' -> SQL Editor ->
-- New query -> paste this whole file -> Run.
-- ============================================================================


-- 20260826_data_requests.py + 20260902_data_request_org_scoping.py
CREATE TABLE IF NOT EXISTS data_requests (
    id VARCHAR PRIMARY KEY,
    requester_id VARCHAR NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    organization_id VARCHAR REFERENCES organizations(id),
    request_type VARCHAR NOT NULL,
    status VARCHAR NOT NULL,
    admin_notes TEXT,
    preview_summary JSON,
    preview_hash VARCHAR,
    result_summary JSON,
    processed_by VARCHAR REFERENCES users(id) ON DELETE SET NULL,
    created_at TIMESTAMP NOT NULL,
    updated_at TIMESTAMP NOT NULL
);
ALTER TABLE data_requests ADD COLUMN IF NOT EXISTS organization_id VARCHAR REFERENCES organizations(id);
UPDATE data_requests dr SET organization_id = u.organization_id
    FROM users u WHERE u.id = dr.requester_id AND dr.organization_id IS NULL;
CREATE INDEX IF NOT EXISTS ix_data_requests_organization_id ON data_requests (organization_id);


-- 20260827_documents_lifecycle.py
ALTER TABLE documents
    ADD COLUMN IF NOT EXISTS scope VARCHAR,
    ADD COLUMN IF NOT EXISTS publication_status VARCHAR,
    ADD COLUMN IF NOT EXISTS version_group VARCHAR,
    ADD COLUMN IF NOT EXISTS provenance JSON,
    ADD COLUMN IF NOT EXISTS checksum VARCHAR,
    ADD COLUMN IF NOT EXISTS validated_at TIMESTAMP,
    ADD COLUMN IF NOT EXISTS validated_by VARCHAR REFERENCES users(id) ON DELETE SET NULL,
    ADD COLUMN IF NOT EXISTS published_at TIMESTAMP,
    ADD COLUMN IF NOT EXISTS published_by VARCHAR REFERENCES users(id) ON DELETE SET NULL,
    ADD COLUMN IF NOT EXISTS archived_at TIMESTAMP,
    ADD COLUMN IF NOT EXISTS change_reason TEXT;
UPDATE documents SET scope = 'OFFICIAL', publication_status = 'PUBLISHED' WHERE scope IS NULL;


-- 20260827_instructor_note_and_guardrail_extras.py
ALTER TABLE risk_signals ADD COLUMN IF NOT EXISTS instructor_note TEXT;
ALTER TABLE guardrail_events
    ADD COLUMN IF NOT EXISTS created_at TIMESTAMP,
    ADD COLUMN IF NOT EXISTS reviewer_note TEXT;

-- src/db/models.py risk_signals.resolved_by -- no migration file ever added
-- this (a gap in the migration chain itself, independent of the
-- alembic_version issue); included here since it's a real model column.
ALTER TABLE risk_signals ADD COLUMN IF NOT EXISTS resolved_by VARCHAR REFERENCES users(id) ON DELETE SET NULL;


-- 20260828_student_profile_notes.py
CREATE TABLE IF NOT EXISTS instructor_student_notes (
    id VARCHAR PRIMARY KEY,
    instructor_id VARCHAR NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    student_id VARCHAR NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    content TEXT NOT NULL,
    created_at TIMESTAMP NOT NULL
);
CREATE INDEX IF NOT EXISTS ix_instructor_student_notes_instructor_id ON instructor_student_notes (instructor_id);
CREATE INDEX IF NOT EXISTS ix_instructor_student_notes_student_id ON instructor_student_notes (student_id);


-- 20260829_workflow_and_privacy_extras.py
ALTER TABLE users ADD COLUMN IF NOT EXISTS share_reflection_summary BOOLEAN NOT NULL DEFAULT FALSE;

CREATE TABLE IF NOT EXISTS practice_set_decisions (
    id VARCHAR PRIMARY KEY,
    set_id VARCHAR NOT NULL REFERENCES practice_sets(id) ON DELETE CASCADE,
    instructor_id VARCHAR NOT NULL REFERENCES users(id),
    decision VARCHAR NOT NULL,
    created_at TIMESTAMP NOT NULL
);
CREATE INDEX IF NOT EXISTS ix_practice_set_decisions_set_id ON practice_set_decisions (set_id);


-- 20260830_admin_announcements.py
CREATE TABLE IF NOT EXISTS admin_announcements (
    id VARCHAR PRIMARY KEY,
    title VARCHAR NOT NULL,
    content TEXT NOT NULL,
    created_by VARCHAR NOT NULL REFERENCES users(id),
    created_at TIMESTAMP NOT NULL
);


-- 20260831_class_activity_window.py
ALTER TABLE class_activities
    ADD COLUMN IF NOT EXISTS opens_at TIMESTAMP,
    ADD COLUMN IF NOT EXISTS closes_at TIMESTAMP;


-- 20260901_instructor_quizzes.py
ALTER TABLE quizzes
    ADD COLUMN IF NOT EXISTS created_by VARCHAR REFERENCES users(id),
    ADD COLUMN IF NOT EXISTS is_published BOOLEAN NOT NULL DEFAULT FALSE,
    ADD COLUMN IF NOT EXISTS opens_at TIMESTAMP;
ALTER TABLE quizzes ALTER COLUMN due_date DROP NOT NULL;
ALTER TABLE quiz_questions ADD COLUMN IF NOT EXISTS order_index INTEGER NOT NULL DEFAULT 0;


-- 20260902_student_role_restore.py (self_study_sessions already exists on
-- this DB per its alembic_version pointer -- only the 2 memory tables +
-- schedule_blocks column are actually missing here)
CREATE TABLE IF NOT EXISTS student_memory_consent (
    student_id VARCHAR PRIMARY KEY REFERENCES users(id),
    granted BOOLEAN NOT NULL DEFAULT FALSE,
    updated_at TIMESTAMP NOT NULL
);
CREATE TABLE IF NOT EXISTS student_memory_entries (
    id VARCHAR PRIMARY KEY,
    student_id VARCHAR NOT NULL REFERENCES users(id),
    subject_code VARCHAR,
    kind VARCHAR NOT NULL,
    content VARCHAR NOT NULL,
    source_conversation_id VARCHAR REFERENCES conversations(id),
    reinforce_count INTEGER NOT NULL DEFAULT 1,
    created_at TIMESTAMP NOT NULL,
    last_reinforced_at TIMESTAMP NOT NULL
);
CREATE INDEX IF NOT EXISTS ix_student_memory_entries_student_id ON student_memory_entries (student_id);
CREATE INDEX IF NOT EXISTS ix_student_memory_entries_subject_code ON student_memory_entries (subject_code);

ALTER TABLE schedule_blocks ADD COLUMN IF NOT EXISTS recurrence_series_id VARCHAR;
CREATE INDEX IF NOT EXISTS ix_schedule_blocks_recurrence_series_id ON schedule_blocks (recurrence_series_id);


-- 20260904_guardrail_policy_versioning.py
CREATE TABLE IF NOT EXISTS guardrail_policy_versions (
    version VARCHAR PRIMARY KEY,
    rules_snapshot JSON NOT NULL,
    source_version VARCHAR,
    change_reason TEXT,
    is_active BOOLEAN NOT NULL DEFAULT FALSE,
    created_by VARCHAR REFERENCES users(id) ON DELETE SET NULL,
    created_at TIMESTAMP NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS ix_guardrail_policy_versions_is_active ON guardrail_policy_versions (is_active);

ALTER TABLE guardrail_rules
    ADD COLUMN IF NOT EXISTS core_locked BOOLEAN NOT NULL DEFAULT FALSE,
    ADD COLUMN IF NOT EXISTS current_version VARCHAR,
    ADD COLUMN IF NOT EXISTS change_reason TEXT;

UPDATE guardrail_rules SET core_locked = TRUE WHERE code = 'PROMPT_INJECTION';

INSERT INTO guardrail_policy_versions (version, rules_snapshot, source_version, change_reason, is_active, created_at)
SELECT
    'gpv1',
    (SELECT json_object_agg(code, enabled) FROM guardrail_rules),
    NULL,
    'Initial guardrail policy',
    TRUE,
    now()
WHERE NOT EXISTS (SELECT 1 FROM guardrail_policy_versions WHERE version = 'gpv1')
  AND EXISTS (SELECT 1 FROM guardrail_rules);

UPDATE guardrail_rules SET current_version = 'gpv1' WHERE current_version IS NULL
    AND EXISTS (SELECT 1 FROM guardrail_policy_versions WHERE version = 'gpv1');
