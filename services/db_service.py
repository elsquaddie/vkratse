"""
Database Service
Wrapper around Supabase for all database operations
"""

from datetime import datetime, timedelta, timezone
from typing import List, Optional
from supabase import create_client, Client
import config
from config import logger
from models import Message, Personality, User, Chat


class DBService:
    """Service for database operations using Supabase"""

    def __init__(self):
        """Initialize Supabase client"""
        self.client: Client = create_client(
            config.SUPABASE_URL,
            config.SUPABASE_KEY
        )
        logger.info("DBService initialized")

    # ================================================
    # MESSAGES
    # ================================================

    def save_message(
        self,
        chat_id: int,
        user_id: Optional[int],
        username: Optional[str],
        message_text: Optional[str]
    ) -> None:
        """Save a message to database and auto-cleanup old messages"""
        try:
            # 1. Save new message
            self.client.table('messages').insert({
                'chat_id': chat_id,
                'user_id': user_id,
                'username': username,
                'message_text': message_text
            }).execute()

            # 2. Auto-cleanup: delete messages older than MESSAGE_RETENTION_DAYS
            time_threshold = datetime.now(timezone.utc) - timedelta(days=config.MESSAGE_RETENTION_DAYS)
            delete_response = self.client.table('messages').delete()\
                .eq('chat_id', chat_id)\
                .lt('created_at', time_threshold.isoformat())\
                .execute()

            deleted_count = len(delete_response.data) if delete_response.data else 0
            if deleted_count > 0:
                logger.info(f"Auto-deleted {deleted_count} old messages from chat {chat_id} (older than {config.MESSAGE_RETENTION_DAYS} days)")

            logger.debug(f"Saved message from {username} in chat {chat_id}")
        except Exception as e:
            logger.error(f"Error saving message: {e}")

    def get_messages(
        self,
        chat_id: int,
        limit: int = 50,
        since: Optional[datetime] = None
    ) -> List[Message]:
        """Get messages from a chat"""
        try:
            query = self.client.table('messages')\
                .select('*')\
                .eq('chat_id', chat_id)

            if since:
                query = query.gte('created_at', since.isoformat())

            response = query.order('created_at', desc=True).limit(limit).execute()

            messages = [Message.from_dict(msg) for msg in response.data]
            # Reverse to get chronological order
            messages.reverse()

            logger.debug(f"Retrieved {len(messages)} messages from chat {chat_id}")
            return messages
        except Exception as e:
            logger.error(f"Error getting messages: {e}")
            return []

    def get_messages_by_users(
        self,
        chat_id: int,
        usernames: List[str],
        limit: int = 20
    ) -> List[Message]:
        """Get messages from specific users in a chat"""
        try:
            response = self.client.table('messages')\
                .select('*')\
                .eq('chat_id', chat_id)\
                .in_('username', usernames)\
                .order('created_at', desc=True)\
                .limit(limit)\
                .execute()

            messages = [Message.from_dict(msg) for msg in response.data]
            messages.reverse()

            logger.debug(f"Retrieved {len(messages)} messages from users {usernames}")
            return messages
        except Exception as e:
            logger.error(f"Error getting messages by users: {e}")
            return []

    def delete_messages_by_chat(self, chat_id: int) -> None:
        """Delete all messages from a chat (when bot is removed)"""
        try:
            self.client.table('messages').delete().eq('chat_id', chat_id).execute()
            logger.info(f"Deleted all messages from chat {chat_id}")
        except Exception as e:
            logger.error(f"Error deleting messages: {e}")

    # ================================================
    # PERSONALITIES
    # ================================================

    def get_personality(self, name: str) -> Optional[Personality]:
        """Get personality by name"""
        try:
            response = self.client.table('personalities')\
                .select('*')\
                .eq('name', name)\
                .eq('is_active', True)\
                .single()\
                .execute()

            if response.data:
                return Personality.from_dict(response.data)
            return None
        except Exception as e:
            logger.error(f"Error getting personality '{name}': {e}")
            return None

    def get_personality_by_id(self, personality_id: int) -> Optional[Personality]:
        """Get personality by ID"""
        try:
            response = self.client.table('personalities')\
                .select('*')\
                .eq('id', personality_id)\
                .eq('is_active', True)\
                .single()\
                .execute()

            if response.data:
                return Personality.from_dict(response.data)
            return None
        except Exception as e:
            logger.error(f"Error getting personality with ID {personality_id}: {e}")
            return None

    def get_all_personalities(self, include_inactive: bool = False) -> List[Personality]:
        """Get all personalities"""
        try:
            logger.info(f"🔍 [DB] Fetching personalities (include_inactive={include_inactive})")
            query = self.client.table('personalities').select('*')

            if not include_inactive:
                query = query.eq('is_active', True)

            response = query.order('id').execute()
            logger.info(f"🔍 [DB] Got {len(response.data)} rows from personalities table")

            # Log raw data for debugging
            for idx, p in enumerate(response.data):
                logger.info(f"🔍 [DB] Personality {idx}: {p}")

            personalities = [Personality.from_dict(p) for p in response.data]
            logger.info(f"✅ [DB] Successfully parsed {len(personalities)} personalities")
            return personalities
        except Exception as e:
            logger.error(f"❌ [DB] Error getting personalities: {e}")
            logger.error(f"❌ [DB] Error type: {type(e).__name__}")
            logger.error(f"❌ [DB] Error traceback:", exc_info=True)
            return []

    def create_personality(
        self,
        name: str,
        display_name: str,
        system_prompt: str,
        created_by_user_id: int,
        emoji: str = '🎭'
    ) -> Optional[int]:
        """Create a custom personality"""
        try:
            response = self.client.table('personalities').insert({
                'name': name,
                'display_name': display_name,
                'system_prompt': system_prompt,
                'emoji': emoji,
                'is_custom': True,
                'created_by_user_id': created_by_user_id,
                'is_active': True
            }).execute()

            if response.data:
                personality_id = response.data[0]['id']
                logger.info(f"Created custom personality '{name}' (ID: {personality_id})")
                return personality_id
            return None
        except Exception as e:
            logger.error(f"Error creating personality: {e}")
            return None

    def personality_exists(self, name: str) -> bool:
        """Check if personality with given name exists"""
        try:
            response = self.client.table('personalities')\
                .select('id')\
                .eq('name', name)\
                .execute()

            return len(response.data) > 0
        except Exception as e:
            logger.error(f"Error checking personality existence: {e}")
            return False

    def count_user_custom_personalities(self, user_id: int) -> int:
        """Count how many custom personalities a user has created"""
        try:
            response = self.client.table('personalities')\
                .select('id', count='exact')\
                .eq('is_custom', True)\
                .eq('created_by_user_id', user_id)\
                .execute()

            return response.count or 0
        except Exception as e:
            logger.error(f"Error counting user personalities: {e}")
            return 0

    def delete_personality(self, name: str, user_id: int) -> bool:
        """
        Delete a custom personality (only if created by this user)
        Returns True if deleted, False otherwise
        """
        try:
            # First verify it's a custom personality created by this user
            response = self.client.table('personalities')\
                .select('id, is_custom, created_by_user_id')\
                .eq('name', name)\
                .single()\
                .execute()

            if not response.data:
                logger.warning(f"Personality '{name}' not found")
                return False

            personality = response.data
            if not personality['is_custom']:
                logger.warning(f"Cannot delete base personality '{name}'")
                return False

            if personality['created_by_user_id'] != user_id:
                logger.warning(f"User {user_id} cannot delete personality '{name}' created by another user")
                return False

            # Delete the personality
            self.client.table('personalities')\
                .delete()\
                .eq('name', name)\
                .execute()

            logger.info(f"User {user_id} deleted custom personality '{name}'")
            return True

        except Exception as e:
            logger.error(f"Error deleting personality: {e}")
            return False

    # ================================================
    # USER SETTINGS
    # ================================================

    def get_user_personality(self, user_id: int) -> str:
        """Get user's selected personality (returns name)"""
        try:
            response = self.client.table('user_settings')\
                .select('selected_personality')\
                .eq('user_id', user_id)\
                .single()\
                .execute()

            if response.data:
                return response.data['selected_personality']
            return config.DEFAULT_PERSONALITY
        except Exception:
            # User doesn't exist yet - return default
            return config.DEFAULT_PERSONALITY

    def update_user_personality(
        self,
        user_id: int,
        personality_name: str,
        username: Optional[str] = None
    ) -> None:
        """Update user's selected personality (upsert)"""
        try:
            self.client.table('user_settings').upsert({
                'user_id': user_id,
                'username': username,
                'selected_personality': personality_name
            }).execute()

            logger.info(f"Updated personality for user {user_id} to '{personality_name}'")
        except Exception as e:
            logger.error(f"Error updating user personality: {e}")

    # ================================================
    # CHAT METADATA
    # ================================================

    def save_chat_metadata(
        self,
        chat_id: int,
        chat_title: Optional[str],
        chat_type: str
    ) -> None:
        """Save or update chat metadata"""
        try:
            self.client.table('chat_metadata').upsert({
                'chat_id': chat_id,
                'chat_title': chat_title,
                'chat_type': chat_type,
                'last_activity': datetime.now(timezone.utc).isoformat()
            }).execute()

            logger.debug(f"Updated metadata for chat {chat_id}")
        except Exception as e:
            logger.error(f"Error saving chat metadata: {e}")

    def delete_chat_metadata(self, chat_id: int) -> None:
        """Delete chat metadata (when bot is removed)"""
        try:
            self.client.table('chat_metadata').delete().eq('chat_id', chat_id).execute()
            logger.info(f"Deleted metadata for chat {chat_id}")
        except Exception as e:
            logger.error(f"Error deleting chat metadata: {e}")

    def get_all_chats(self) -> List[Chat]:
        """Get all chats where bot is active"""
        try:
            response = self.client.table('chat_metadata')\
                .select('*')\
                .order('last_activity', desc=True)\
                .execute()

            return [Chat.from_dict(chat) for chat in response.data]
        except Exception as e:
            logger.error(f"Error getting chats: {e}")
            return []

    # ================================================
    # ANALYTICS
    # ================================================

    def log_event(
        self,
        user_id: int,
        chat_id: int,
        event_type: str,
        metadata: dict = None
    ) -> None:
        """Log an event for analytics"""
        try:
            self.client.table('analytics').insert({
                'user_id': user_id,
                'chat_id': chat_id,
                'event_type': event_type,
                'metadata': metadata or {}
            }).execute()

            logger.debug(f"Logged event: {event_type} for user {user_id}")
        except Exception as e:
            logger.error(f"Error logging event: {e}")

    def get_user_stats(self, user_id: int) -> dict:
        """Get user statistics from analytics table"""
        try:
            response = self.client.table('analytics')\
                .select('event_type')\
                .eq('user_id', user_id)\
                .execute()

            # Count events by type
            stats = {}
            for event in response.data:
                event_type = event['event_type']
                stats[event_type] = stats.get(event_type, 0) + 1

            logger.debug(f"Retrieved stats for user {user_id}: {stats}")
            return stats
        except Exception as e:
            logger.error(f"Error getting user stats: {e}")
            return {}

    def get_personality_usage_stats(self, user_id: int) -> dict:
        """
        Get personality usage statistics for a user.

        Returns a dict with:
        - personality_counts: dict of personality name -> usage count
        - favorite_personality: most used personality name
        - total_uses: total number of times personalities were used
        """
        try:
            response = self.client.table('analytics')\
                .select('metadata')\
                .eq('user_id', user_id)\
                .in_('event_type', ['summary', 'summary_dm', 'judge'])\
                .execute()

            # Count personality usage
            personality_counts = {}
            for event in response.data:
                metadata = event.get('metadata', {})
                personality = metadata.get('personality')
                if personality:
                    personality_counts[personality] = personality_counts.get(personality, 0) + 1

            # Find favorite personality (most used)
            favorite = None
            max_count = 0
            if personality_counts:
                favorite = max(personality_counts.items(), key=lambda x: x[1])[0]
                max_count = personality_counts[favorite]

            total_uses = sum(personality_counts.values())

            result = {
                'personality_counts': personality_counts,
                'favorite_personality': favorite,
                'favorite_count': max_count,
                'total_uses': total_uses
            }

            logger.debug(f"Retrieved personality stats for user {user_id}: {result}")
            return result
        except Exception as e:
            logger.error(f"Error getting personality usage stats: {e}")
            return {
                'personality_counts': {},
                'favorite_personality': None,
                'favorite_count': 0,
                'total_uses': 0
            }

    # ================================================
    # CHAT HISTORY (for direct chat context)
    # ================================================

    def get_chat_history(
        self,
        chat_id: int,
        user_id: Optional[int] = None,
        limit: int = 30
    ) -> List[Message]:
        """
        Get recent chat history for context in direct conversations.
        If user_id is provided, only gets messages between that user and the bot.

        Args:
            chat_id: The chat ID
            user_id: Optional user ID to filter conversation with bot
            limit: Maximum number of messages to retrieve (default 30)

        Returns:
            List of Message objects in chronological order
        """
        try:
            query = self.client.table('messages')\
                .select('*')\
                .eq('chat_id', chat_id)

            # If user_id provided, filter for messages from user or bot (user_id=None)
            if user_id:
                query = query.or_(f'user_id.eq.{user_id},user_id.is.null')

            response = query.order('created_at', desc=True).limit(limit).execute()

            messages = [Message.from_dict(msg) for msg in response.data]
            # Reverse to get chronological order (oldest first)
            messages.reverse()

            logger.debug(f"Retrieved {len(messages)} messages for chat history (chat: {chat_id}, user: {user_id})")
            return messages
        except Exception as e:
            logger.error(f"Error getting chat history: {e}")
            return []

    # ================================================
    # ACTIVE CHAT SESSIONS (for /chat in groups)
    # ================================================

    def create_chat_session(
        self,
        user_id: int,
        chat_id: int,
        personality: str
    ) -> bool:
        """
        Create a new active chat session for a user in a group.

        Args:
            user_id: Telegram user ID
            chat_id: Telegram chat ID
            personality: Personality name to use in this session

        Returns:
            True if created successfully, False otherwise
        """
        try:
            self.client.table('active_chat_sessions').upsert({
                'user_id': user_id,
                'chat_id': chat_id,
                'personality': personality,
                'started_at': datetime.now(timezone.utc).isoformat(),
                'last_activity': datetime.now(timezone.utc).isoformat()
            }).execute()

            logger.info(f"Created chat session for user {user_id} in chat {chat_id} with personality '{personality}'")
            return True
        except Exception as e:
            logger.error(f"Error creating chat session: {e}")
            return False

    def get_active_session(
        self,
        user_id: int,
        chat_id: int
    ) -> Optional[dict]:
        """
        Get active chat session for a user in a chat.

        Args:
            user_id: Telegram user ID
            chat_id: Telegram chat ID

        Returns:
            Session dict with personality and timestamps, or None if no active session
        """
        try:
            response = self.client.table('active_chat_sessions')\
                .select('*')\
                .eq('user_id', user_id)\
                .eq('chat_id', chat_id)\
                .single()\
                .execute()

            if response.data:
                logger.debug(f"Found active session for user {user_id} in chat {chat_id}")
                return response.data
            return None
        except Exception:
            # No session found (single() raises exception if no data)
            return None

    def update_session_activity(
        self,
        user_id: int,
        chat_id: int
    ) -> bool:
        """
        Update the last_activity timestamp for a session.

        Args:
            user_id: Telegram user ID
            chat_id: Telegram chat ID

        Returns:
            True if updated, False otherwise
        """
        try:
            response = self.client.table('active_chat_sessions')\
                .update({'last_activity': datetime.now(timezone.utc).isoformat()})\
                .eq('user_id', user_id)\
                .eq('chat_id', chat_id)\
                .execute()

            updated = len(response.data) > 0 if response.data else False
            if updated:
                logger.debug(f"Updated session activity for user {user_id} in chat {chat_id}")
            return updated
        except Exception as e:
            logger.error(f"Error updating session activity: {e}")
            return False

    def end_chat_session(
        self,
        user_id: int,
        chat_id: int
    ) -> bool:
        """
        End (delete) a chat session.

        Args:
            user_id: Telegram user ID
            chat_id: Telegram chat ID

        Returns:
            True if ended successfully, False otherwise
        """
        try:
            response = self.client.table('active_chat_sessions')\
                .delete()\
                .eq('user_id', user_id)\
                .eq('chat_id', chat_id)\
                .execute()

            deleted = len(response.data) > 0 if response.data else False
            if deleted:
                logger.info(f"Ended chat session for user {user_id} in chat {chat_id}")
            return deleted
        except Exception as e:
            logger.error(f"Error ending chat session: {e}")
            return False

    def cleanup_inactive_sessions(
        self,
        timeout_minutes: int = 15
    ) -> int:
        """
        Clean up inactive chat sessions older than timeout.

        Args:
            timeout_minutes: Session timeout in minutes (default 15)

        Returns:
            Number of sessions cleaned up
        """
        try:
            time_threshold = datetime.now(timezone.utc) - timedelta(minutes=timeout_minutes)

            response = self.client.table('active_chat_sessions')\
                .delete()\
                .lt('last_activity', time_threshold.isoformat())\
                .execute()

            deleted_count = len(response.data) if response.data else 0
            if deleted_count > 0:
                logger.info(f"Cleaned up {deleted_count} inactive chat sessions (timeout: {timeout_minutes} min)")
            return deleted_count
        except Exception as e:
            logger.error(f"Error cleaning up inactive sessions: {e}")
            return 0
