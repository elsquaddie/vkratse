-- Migration 003: Create subscriptions table for monetization
-- Date: 2025-11-17
-- Purpose: Track user subscription tiers (free/pro) and expiration dates

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

-- Indexes for fast queries
CREATE INDEX IF NOT EXISTS idx_subscriptions_user_id ON subscriptions(user_id);
CREATE INDEX IF NOT EXISTS idx_subscriptions_tier ON subscriptions(tier);
CREATE INDEX IF NOT EXISTS idx_subscriptions_active ON subscriptions(is_active);
CREATE INDEX IF NOT EXISTS idx_subscriptions_expires ON subscriptions(expires_at);

-- Comments
COMMENT ON TABLE subscriptions IS 'User subscription tiers and payment tracking';
COMMENT ON COLUMN subscriptions.tier IS 'Subscription tier: free or pro';
COMMENT ON COLUMN subscriptions.expires_at IS 'Expiration date (NULL for free tier)';
COMMENT ON COLUMN subscriptions.payment_method IS 'Payment method: stars, yookassa, tribute';
