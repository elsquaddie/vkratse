-- Migrate conversation_states to use composite key in user_id field
-- This is needed to properly track conversations in both DMs and groups

-- Step 1: Add temporary column
ALTER TABLE conversation_states ADD COLUMN user_id_new VARCHAR(100);

-- Step 2: Convert existing data to composite key format
-- For existing rows where user_id is just a number, we assume it's a DM (chat_id == user_id)
UPDATE conversation_states
SET user_id_new = CAST(user_id AS VARCHAR) || ':' || CAST(user_id AS VARCHAR);

-- Step 3: Drop old primary key constraint
ALTER TABLE conversation_states DROP CONSTRAINT conversation_states_pkey;

-- Step 4: Drop old column
ALTER TABLE conversation_states DROP COLUMN user_id;

-- Step 5: Rename new column to user_id
ALTER TABLE conversation_states RENAME COLUMN user_id_new TO user_id;

-- Step 6: Recreate primary key
ALTER TABLE conversation_states ADD PRIMARY KEY (user_id);

-- Done! Now user_id stores composite keys like "-1001860737658:92146951" or "92146951:92146951" for DMs
