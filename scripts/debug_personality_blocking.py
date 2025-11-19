"""
Debug script to investigate why a personality got blocked

Usage:
    python scripts/debug_personality_blocking.py <user_id>
"""

import sys
import os
import asyncio
from datetime import datetime

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from services import DBService
from services.subscription import get_subscription_service, init_subscription_service
from config import logger, PROJECT_TELEGRAM_GROUP_ID


async def debug_blocking(user_id: int):
    """
    Debug why a personality got blocked for a user

    Args:
        user_id: Telegram user ID
    """
    db = DBService()
    init_subscription_service(db)
    subscription_service = get_subscription_service()

    print(f"\n{'='*60}")
    print(f"🔍 DEBUGGING PERSONALITY BLOCKING FOR USER {user_id}")
    print(f"{'='*60}\n")

    # 1. Check subscription
    print("📋 SUBSCRIPTION INFO:")
    try:
        subscription = await db.get_subscription(user_id)
        if subscription:
            print(f"  Tier: {subscription.get('tier', 'N/A')}")
            print(f"  Active: {subscription.get('is_active', 'N/A')}")
            print(f"  Expires: {subscription.get('expires_at', 'N/A')}")
            print(f"  Payment method: {subscription.get('payment_method', 'N/A')}")
        else:
            print("  ⚠️ No subscription found (FREE tier)")
    except Exception as e:
        print(f"  ❌ Error: {e}")

    # 2. Check group membership
    print(f"\n👥 GROUP MEMBERSHIP:")
    print(f"  Project group ID configured: {PROJECT_TELEGRAM_GROUP_ID}")
    if PROJECT_TELEGRAM_GROUP_ID:
        try:
            cache = await db.get_group_membership_cache(user_id)
            if cache:
                print(f"  Is member (cached): {cache.get('is_member', 'N/A')}")
                print(f"  Checked at: {cache.get('checked_at', 'N/A')}")
            else:
                print("  ⚠️ No cache entry (never checked)")
        except Exception as e:
            print(f"  ❌ Error: {e}")
    else:
        print("  ⚠️ Project group ID NOT configured - membership tracking disabled!")

    # 3. Check custom personalities
    print(f"\n🎭 CUSTOM PERSONALITIES:")
    try:
        response = db.client.table('personalities')\
            .select('*')\
            .eq('created_by_user_id', user_id)\
            .eq('is_custom', True)\
            .execute()

        personalities = response.data
        print(f"  Total custom personalities: {len(personalities)}")

        for p in personalities:
            status = "🔒 BLOCKED" if p.get('is_blocked') else "✅ Active"
            bonus = " [GROUP BONUS]" if p.get('is_group_bonus') else ""
            print(f"\n  {status} - {p['display_name']}{bonus}")
            print(f"    ID: {p['id']}")
            print(f"    Name: {p['name']}")
            print(f"    Created: {p.get('created_at', 'N/A')}")
            print(f"    is_group_bonus: {p.get('is_group_bonus', False)}")
            print(f"    is_blocked: {p.get('is_blocked', False)}")
            print(f"    is_active: {p.get('is_active', True)}")

    except Exception as e:
        print(f"  ❌ Error: {e}")

    # 4. Check what SHOULD happen
    print(f"\n🔬 ANALYSIS:")
    tier = await subscription_service.get_user_tier(user_id)
    print(f"  Current tier (from service): {tier}")

    limit = await subscription_service.get_custom_personality_limit(user_id, None)
    print(f"  Custom personality limit: {limit}")

    count = await db.get_active_custom_personalities_count(user_id)
    print(f"  Active custom personalities: {count}")

    if count > limit:
        print(f"  ⚠️ OVER LIMIT! Should block {count - limit} personalities")
    else:
        print(f"  ✅ Within limit")

    # 5. Possible causes
    print(f"\n💡 POSSIBLE CAUSES OF BLOCKING:")
    causes = []

    if not PROJECT_TELEGRAM_GROUP_ID:
        causes.append("❌ PROJECT_TELEGRAM_GROUP_ID not configured")
        causes.append("   → Membership tracking won't work")
        causes.append("   → But shouldn't cause blocking either")

    if tier == 'free':
        causes.append("⚠️ User is FREE tier")
        causes.append("   → Personalities created with is_group_bonus=True")
        causes.append("   → Will be blocked if user leaves group (but tracking is broken!)")

    if count > limit:
        causes.append(f"⚠️ Exceeded limit: {count} > {limit}")
        causes.append("   → auto_downgrade_expired_subscription() may have been called")

    if not causes:
        causes.append("✅ No obvious causes found")
        causes.append("   → Blocking may have been manual or from old migration")

    for cause in causes:
        print(f"  {cause}")

    print(f"\n{'='*60}")
    print("📝 RECOMMENDATION:")
    print("  1. Check Vercel logs for 'Blocked group bonus personalities'")
    print("  2. Run unblock script if needed:")
    print(f"     python scripts/unblock_personalities.py {user_id}")
    print(f"{'='*60}\n")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python scripts/debug_personality_blocking.py <user_id>")
        print("\nExample:")
        print("  python scripts/debug_personality_blocking.py 123456789")
        sys.exit(1)

    try:
        user_id = int(sys.argv[1])
    except ValueError:
        print("❌ Error: user_id must be a number")
        sys.exit(1)

    asyncio.run(debug_blocking(user_id))
