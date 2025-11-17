-- Migration 005: Create personality_usage table for tracking personality limits
-- Date: 2025-11-17
-- Purpose: Track daily usage of specific personalities (for free tier limits)

CREATE TABLE IF NOT EXISTS personality_usage (
  id SERIAL PRIMARY KEY,
  user_id BIGINT NOT NULL,
  personality_name VARCHAR(100) NOT NULL,
  date DATE DEFAULT CURRENT_DATE,
  summary_count INT DEFAULT 0,
  chat_count INT DEFAULT 0,
  judge_count INT DEFAULT 0,
  created_at TIMESTAMP DEFAULT NOW(),
  updated_at TIMESTAMP DEFAULT NOW(),
  UNIQUE(user_id, personality_name, date)
);

-- Indexes for fast queries
CREATE INDEX IF NOT EXISTS idx_personality_usage_user_date ON personality_usage(user_id, date);
CREATE INDEX IF NOT EXISTS idx_personality_usage_user_personality ON personality_usage(user_id, personality_name);

-- Comments
COMMENT ON TABLE personality_usage IS 'Track usage of specific personalities per day';
COMMENT ON COLUMN personality_usage.personality_name IS 'Name of the personality (e.g., bydlan, philosopher)';
COMMENT ON COLUMN personality_usage.summary_count IS 'Times used for summary today';
COMMENT ON COLUMN personality_usage.chat_count IS 'Times used for chat today';
COMMENT ON COLUMN personality_usage.judge_count IS 'Times used for judge today';
