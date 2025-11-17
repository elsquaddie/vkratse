-- Migration 004: Create usage_limits table for daily usage tracking
-- Date: 2025-11-17
-- Purpose: Track daily usage of bot features per user

CREATE TABLE IF NOT EXISTS usage_limits (
  id SERIAL PRIMARY KEY,
  user_id BIGINT NOT NULL,
  date DATE DEFAULT CURRENT_DATE,
  messages_count INT DEFAULT 0,
  summaries_count INT DEFAULT 0,
  summaries_dm_count INT DEFAULT 0,
  judge_count INT DEFAULT 0,
  created_at TIMESTAMP DEFAULT NOW(),
  updated_at TIMESTAMP DEFAULT NOW(),
  UNIQUE(user_id, date)
);

-- Indexes for fast queries
CREATE INDEX IF NOT EXISTS idx_usage_limits_user_date ON usage_limits(user_id, date);
CREATE INDEX IF NOT EXISTS idx_usage_limits_date ON usage_limits(date);

-- Comments
COMMENT ON TABLE usage_limits IS 'Daily usage tracking for rate limiting';
COMMENT ON COLUMN usage_limits.messages_count IS 'Direct messages sent in DM today';
COMMENT ON COLUMN usage_limits.summaries_count IS 'Group summaries requested today';
COMMENT ON COLUMN usage_limits.summaries_dm_count IS 'DM summaries requested today';
COMMENT ON COLUMN usage_limits.judge_count IS 'Judge requests today';
