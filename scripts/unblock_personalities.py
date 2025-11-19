"""
Script to manually unblock custom personalities for a user

Usage:
    python scripts/unblock_personalities.py <user_id>
"""

import sys
import os
import asyncio

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from services import DBService
from config import logger


async def unblock_all_personalities(user_id: int):
    """
    Unblock all custom personalities for a user

    Args:
        user_id: Telegram user ID
    """
    db = DBService()

    try:
        # Get all blocked custom personalities
        response = db.client.table('personalities')\
            .select('*')\
            .eq('created_by_user_id', user_id)\
            .eq('is_custom', True)\
            .eq('is_blocked', True)\
            .execute()

        personalities = response.data

        if not personalities:
            print(f"✅ No blocked personalities found for user {user_id}")
            return

        print(f"Found {len(personalities)} blocked personalities:")
        for p in personalities:
            print(f"  - {p['display_name']} (is_group_bonus: {p.get('is_group_bonus', False)})")

        # Unblock all
        response = db.client.table('personalities')\
            .update({'is_blocked': False})\
            .eq('created_by_user_id', user_id)\
            .eq('is_custom', True)\
            .eq('is_blocked', True)\
            .execute()

        print(f"\n✅ Unblocked {len(personalities)} personalities for user {user_id}")

        # Show final state
        response = db.client.table('personalities')\
            .select('display_name, is_blocked, is_group_bonus')\
            .eq('created_by_user_id', user_id)\
            .eq('is_custom', True)\
            .execute()

        print("\nFinal state:")
        for p in response.data:
            status = "🔒 Blocked" if p['is_blocked'] else "✅ Active"
            bonus = " (group bonus)" if p.get('is_group_bonus') else ""
            print(f"  {status} - {p['display_name']}{bonus}")

    except Exception as e:
        logger.error(f"Error unblocking personalities: {e}")
        print(f"❌ Error: {e}")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python scripts/unblock_personalities.py <user_id>")
        print("\nExample:")
        print("  python scripts/unblock_personalities.py 123456789")
        sys.exit(1)

    try:
        user_id = int(sys.argv[1])
    except ValueError:
        print("❌ Error: user_id must be a number")
        sys.exit(1)

    print(f"Unblocking personalities for user {user_id}...\n")
    asyncio.run(unblock_all_personalities(user_id))
