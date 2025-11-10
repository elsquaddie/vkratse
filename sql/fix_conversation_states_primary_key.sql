-- Fix conversation_states table: use composite primary key
-- This allows the same user to have multiple concurrent conversations

-- Step 1: Drop the old primary key
ALTER TABLE conversation_states DROP CONSTRAINT IF EXISTS conversation_states_pkey;

-- Step 2: Add composite primary key on (user_id, conversation_name)
ALTER TABLE conversation_states ADD PRIMARY KEY (user_id, conversation_name);

-- Step 3: Update the index (it should already exist, but let's recreate it to be sure)
DROP INDEX IF EXISTS idx_conversation_states_user_conversation;
CREATE INDEX idx_conversation_states_user_conversation
  ON conversation_states(user_id, conversation_name);

-- Done! Now we can store multiple conversations for the same user_id
