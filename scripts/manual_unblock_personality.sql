-- Manual Personality Unblock Script
-- Use this to check and manually unblock personalities in Supabase

-- ================================================
-- STEP 1: Find your user_id
-- ================================================
-- Replace 'YOUR_TELEGRAM_USERNAME' with your actual Telegram username (without @)
SELECT
    user_id,
    username,
    selected_personality,
    created_at
FROM user_settings
WHERE username = 'YOUR_TELEGRAM_USERNAME';
-- Copy the user_id from the result


-- ================================================
-- STEP 2: Check all your group bonus personalities
-- ================================================
-- Replace YOUR_USER_ID with the user_id from Step 1
SELECT
    id,
    name,
    display_name,
    emoji,
    is_group_bonus,
    is_blocked,
    is_active,
    created_at
FROM personalities
WHERE created_by_user_id = YOUR_USER_ID
  AND is_group_bonus = true
ORDER BY created_at DESC;


-- ================================================
-- STEP 3: Check group membership cache
-- ================================================
-- Replace YOUR_USER_ID with the user_id from Step 1
SELECT
    user_id,
    is_member,
    checked_at
FROM group_membership_cache
WHERE user_id = YOUR_USER_ID;


-- ================================================
-- STEP 4: Manually unblock all your group bonus personalities
-- ================================================
-- This is what the bot should do automatically when you're in the group
-- Replace YOUR_USER_ID with the user_id from Step 1
UPDATE personalities
SET is_blocked = false
WHERE created_by_user_id = YOUR_USER_ID
  AND is_group_bonus = true
  AND is_active = true;

-- Check how many rows were updated
SELECT
    id,
    name,
    display_name,
    is_blocked
FROM personalities
WHERE created_by_user_id = YOUR_USER_ID
  AND is_group_bonus = true;


-- ================================================
-- STEP 5: Update group membership cache (force refresh)
-- ================================================
-- This forces the bot to recheck your membership on next request
-- Replace YOUR_USER_ID with the user_id from Step 1
DELETE FROM group_membership_cache
WHERE user_id = YOUR_USER_ID;

-- The bot will recheck your membership on next interaction
