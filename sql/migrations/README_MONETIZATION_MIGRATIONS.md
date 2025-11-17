# 💰 Monetization Migrations - Instructions

## 📋 Overview

This directory contains SQL migrations for implementing the monetization system v2.1.

## 🚀 How to Apply Migrations

### Option 1: Apply All at Once (Recommended)

1. Open **Supabase Dashboard** → **SQL Editor**
2. Click **"+ New query"**
3. Copy the contents of `apply_monetization_migrations.sql`
4. Paste into the editor
5. Click **"Run"** (or press Ctrl/Cmd + Enter)
6. Verify all tables were created successfully

### Option 2: Apply Individual Migrations

Apply in this order:

1. `003_create_subscriptions.sql` - Subscription tiers
2. `004_create_usage_limits.sql` - Daily usage tracking
3. `005_create_personality_usage.sql` - Personality usage tracking
4. `006_create_group_membership_cache.sql` - Group membership cache
5. `007_add_personality_bonus_fields.sql` - Personality bonus fields

## ✅ Verification Checklist

After applying migrations, verify the following:

### 1. Check Tables Exist

Run this query in Supabase SQL Editor:

```sql
SELECT table_name
FROM information_schema.tables
WHERE table_schema = 'public'
  AND table_name IN (
    'subscriptions',
    'usage_limits',
    'personality_usage',
    'group_membership_cache'
  )
ORDER BY table_name;
```

**Expected result:** All 4 tables should be listed.

---

### 2. Check Columns in personalities Table

Run this query:

```sql
SELECT column_name, data_type, is_nullable
FROM information_schema.columns
WHERE table_name = 'personalities'
  AND column_name IN ('is_group_bonus', 'is_blocked')
ORDER BY column_name;
```

**Expected result:**
- `is_group_bonus` - boolean, nullable
- `is_blocked` - boolean, nullable

---

### 3. Check Indexes

Run this query:

```sql
SELECT
  schemaname,
  tablename,
  indexname
FROM pg_indexes
WHERE tablename IN (
  'subscriptions',
  'usage_limits',
  'personality_usage',
  'group_membership_cache',
  'personalities'
)
AND indexname LIKE '%monetization%' OR indexname LIKE '%subscription%' OR indexname LIKE '%usage%' OR indexname LIKE '%group_bonus%' OR indexname LIKE '%blocked%'
ORDER BY tablename, indexname;
```

**Expected result:** Multiple indexes for efficient queries.

---

### 4. Test Insert and Select

Test each table:

```sql
-- Test subscriptions
INSERT INTO subscriptions (user_id, tier)
VALUES (123456789, 'free')
ON CONFLICT (user_id) DO NOTHING;

SELECT * FROM subscriptions WHERE user_id = 123456789;

-- Test usage_limits
INSERT INTO usage_limits (user_id, messages_count)
VALUES (123456789, 5)
ON CONFLICT (user_id, date)
DO UPDATE SET messages_count = usage_limits.messages_count + 5;

SELECT * FROM usage_limits WHERE user_id = 123456789;

-- Test personality_usage
INSERT INTO personality_usage (user_id, personality_name, summary_count)
VALUES (123456789, 'bydlan', 1)
ON CONFLICT (user_id, personality_name, date)
DO UPDATE SET summary_count = personality_usage.summary_count + 1;

SELECT * FROM personality_usage WHERE user_id = 123456789;

-- Test group_membership_cache
INSERT INTO group_membership_cache (user_id, is_member)
VALUES (123456789, true)
ON CONFLICT (user_id)
DO UPDATE SET is_member = true, checked_at = NOW();

SELECT * FROM group_membership_cache WHERE user_id = 123456789;

-- Cleanup test data
DELETE FROM subscriptions WHERE user_id = 123456789;
DELETE FROM usage_limits WHERE user_id = 123456789;
DELETE FROM personality_usage WHERE user_id = 123456789;
DELETE FROM group_membership_cache WHERE user_id = 123456789;
```

**Expected result:** All inserts and selects should work without errors.

---

## 🔧 Environment Variables

After applying migrations, add these to your `.env` file (and Vercel):

```env
# Monetization settings
PROJECT_TELEGRAM_GROUP_ID=0  # Replace with actual group ID
TRIBUTE_URL=https://tribute.to/your_bot_page  # Replace with actual URL
ADMIN_USER_ID=0  # Replace with your Telegram user ID

# Optional (for YooKassa integration)
YOOKASSA_SHOP_ID=
YOOKASSA_SECRET_KEY=
```

---

## 🐛 Troubleshooting

### Problem: "relation already exists"

**Solution:** This is normal if you run the script multiple times. All migrations use `IF NOT EXISTS` or `IF NOT EXISTS`, so they're safe to re-run.

---

### Problem: "column already exists"

**Solution:** Same as above - `ADD COLUMN IF NOT EXISTS` ensures idempotency.

---

### Problem: "permission denied"

**Solution:** Ensure you're using the correct Supabase credentials with sufficient permissions.

---

## 📊 Database Schema Overview

```
┌─────────────────────┐
│   subscriptions     │ ← User tier (free/pro)
├─────────────────────┤
│ user_id (PK)        │
│ tier                │
│ expires_at          │
│ payment_method      │
└─────────────────────┘

┌─────────────────────┐
│   usage_limits      │ ← Daily usage tracking
├─────────────────────┤
│ user_id             │
│ date                │
│ messages_count      │
│ summaries_dm_count  │
│ judge_count         │
└─────────────────────┘

┌─────────────────────┐
│ personality_usage   │ ← Personality-specific limits
├─────────────────────┤
│ user_id             │
│ personality_name    │
│ date                │
│ summary_count       │
│ chat_count          │
│ judge_count         │
└─────────────────────┘

┌─────────────────────┐
│ group_membership_   │ ← Group bonus tracking
│      cache          │
├─────────────────────┤
│ user_id (PK)        │
│ is_member           │
│ checked_at          │
└─────────────────────┘

┌─────────────────────┐
│   personalities     │ ← Enhanced with bonus fields
├─────────────────────┤
│ ...existing...      │
│ is_group_bonus ✨   │ NEW
│ is_blocked ✨       │ NEW
└─────────────────────┘
```

---

## ✅ Success Checklist

- [x] All 4 new tables created
- [x] 2 new columns added to personalities
- [x] All indexes created
- [x] Test inserts/selects work
- [x] Environment variables configured
- [x] Config.py updated with TIER_LIMITS

**Next step:** Proceed to Step 2 in `TODO_MONETIZATION_v2.1.md`

---

**Created:** 2025-11-17
**Version:** v2.1
**Status:** Ready for production
