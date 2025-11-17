-- Migration 006: Create group_membership_cache table
-- Date: 2025-11-17
-- Purpose: Cache group membership status to avoid repeated API calls

CREATE TABLE IF NOT EXISTS group_membership_cache (
  user_id BIGINT PRIMARY KEY,
  is_member BOOLEAN DEFAULT FALSE,
  checked_at TIMESTAMP DEFAULT NOW(),
  updated_at TIMESTAMP DEFAULT NOW()
);

-- Index for cleanup queries
CREATE INDEX IF NOT EXISTS idx_group_membership_checked ON group_membership_cache(checked_at);

-- Comments
COMMENT ON TABLE group_membership_cache IS 'Cache for project group membership status';
COMMENT ON COLUMN group_membership_cache.is_member IS 'Whether user is member of project group';
COMMENT ON COLUMN group_membership_cache.checked_at IS 'Last time membership was checked';
