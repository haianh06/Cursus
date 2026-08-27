-- Cursus Chat backend/ schema gap on this Supabase project, found 27/08 while
-- restoring cursus-backend after the src/ -> backend/ cutover (prod had been
-- down since ~16:00 that day due to an unrelated alembic multi-head crash,
-- fixed separately in docker_entrypoint.py). This DB's alembic_version
-- points at 20260906_llm_quota_events, which isn't an ancestor of
-- backend/migrations' chain -- same class of gap documented in
-- docs/PROJECT_CONTEXT.md mục 20 ý8, needs a human to reconcile
-- alembic_version by hand, not something this script touches.
--
-- Generated from a real diff: backend/src/db/models.py's SQLAlchemy metadata
-- vs. this exact live schema (via sqlalchemy.inspect), not hand-guessed.
-- Confirmed missing: 5 tables (all of Cursus Chat's own storage) + 7 columns
-- on tables that already existed under the old src/ codebase.
--
-- Does NOT touch: conversations/messages (the OLD "Cursus Assistant" tables,
-- superseded by Cursus Chat per explicit product decision 27/08 -- left
-- alone here since backend/'s migrations already has a
-- 20260910_remove_chatbot_feature migration to drop them properly; this
-- script only adds what's missing, never drops).
--
-- Safe to run more than once (every statement checks "does this already
-- exist?" first).
--
-- HOW TO RUN: Supabase Dashboard -> project 'cursus' -> SQL Editor ->
-- New query -> paste this whole file -> Run.
-- ============================================================================


-- chat_conversations
CREATE TABLE IF NOT EXISTS chat_conversations (
    id VARCHAR NOT NULL,
    student_id VARCHAR NOT NULL,
    created_at TIMESTAMP WITHOUT TIME ZONE NOT NULL,
    updated_at TIMESTAMP WITHOUT TIME ZONE NOT NULL,
    expires_at TIMESTAMP WITHOUT TIME ZONE NOT NULL,
    PRIMARY KEY (id),
    FOREIGN KEY(student_id) REFERENCES users (id) ON DELETE CASCADE
);
CREATE INDEX IF NOT EXISTS ix_chat_conversations_student_id ON chat_conversations (student_id);
CREATE INDEX IF NOT EXISTS ix_chat_conversations_expires_at ON chat_conversations (expires_at);


-- chat_messages
CREATE TABLE IF NOT EXISTS chat_messages (
    id VARCHAR NOT NULL,
    conversation_id VARCHAR NOT NULL,
    role VARCHAR NOT NULL,
    content TEXT NOT NULL,
    metadata_info JSON NOT NULL,
    created_at TIMESTAMP WITHOUT TIME ZONE NOT NULL,
    PRIMARY KEY (id),
    FOREIGN KEY(conversation_id) REFERENCES chat_conversations (id) ON DELETE CASCADE
);
CREATE INDEX IF NOT EXISTS ix_chat_messages_conversation_id ON chat_messages (conversation_id);


-- chat_briefing_impressions
CREATE TABLE IF NOT EXISTS chat_briefing_impressions (
    id VARCHAR NOT NULL,
    student_id VARCHAR NOT NULL,
    briefing_key VARCHAR NOT NULL,
    shown_at TIMESTAMP WITHOUT TIME ZONE NOT NULL,
    PRIMARY KEY (id),
    FOREIGN KEY(student_id) REFERENCES users (id) ON DELETE CASCADE
);
CREATE INDEX IF NOT EXISTS ix_chat_briefing_impressions_student_id ON chat_briefing_impressions (student_id);


-- chat_action_proposals
CREATE TABLE IF NOT EXISTS chat_action_proposals (
    id VARCHAR NOT NULL,
    student_id VARCHAR NOT NULL,
    action_type VARCHAR NOT NULL,
    payload JSON NOT NULL,
    status VARCHAR NOT NULL,
    expires_at TIMESTAMP WITHOUT TIME ZONE NOT NULL,
    PRIMARY KEY (id),
    FOREIGN KEY(student_id) REFERENCES users (id) ON DELETE CASCADE
);
CREATE INDEX IF NOT EXISTS ix_chat_action_proposals_student_id ON chat_action_proposals (student_id);
CREATE INDEX IF NOT EXISTS ix_chat_action_proposals_expires_at ON chat_action_proposals (expires_at);


-- crisis_escalations
CREATE TABLE IF NOT EXISTS crisis_escalations (
    id VARCHAR NOT NULL,
    student_id VARCHAR NOT NULL,
    conversation_id VARCHAR,
    message_excerpt TEXT NOT NULL,
    status VARCHAR NOT NULL,
    created_at TIMESTAMP WITHOUT TIME ZONE NOT NULL,
    acknowledged_by VARCHAR,
    acknowledged_at TIMESTAMP WITHOUT TIME ZONE,
    resolution_note TEXT,
    PRIMARY KEY (id),
    FOREIGN KEY(student_id) REFERENCES users (id) ON DELETE CASCADE,
    FOREIGN KEY(conversation_id) REFERENCES chat_conversations (id) ON DELETE SET NULL,
    FOREIGN KEY(acknowledged_by) REFERENCES users (id) ON DELETE SET NULL
);
CREATE INDEX IF NOT EXISTS ix_crisis_escalations_created_at ON crisis_escalations (created_at);
CREATE INDEX IF NOT EXISTS ix_crisis_escalations_student_id ON crisis_escalations (student_id);


-- Columns missing on tables that already existed (carried over from the old
-- src/ codebase, added by migrations this DB never got a chance to apply).
ALTER TABLE org_invites
    ADD COLUMN IF NOT EXISTS delivery_status VARCHAR NOT NULL DEFAULT 'PENDING',
    ADD COLUMN IF NOT EXISTS resend_count INTEGER NOT NULL DEFAULT 0,
    ADD COLUMN IF NOT EXISTS last_sent_at TIMESTAMP;

ALTER TABLE documents
    ADD COLUMN IF NOT EXISTS previous_version_id VARCHAR;

ALTER TABLE admin_announcements
    ADD COLUMN IF NOT EXISTS organization_id VARCHAR;

ALTER TABLE guardrail_events
    ADD COLUMN IF NOT EXISTS student_id VARCHAR,
    ADD COLUMN IF NOT EXISTS section_id VARCHAR;
