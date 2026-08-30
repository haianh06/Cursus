-- Schema gap found 28/08 while syncing 154 upstream commits (class
-- scheduling feature + ai_usage cost-tracking panel) into this Supabase
-- project. Generated from a real diff: backend/src/db/models.py's
-- SQLAlchemy metadata vs. this exact live schema (via sqlalchemy.inspect),
-- and the CREATE TABLE statements below are compiled straight from that
-- same metadata (sqlalchemy.schema.CreateTable), not hand-transcribed --
-- avoids the class of mistake a hand-guessed column list would make. Does
-- not touch alembic_version (same reasoning as every other script in this
-- directory -- see docs/PROJECT_CONTEXT.md mục 20 ý8).
--
-- Safe to run more than once (every statement checks "does this already
-- exist?" first).
--
-- HOW TO RUN: Supabase Dashboard -> project 'cursus' -> SQL Editor ->
-- New query -> paste this whole file -> Run.
-- ============================================================================

CREATE TABLE IF NOT EXISTS term_study_slots (
    id VARCHAR NOT NULL,
    organization_id VARCHAR NOT NULL,
    term_name VARCHAR NOT NULL,
    name VARCHAR NOT NULL,
    start_minute INTEGER NOT NULL,
    end_minute INTEGER NOT NULL,
    display_order INTEGER NOT NULL,
    is_active BOOLEAN NOT NULL,
    PRIMARY KEY (id),
    FOREIGN KEY(organization_id) REFERENCES organizations (id) ON DELETE CASCADE
);
CREATE INDEX IF NOT EXISTS ix_term_study_slots_organization_id ON term_study_slots (organization_id);
CREATE INDEX IF NOT EXISTS ix_term_study_slots_term_name ON term_study_slots (term_name);


CREATE TABLE IF NOT EXISTS fixed_class_schedules (
    id VARCHAR NOT NULL,
    section_id VARCHAR NOT NULL,
    slot_id VARCHAR NOT NULL,
    weekday INTEGER NOT NULL,
    start_minute INTEGER NOT NULL,
    end_minute INTEGER NOT NULL,
    room VARCHAR,
    note TEXT,
    effective_from DATE NOT NULL,
    effective_to DATE NOT NULL,
    created_by VARCHAR NOT NULL,
    created_at TIMESTAMP WITHOUT TIME ZONE NOT NULL,
    PRIMARY KEY (id),
    FOREIGN KEY(section_id) REFERENCES course_sections (id) ON DELETE CASCADE,
    FOREIGN KEY(slot_id) REFERENCES term_study_slots (id) ON DELETE RESTRICT,
    FOREIGN KEY(created_by) REFERENCES users (id)
);
CREATE INDEX IF NOT EXISTS ix_fixed_class_schedules_section_id ON fixed_class_schedules (section_id);


CREATE TABLE IF NOT EXISTS class_schedule_exceptions (
    id VARCHAR NOT NULL,
    schedule_id VARCHAR,
    section_id VARCHAR NOT NULL,
    kind VARCHAR NOT NULL,
    event_date DATE NOT NULL,
    start_minute INTEGER NOT NULL,
    end_minute INTEGER NOT NULL,
    room VARCHAR,
    note TEXT,
    reason TEXT NOT NULL,
    created_by VARCHAR NOT NULL,
    created_at TIMESTAMP WITHOUT TIME ZONE NOT NULL,
    PRIMARY KEY (id),
    FOREIGN KEY(schedule_id) REFERENCES fixed_class_schedules (id) ON DELETE CASCADE,
    FOREIGN KEY(section_id) REFERENCES course_sections (id) ON DELETE CASCADE,
    FOREIGN KEY(created_by) REFERENCES users (id)
);
CREATE INDEX IF NOT EXISTS ix_class_schedule_exceptions_section_id ON class_schedule_exceptions (section_id);
CREATE INDEX IF NOT EXISTS ix_class_schedule_exceptions_event_date ON class_schedule_exceptions (event_date);
CREATE INDEX IF NOT EXISTS ix_class_schedule_exceptions_schedule_id ON class_schedule_exceptions (schedule_id);


CREATE TABLE IF NOT EXISTS class_schedule_notifications (
    id VARCHAR NOT NULL,
    recipient_id VARCHAR NOT NULL,
    exception_id VARCHAR NOT NULL,
    title VARCHAR NOT NULL,
    body TEXT NOT NULL,
    read_at TIMESTAMP WITHOUT TIME ZONE,
    created_at TIMESTAMP WITHOUT TIME ZONE NOT NULL,
    PRIMARY KEY (id),
    FOREIGN KEY(recipient_id) REFERENCES users (id) ON DELETE CASCADE,
    FOREIGN KEY(exception_id) REFERENCES class_schedule_exceptions (id) ON DELETE CASCADE
);
CREATE INDEX IF NOT EXISTS ix_class_schedule_notifications_recipient_id ON class_schedule_notifications (recipient_id);
CREATE INDEX IF NOT EXISTS ix_class_schedule_notifications_exception_id ON class_schedule_notifications (exception_id);


CREATE TABLE IF NOT EXISTS ai_usage (
    id VARCHAR NOT NULL,
    created_at TIMESTAMP WITHOUT TIME ZONE NOT NULL,
    organization_id VARCHAR,
    user_id VARCHAR,
    feature VARCHAR NOT NULL,
    model VARCHAR NOT NULL,
    input_tokens INTEGER NOT NULL,
    output_tokens INTEGER NOT NULL,
    latency_ms INTEGER NOT NULL,
    success BOOLEAN NOT NULL,
    PRIMARY KEY (id)
);
CREATE INDEX IF NOT EXISTS ix_ai_usage_organization_id ON ai_usage (organization_id);
CREATE INDEX IF NOT EXISTS ix_ai_usage_created_at ON ai_usage (created_at);
CREATE INDEX IF NOT EXISTS ix_ai_usage_feature ON ai_usage (feature);


ALTER TABLE org_invites
    ADD COLUMN IF NOT EXISTS section_id VARCHAR;
