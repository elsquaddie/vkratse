#!/usr/bin/env python3
"""
One-time cleanup script to delete old messages from database
Run this after changing MESSAGE_RETENTION_DAYS to clean existing old data
"""

import sys
import os
from datetime import datetime, timedelta, timezone

# Add parent directory to path to import config
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from supabase import create_client
import config
from config import logger


def cleanup_old_messages():
    """Delete all messages older than MESSAGE_RETENTION_DAYS from all chats"""

    logger.info("=" * 60)
    logger.info("Starting cleanup of old messages")
    logger.info(f"Retention policy: {config.MESSAGE_RETENTION_DAYS} days")
    logger.info("=" * 60)

    # Initialize Supabase client
    client = create_client(config.SUPABASE_URL, config.SUPABASE_KEY)

    # Calculate time threshold
    time_threshold = datetime.now(timezone.utc) - timedelta(days=config.MESSAGE_RETENTION_DAYS)
    logger.info(f"Deleting messages older than: {time_threshold.isoformat()}")

    try:
        # First, get statistics by chat
        logger.info("\nFetching statistics before cleanup...")

        # Get all messages older than threshold
        old_messages = client.table('messages')\
            .select('chat_id, created_at')\
            .lt('created_at', time_threshold.isoformat())\
            .execute()

        if not old_messages.data:
            logger.info("✅ No old messages found - database is clean!")
            return

        # Count by chat
        chat_counts = {}
        for msg in old_messages.data:
            chat_id = msg['chat_id']
            chat_counts[chat_id] = chat_counts.get(chat_id, 0) + 1

        total_old = len(old_messages.data)
        logger.info(f"\nFound {total_old} old messages across {len(chat_counts)} chats:")
        for chat_id, count in sorted(chat_counts.items(), key=lambda x: x[1], reverse=True):
            logger.info(f"  Chat {chat_id}: {count} messages")

        # Confirm deletion
        print("\n" + "=" * 60)
        response = input(f"Delete {total_old} messages? [y/N]: ")
        if response.lower() != 'y':
            logger.info("Cleanup cancelled by user")
            return

        # Delete old messages
        logger.info("\nDeleting old messages...")
        delete_response = client.table('messages').delete()\
            .lt('created_at', time_threshold.isoformat())\
            .execute()

        deleted_count = len(delete_response.data) if delete_response.data else 0
        logger.info(f"✅ Successfully deleted {deleted_count} old messages")

        # Show final statistics
        logger.info("\nFetching final statistics...")
        remaining_messages = client.table('messages')\
            .select('id', count='exact')\
            .execute()

        remaining_count = remaining_messages.count or 0
        logger.info(f"📊 Remaining messages in database: {remaining_count}")

        logger.info("\n" + "=" * 60)
        logger.info("✅ Cleanup completed successfully!")
        logger.info("=" * 60)

    except Exception as e:
        logger.error(f"❌ Error during cleanup: {e}")
        sys.exit(1)


def main():
    """Main entry point"""
    try:
        cleanup_old_messages()
    except KeyboardInterrupt:
        logger.info("\n\nCleanup interrupted by user")
        sys.exit(0)


if __name__ == '__main__':
    main()
