-- Migration: Create active_chat_sessions table
-- Date: 2025-11-12
-- Description: Table for tracking active /chat sessions in groups

-- Create active_chat_sessions table if it doesn't exist
CREATE TABLE IF NOT EXISTS active_chat_sessions (
    id SERIAL PRIMARY KEY,
    user_id BIGINT NOT NULL,
    chat_id BIGINT NOT NULL,
    personality VARCHAR(100) NOT NULL,
    started_at TIMESTAMP DEFAULT NOW(),
    last_activity TIMESTAMP DEFAULT NOW(),
    CONSTRAINT unique_user_chat UNIQUE(user_id, chat_id)
);

-- Create index for efficient session cleanup and queries
CREATE INDEX IF NOT EXISTS idx_sessions_activity
ON active_chat_sessions(last_activity);

-- Create index for user lookups
CREATE INDEX IF NOT EXISTS idx_sessions_user_chat
ON active_chat_sessions(user_id, chat_id);

-- Add comment to table
COMMENT ON TABLE active_chat_sessions IS 'Tracks active /chat sessions in group chats';
COMMENT ON COLUMN active_chat_sessions.user_id IS 'Telegram user ID who started the session';
COMMENT ON COLUMN active_chat_sessions.chat_id IS 'Telegram chat ID where session is active';
COMMENT ON COLUMN active_chat_sessions.personality IS 'Personality name used in this session';
COMMENT ON COLUMN active_chat_sessions.started_at IS 'When the session was started';
COMMENT ON COLUMN active_chat_sessions.last_activity IS 'Last time user interacted in this session';

-- Create function to auto-cleanup old sessions
CREATE OR REPLACE FUNCTION cleanup_inactive_sessions(timeout_minutes INTEGER DEFAULT 15)
RETURNS INTEGER AS $$
DECLARE
    deleted_count INTEGER;
BEGIN
    DELETE FROM active_chat_sessions
    WHERE last_activity < NOW() - (timeout_minutes || ' minutes')::INTERVAL;

    GET DIAGNOSTICS deleted_count = ROW_COUNT;

    RETURN deleted_count;
END;
$$ LANGUAGE plpgsql;

-- Create function to update session activity
CREATE OR REPLACE FUNCTION update_session_activity(p_user_id BIGINT, p_chat_id BIGINT)
RETURNS BOOLEAN AS $$
BEGIN
    UPDATE active_chat_sessions
    SET last_activity = NOW()
    WHERE user_id = p_user_id AND chat_id = p_chat_id;

    RETURN FOUND;
END;
$$ LANGUAGE plpgsql;

-- Verify migration
DO $$
BEGIN
    IF EXISTS (
        SELECT 1 FROM information_schema.tables
        WHERE table_name = 'active_chat_sessions'
    ) THEN
        RAISE NOTICE 'active_chat_sessions table created successfully';
    ELSE
        RAISE EXCEPTION 'Failed to create active_chat_sessions table';
    END IF;
END $$;
