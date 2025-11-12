-- ================================================
-- Complete Phase 2 Setup
-- Run this ONCE in Supabase SQL Editor
-- ================================================

-- Step 1: Add emoji column (if not exists)
ALTER TABLE personalities ADD COLUMN IF NOT EXISTS emoji VARCHAR(10) DEFAULT '🎭';

-- Step 2: Update emoji for base personalities
UPDATE personalities SET emoji = '🎓' WHERE name = 'neutral' AND emoji = '🎭';
UPDATE personalities SET emoji = '🏭' WHERE name = 'bydlan' AND emoji = '🎭';
UPDATE personalities SET emoji = '🧙' WHERE name = 'philosopher' AND emoji = '🎭';
UPDATE personalities SET emoji = '👟' WHERE name = 'gopnik' AND emoji = '🎭';
UPDATE personalities SET emoji = '💼' WHERE name = 'oligarch' AND emoji = '🎭';
UPDATE personalities SET emoji = '😂' WHERE name = 'comedian' AND emoji = '🎭';
UPDATE personalities SET emoji = '🔬' WHERE name = 'scientist' AND emoji = '🎭';

-- Step 3: Add greeting_message column (if not exists)
ALTER TABLE personalities ADD COLUMN IF NOT EXISTS greeting_message TEXT DEFAULT NULL;

-- Step 4: Fill greetings for base personalities
UPDATE personalities
SET greeting_message = 'Йоу, братан! Ну че, приехали? Че надо?
Не стой как столб, давай базарь чё к чему! 🏭'
WHERE name = 'bydlan' AND greeting_message IS NULL;

UPDATE personalities
SET greeting_message = 'Приветствую тебя, путник. Ты пришёл в поисках истины,
или просто заблудился в лабиринте бытия? 🧙'
WHERE name = 'philosopher' AND greeting_message IS NULL;

UPDATE personalities
SET greeting_message = 'Чё, браток, залетел? Давай базарить, только конкретно,
без этих твоих приколов. 👟'
WHERE name = 'gopnik' AND greeting_message IS NULL;

UPDATE personalities
SET greeting_message = 'Друг мой, как приятно видеть тебя!
Присядь, расскажи о своих делах. Может, инвестировать куда посоветуешь? 💼'
WHERE name = 'oligarch' AND greeting_message IS NULL;

UPDATE personalities
SET greeting_message = 'Привет-привет! 😂 Готов к шуткам и приколам?
Давай я буду твоим персональным комиком!'
WHERE name = 'comedian' AND greeting_message IS NULL;

UPDATE personalities
SET greeting_message = 'Здравствуйте. Я готов к анализу и научному подходу
к вашим вопросам. Давайте начнём исследование! 🔬'
WHERE name = 'scientist' AND greeting_message IS NULL;

UPDATE personalities
SET greeting_message = 'Здравствуй! Я готов помочь тебе.
Задавай вопросы, и я отвечу максимально профессионально и по делу. 🎓'
WHERE name = 'neutral' AND greeting_message IS NULL;

-- Step 5: Create active_chat_sessions table (if not exists)
CREATE TABLE IF NOT EXISTS active_chat_sessions (
  id SERIAL PRIMARY KEY,
  user_id BIGINT NOT NULL,
  chat_id BIGINT NOT NULL,
  personality VARCHAR(100) NOT NULL,
  started_at TIMESTAMP DEFAULT NOW(),
  last_activity TIMESTAMP DEFAULT NOW(),
  CONSTRAINT unique_user_chat UNIQUE(user_id, chat_id)
);

-- Step 6: Create index for session activity
CREATE INDEX IF NOT EXISTS idx_sessions_activity ON active_chat_sessions(last_activity);
CREATE INDEX IF NOT EXISTS idx_sessions_user_chat ON active_chat_sessions(user_id, chat_id);

-- Step 7: Create function to cleanup old sessions (15 minutes)
CREATE OR REPLACE FUNCTION cleanup_inactive_sessions()
RETURNS void AS $$
BEGIN
  DELETE FROM active_chat_sessions
  WHERE last_activity < NOW() - INTERVAL '15 minutes';
END;
$$ LANGUAGE plpgsql;

-- ================================================
-- Verification: Check all changes applied correctly
-- ================================================
DO $$
BEGIN
  -- Check emoji column exists
  IF EXISTS (
    SELECT 1 FROM information_schema.columns
    WHERE table_name = 'personalities' AND column_name = 'emoji'
  ) THEN
    RAISE NOTICE '✅ emoji column exists';
  ELSE
    RAISE EXCEPTION '❌ emoji column missing!';
  END IF;

  -- Check greeting_message column exists
  IF EXISTS (
    SELECT 1 FROM information_schema.columns
    WHERE table_name = 'personalities' AND column_name = 'greeting_message'
  ) THEN
    RAISE NOTICE '✅ greeting_message column exists';
  ELSE
    RAISE EXCEPTION '❌ greeting_message column missing!';
  END IF;

  -- Check active_chat_sessions table exists
  IF EXISTS (
    SELECT 1 FROM information_schema.tables
    WHERE table_name = 'active_chat_sessions'
  ) THEN
    RAISE NOTICE '✅ active_chat_sessions table exists';
  ELSE
    RAISE EXCEPTION '❌ active_chat_sessions table missing!';
  END IF;

  RAISE NOTICE '✅ All Phase 2 migrations applied successfully!';
END $$;

-- ================================================
-- Check current state
-- ================================================
SELECT
  name,
  display_name,
  emoji,
  CASE
    WHEN greeting_message IS NOT NULL THEN '✅ Has greeting'
    ELSE '❌ No greeting'
  END as greeting_status
FROM personalities
ORDER BY id;
