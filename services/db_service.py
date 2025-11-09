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
            self.client.table('messages').delete()\
                .eq('chat_id', chat_id)\
                .lt('created_at', time_threshold.isoformat())\
                .execute()

            logger.debug(f"Saved message from {username} in chat {chat_id}, cleaned old messages")
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

    def get_all_personalities(self, include_inactive: bool = False) -> List[Personality]:
        """Get all personalities"""
        try:
            query = self.client.table('personalities').select('*')

            if not include_inactive:
                query = query.eq('is_active', True)

            response = query.order('id').execute()

            return [Personality.from_dict(p) for p in response.data]
        except Exception as e:
            logger.error(f"Error getting personalities: {e}")
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
