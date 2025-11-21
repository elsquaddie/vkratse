-- Cleanup incorrect conversation states from per_chat=False bug
--
-- Problem: Before fix, states were saved as "user_id:user_id" instead of "user_id"
-- This script removes those incorrect entries to allow fresh start
--
-- Run this ONCE after deploying the persistence fix

-- Delete conversation states where user_id has duplicate ID format (e.g., "92146951:92146951")
-- These are invalid states from the bug where per_chat=False was not handled correctly
DELETE FROM conversation_states
WHERE user_id LIKE '%:%'
  AND SPLIT_PART(user_id, ':', 1) = SPLIT_PART(user_id, ':', 2);

-- Show remaining conversation states for verification
SELECT
  conversation_name,
  user_id,
  state,
  updated_at
FROM conversation_states
ORDER BY updated_at DESC;
