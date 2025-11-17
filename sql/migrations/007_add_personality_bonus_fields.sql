-- Migration 007: Add group bonus and blocking fields to personalities
-- Date: 2025-11-17
-- Purpose: Support group bonus personalities and soft blocking

-- Add is_group_bonus field to track if personality is a group bonus
ALTER TABLE personalities
ADD COLUMN IF NOT EXISTS is_group_bonus BOOLEAN DEFAULT FALSE;

-- Add is_blocked field for soft blocking personalities
ALTER TABLE personalities
ADD COLUMN IF NOT EXISTS is_blocked BOOLEAN DEFAULT FALSE;

-- Add index for queries
CREATE INDEX IF NOT EXISTS idx_personalities_group_bonus ON personalities(is_group_bonus);
CREATE INDEX IF NOT EXISTS idx_personalities_blocked ON personalities(is_blocked);

-- Comments
COMMENT ON COLUMN personalities.is_group_bonus IS 'True if this is a bonus personality for group membership';
COMMENT ON COLUMN personalities.is_blocked IS 'True if personality is temporarily blocked (e.g., user left group)';
