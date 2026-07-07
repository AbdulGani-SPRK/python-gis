-- ============================================================
-- init-db/01_sessions.sql
-- Session table for wf_sub_memory_manager
-- Run once on first PostgreSQL startup
-- ============================================================

-- Enable required extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS postgis;

-- ─── SESSIONS TABLE ─────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS sessions (
    session_id  UUID PRIMARY KEY,
    channel     VARCHAR(50) NOT NULL DEFAULT 'web',
    state       JSONB       NOT NULL DEFAULT '{}',
    created_at  TIMESTAMPTZ          DEFAULT NOW(),
    updated_at  TIMESTAMPTZ          DEFAULT NOW(),
    expires_at  TIMESTAMPTZ          DEFAULT (NOW() + INTERVAL '2 hours')
);

-- Indexes for session lookup and expiry cleanup
CREATE INDEX IF NOT EXISTS idx_sessions_expires_at
    ON sessions (expires_at);

CREATE INDEX IF NOT EXISTS idx_sessions_channel
    ON sessions (channel);

-- Auto-update updated_at on any row change
CREATE OR REPLACE FUNCTION touch_updated_at()
RETURNS TRIGGER LANGUAGE plpgsql AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$;

DROP TRIGGER IF EXISTS trg_sessions_updated_at ON sessions;
CREATE TRIGGER trg_sessions_updated_at
    BEFORE UPDATE ON sessions
    FOR EACH ROW EXECUTE FUNCTION touch_updated_at();

-- ─── WORKFLOW LOGS TABLE ─────────────────────────────────────────
CREATE TABLE IF NOT EXISTS workflow_logs (
    id            BIGSERIAL    PRIMARY KEY,
    session_id    UUID,
    workflow_name VARCHAR(100),
    node_name     VARCHAR(100),
    event_type    VARCHAR(50),
    payload       JSONB,
    duration_ms   INTEGER,
    status        VARCHAR(20)  DEFAULT 'success',
    created_at    TIMESTAMPTZ  DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_wf_logs_session_id
    ON workflow_logs (session_id);

CREATE INDEX IF NOT EXISTS idx_wf_logs_created_at
    ON workflow_logs (created_at DESC);

CREATE INDEX IF NOT EXISTS idx_wf_logs_workflow_name
    ON workflow_logs (workflow_name);

-- ─── QUICK SANITY CHECK ──────────────────────────────────────────
DO $$
BEGIN
    RAISE NOTICE 'Sessions table ready: %', (SELECT COUNT(*) FROM sessions);
    RAISE NOTICE 'Workflow logs table ready: %', (SELECT COUNT(*) FROM workflow_logs);
END;
$$;
