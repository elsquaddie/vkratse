-- Migration: Add emoji column to personalities table
-- Date: 2025-11-09
-- Purpose: Store emoji in database instead of hardcoding in Python

-- Add emoji column with default value
ALTER TABLE personalities ADD COLUMN IF NOT EXISTS emoji VARCHAR(10) DEFAULT '🎭';

-- Update emoji for base personalities
UPDATE personalities SET emoji = '🎓' WHERE name = 'neutral';
UPDATE personalities SET emoji = '🏭' WHERE name = 'bydlan';
UPDATE personalities SET emoji = '🧙' WHERE name = 'philosopher';
UPDATE personalities SET emoji = '👟' WHERE name = 'gopnik';
UPDATE personalities SET emoji = '💼' WHERE name = 'oligarch';
UPDATE personalities SET emoji = '😂' WHERE name = 'comedian';
UPDATE personalities SET emoji = '🔬' WHERE name = 'scientist';
