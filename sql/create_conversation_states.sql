-- Conversation states table for persistent ConversationHandler
-- This is required for serverless environment where each webhook creates new Application

CREATE TABLE IF NOT EXISTS conversation_states (
  user_id BIGINT PRIMARY KEY,
  conversation_name VARCHAR(100) NOT NULL,
  state VARCHAR(100),
  data JSONB DEFAULT '{}',
  created_at TIMESTAMP DEFAULT NOW(),
  updated_at TIMESTAMP DEFAULT NOW()
);

-- Index for faster lookups
CREATE INDEX IF NOT EXISTS idx_conversation_states_user_conversation
  ON conversation_states(user_id, conversation_name);

-- Auto-cleanup: remove states older than 24 hours (stale conversations)
-- This should be run periodically or on each state update
-- DELETE FROM conversation_states WHERE updated_at < NOW() - INTERVAL '24 hours';
