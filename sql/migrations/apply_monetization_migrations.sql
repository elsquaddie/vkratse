-- ============================================
-- MONETIZATION MIGRATIONS - MASTER SCRIPT
-- ============================================
-- Date: 2025-11-17
-- Purpose: Apply all monetization-related migrations
--
-- INSTRUCTIONS:
-- 1. Go to Supabase Dashboard → SQL Editor
-- 2. Create a new query
-- 3. Copy and paste this entire file
-- 4. Click "Run" to execute
--
-- This script is idempotent (safe to run multiple times)
-- ============================================

BEGIN;

-- ============================================
-- MIGRATION 003: subscriptions table
-- ============================================

CREATE TABLE IF NOT EXISTS subscriptions (
  id SERIAL PRIMARY KEY,
  user_id BIGINT NOT NULL UNIQUE,
  tier VARCHAR(20) NOT NULL DEFAULT 'free',  -- 'free' or 'pro'
  started_at TIMESTAMP DEFAULT NOW(),
  expires_at TIMESTAMP,  -- NULL for free tier
  payment_method VARCHAR(50),  -- 'stars', 'yookassa', 'tribute'
  transaction_id VARCHAR(255),
  is_active BOOLEAN DEFAULT TRUE,
  created_at TIMESTAMP DEFAULT NOW(),
  updated_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_subscriptions_user_id ON subscriptions(user_id);
CREATE INDEX IF NOT EXISTS idx_subscriptions_tier ON subscriptions(tier);
CREATE INDEX IF NOT EXISTS idx_subscriptions_active ON subscriptions(is_active);
CREATE INDEX IF NOT EXISTS idx_subscriptions_expires ON subscriptions(expires_at);

COMMENT ON TABLE subscriptions IS 'User subscription tiers and payment tracking';

-- ============================================
-- MIGRATION 004: usage_limits table
-- ============================================

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

CREATE INDEX IF NOT EXISTS idx_usage_limits_user_date ON usage_limits(user_id, date);
CREATE INDEX IF NOT EXISTS idx_usage_limits_date ON usage_limits(date);

COMMENT ON TABLE usage_limits IS 'Daily usage tracking for rate limiting';

-- ============================================
-- MIGRATION 005: personality_usage table
-- ============================================

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

CREATE INDEX IF NOT EXISTS idx_personality_usage_user_date ON personality_usage(user_id, date);
CREATE INDEX IF NOT EXISTS idx_personality_usage_user_personality ON personality_usage(user_id, personality_name);

COMMENT ON TABLE personality_usage IS 'Track usage of specific personalities per day';

-- ============================================
-- MIGRATION 006: group_membership_cache table
-- ============================================

CREATE TABLE IF NOT EXISTS group_membership_cache (
  user_id BIGINT PRIMARY KEY,
  is_member BOOLEAN DEFAULT FALSE,
  checked_at TIMESTAMP DEFAULT NOW(),
  updated_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_group_membership_checked ON group_membership_cache(checked_at);

COMMENT ON TABLE group_membership_cache IS 'Cache for project group membership status';

-- ============================================
-- MIGRATION 007: Add personality bonus fields
-- ============================================

ALTER TABLE personalities
ADD COLUMN IF NOT EXISTS is_group_bonus BOOLEAN DEFAULT FALSE;

ALTER TABLE personalities
ADD COLUMN IF NOT EXISTS is_blocked BOOLEAN DEFAULT FALSE;

CREATE INDEX IF NOT EXISTS idx_personalities_group_bonus ON personalities(is_group_bonus);
CREATE INDEX IF NOT EXISTS idx_personalities_blocked ON personalities(is_blocked);

COMMENT ON COLUMN personalities.is_group_bonus IS 'True if this is a bonus personality for group membership';
COMMENT ON COLUMN personalities.is_blocked IS 'True if personality is temporarily blocked (e.g., user left group)';

-- ============================================
-- VERIFY TABLES EXIST
-- ============================================

DO $$
BEGIN
    RAISE NOTICE 'Verifying monetization tables...';

    IF EXISTS (SELECT FROM pg_tables WHERE tablename = 'subscriptions') THEN
        RAISE NOTICE '✓ subscriptions table exists';
    ELSE
        RAISE EXCEPTION '✗ subscriptions table NOT created!';
    END IF;

    IF EXISTS (SELECT FROM pg_tables WHERE tablename = 'usage_limits') THEN
        RAISE NOTICE '✓ usage_limits table exists';
    ELSE
        RAISE EXCEPTION '✗ usage_limits table NOT created!';
    END IF;

    IF EXISTS (SELECT FROM pg_tables WHERE tablename = 'personality_usage') THEN
        RAISE NOTICE '✓ personality_usage table exists';
    ELSE
        RAISE EXCEPTION '✗ personality_usage table NOT created!';
    END IF;

    IF EXISTS (SELECT FROM pg_tables WHERE tablename = 'group_membership_cache') THEN
        RAISE NOTICE '✓ group_membership_cache table exists';
    ELSE
        RAISE EXCEPTION '✗ group_membership_cache table NOT created!';
    END IF;

    RAISE NOTICE 'All monetization tables created successfully! ✓';
END $$;

COMMIT;

-- ============================================
-- SUCCESS MESSAGE
-- ============================================
SELECT 'Monetization migrations applied successfully! ✓' as status;
