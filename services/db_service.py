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

            # Auto-cleanup completed silently
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
            return messages
        except Exception as e:
            logger.error(f"Error getting messages by users: {e}")
            return []

    def delete_messages_by_chat(self, chat_id: int) -> None:
        """Delete all messages from a chat (when bot is removed)"""
        try:
            self.client.table('messages').delete().eq('chat_id', chat_id).execute()
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
            query = self.client.table('personalities').select('*')

            if not include_inactive:
                query = query.eq('is_active', True)

            response = query.order('id').execute()
            personalities = [Personality.from_dict(p) for p in response.data]
            return personalities
        except Exception as e:
            logger.error(f"Error getting personalities: {e}", exc_info=True)
            return []

    def create_personality(
        self,
        name: str,
        display_name: str,
        system_prompt: str,
        created_by_user_id: int,
        emoji: str = '🎭',
        is_group_bonus: bool = False
    ) -> Optional[int]:
        """
        Create a custom personality

        Args:
            name: Internal name (lowercase)
            display_name: Display name
            system_prompt: AI personality prompt
            created_by_user_id: Creator's Telegram user ID
            emoji: Personality emoji
            is_group_bonus: Whether this is a group membership bonus personality

        Returns:
            Personality ID if successful, None otherwise
        """
        try:
            response = self.client.table('personalities').insert({
                'name': name,
                'display_name': display_name,
                'system_prompt': system_prompt,
                'emoji': emoji,
                'is_custom': True,
                'created_by_user_id': created_by_user_id,
                'is_active': True,
                'is_group_bonus': is_group_bonus
            }).execute()

            if response.data:
                personality_id = response.data[0]['id']
                logger.info(f"Created personality '{name}' (ID: {personality_id}, group_bonus: {is_group_bonus})")
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

    def get_user_personalities(self, user_id: int) -> List[Personality]:
        """
        Get all personalities available to a user (base personalities + their custom ones).

        Args:
            user_id: Telegram user ID

        Returns:
            List of Personality objects (base + user's custom)
        """
        try:
            # Get all base personalities (is_custom=False) + user's custom personalities
            response = self.client.table('personalities')\
                .select('*')\
                .eq('is_active', True)\
                .or_(f'is_custom.eq.false,created_by_user_id.eq.{int(user_id)}')\
                .order('is_custom')\
                .order('id')\
                .execute()

            personalities = [Personality.from_dict(p) for p in response.data]
            return personalities
        except Exception as e:
            logger.error(f"Error getting user personalities: {e}")
            return []

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

            return True

        except Exception as e:
            logger.error(f"Error deleting personality: {e}")
            return False

    def update_personality(
        self,
        name: str,
        user_id: int,
        display_name: Optional[str] = None,
        emoji: Optional[str] = None,
        system_prompt: Optional[str] = None
    ) -> bool:
        """
        Update a custom personality (only if created by this user)

        Args:
            name: Current personality name
            user_id: User ID (must be creator)
            display_name: New display name (optional)
            emoji: New emoji (optional)
            system_prompt: New system prompt (optional)

        Returns:
            True if updated, False otherwise
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
                logger.warning(f"Cannot edit base personality '{name}'")
                return False

            if personality['created_by_user_id'] != user_id:
                logger.warning(f"User {user_id} cannot edit personality '{name}' created by another user")
                return False

            # Build update dict with only provided fields
            update_data = {}
            if display_name is not None:
                update_data['display_name'] = display_name
            if emoji is not None:
                update_data['emoji'] = emoji
            if system_prompt is not None:
                update_data['system_prompt'] = system_prompt

            if not update_data:
                logger.warning("No fields to update")
                return False

            # Update the personality
            self.client.table('personalities')\
                .update(update_data)\
                .eq('name', name)\
                .execute()

            return True

        except Exception as e:
            logger.error(f"Error updating personality: {e}")
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

        except Exception as e:
            logger.error(f"Error saving chat metadata: {e}")

    def delete_chat_metadata(self, chat_id: int) -> None:
        """Delete chat metadata (when bot is removed)"""
        try:
            self.client.table('chat_metadata').delete().eq('chat_id', chat_id).execute()
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

            return stats
        except Exception as e:
            logger.error(f"Error getting user stats: {e}")
            return {}

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
                # SECURITY: use int() to prevent SQL injection
                query = query.or_(f'user_id.eq.{int(user_id)},user_id.is.null')

            response = query.order('created_at', desc=True).limit(limit).execute()

            messages = [Message.from_dict(msg) for msg in response.data]
            # Reverse to get chronological order (oldest first)
            messages.reverse()

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
            return deleted_count
        except Exception as e:
            logger.error(f"Error cleaning up inactive sessions: {e}")
            return 0

    # ================================================
    # MONETIZATION: SUBSCRIPTIONS
    # ================================================

    async def get_subscription(self, user_id: int) -> Optional[dict]:
        """
        Get user's subscription info

        Args:
            user_id: Telegram user ID

        Returns:
            Subscription dict or None
        """
        try:
            response = self.client.table('subscriptions')\
                .select('*')\
                .eq('user_id', user_id)\
                .single()\
                .execute()

            return response.data if response.data else None
        except Exception:
            # No subscription found
            return None

    async def create_or_update_subscription(
        self,
        user_id: int,
        tier: str,
        duration_days: int,
        payment_method: str = 'manual',
        transaction_id: Optional[str] = None
    ) -> bool:
        """
        Create or update user subscription

        Args:
            user_id: Telegram user ID
            tier: 'free' or 'pro'
            duration_days: Number of days for subscription
            payment_method: 'manual', 'tribute', 'yookassa', 'telegram_stars'
            transaction_id: Optional transaction ID

        Returns:
            True if successful
        """
        try:
            expires_at = datetime.now(timezone.utc) + timedelta(days=duration_days)

            logger.info(
                f"Creating/updating subscription for user {user_id}: "
                f"tier={tier}, duration={duration_days} days, "
                f"payment_method={payment_method}, expires_at={expires_at.isoformat()}"
            )

            data = {
                'user_id': user_id,
                'tier': tier,
                'expires_at': expires_at.isoformat(),
                'payment_method': payment_method,
                'transaction_id': transaction_id,
                'is_active': True,
                'updated_at': datetime.now(timezone.utc).isoformat()
            }

            logger.info(f"Upserting data to subscriptions table: {data}")

            result = self.client.table('subscriptions').upsert(data, on_conflict='user_id').execute()

            logger.info(f"Upsert result: {result.data if hasattr(result, 'data') else 'no data'}")
            logger.info(f"Subscription created/updated successfully for user {user_id}: {tier}, {duration_days} days")

            # Unblock/block custom personalities based on new tier
            import config
            tier_limits = config.TIER_LIMITS.get(tier, config.TIER_LIMITS['free'])
            max_custom_personalities = tier_limits.get('max_custom_personalities', 0)

            # This will unblock personalities within the limit, block excess ones
            await self.block_excess_custom_personalities(user_id, limit=max_custom_personalities)
            logger.info(f"Adjusted personality blocking for user {user_id} based on tier {tier} (limit={max_custom_personalities})")

            return True
        except Exception as e:
            logger.error(f"Error creating/updating subscription for {user_id}: {e}", exc_info=True)
            return False

    async def deactivate_subscription(self, user_id: int) -> bool:
        """
        Deactivate user's subscription (downgrade to Free tier)

        Args:
            user_id: Telegram user ID

        Returns:
            True if successful
        """
        try:
            self.client.table('subscriptions')\
                .update({
                    'tier': 'free',
                    'is_active': False,
                    'expires_at': None,  # Clear expiration date
                    'updated_at': datetime.now(timezone.utc).isoformat()
                })\
                .eq('user_id', user_id)\
                .execute()

            logger.info(f"Subscription deactivated for user {user_id} (downgraded to Free tier)")
            return True
        except Exception as e:
            logger.error(f"Error deactivating subscription for {user_id}: {e}")
            return False

    # ================================================
    # MONETIZATION: USAGE LIMITS
    # ================================================

    async def get_usage_limits(self, user_id: int, date: 'date') -> Optional[dict]:
        """
        Get usage limits for a user on a specific date

        Args:
            user_id: Telegram user ID
            date: Date to check

        Returns:
            Usage dict or None
        """
        try:
            from datetime import date as date_type
            date_str = date.isoformat()

            response = self.client.table('usage_limits')\
                .select('*')\
                .eq('user_id', user_id)\
                .eq('date', date_str)\
                .single()\
                .execute()

            return response.data if response.data else None
        except Exception:
            # No usage record for this date
            return None

    async def increment_usage_limit(self, user_id: int, action: str) -> bool:
        """
        Increment usage counter for an action

        Args:
            user_id: Telegram user ID
            action: 'message_dm', 'summary_dm', 'summary_group', 'judge'

        Returns:
            True if successful
        """
        try:
            from datetime import date as date_type
            today = date_type.today()

            # Map action to field name
            action_field_map = {
                'message_dm': 'messages_count',
                'summary_dm': 'summaries_dm_count',
                'summary_group': 'summaries_count',
                'judge': 'judge_count'
            }

            field_name = action_field_map.get(action, 'messages_count')

            # Get current usage
            current_usage = await self.get_usage_limits(user_id, today)

            if current_usage:
                # Increment existing record
                new_value = current_usage.get(field_name, 0) + 1
                self.client.table('usage_limits')\
                    .update({field_name: new_value})\
                    .eq('user_id', user_id)\
                    .eq('date', today.isoformat())\
                    .execute()
            else:
                # Create new record
                self.client.table('usage_limits').insert({
                    'user_id': user_id,
                    'date': today.isoformat(),
                    field_name: 1
                }).execute()

            return True
        except Exception as e:
            logger.error(f"Error incrementing usage limit for {user_id}, {action}: {e}")
            return False

    # ================================================
    # MONETIZATION: PERSONALITY USAGE
    # ================================================

    async def get_personality_usage(
        self,
        user_id: int,
        personality: str,
        date: 'date'
    ) -> Optional[dict]:
        """
        Get personality usage for a user on a specific date

        Args:
            user_id: Telegram user ID
            personality: Personality name
            date: Date to check

        Returns:
            Usage dict or None
        """
        try:
            from datetime import date as date_type
            date_str = date.isoformat()

            response = self.client.table('personality_usage')\
                .select('*')\
                .eq('user_id', user_id)\
                .eq('personality_name', personality)\
                .eq('date', date_str)\
                .single()\
                .execute()

            return response.data if response.data else None
        except Exception:
            # No usage record
            return None

    async def increment_personality_usage(
        self,
        user_id: int,
        personality: str,
        action: str
    ) -> bool:
        """
        Increment personality usage counter

        Args:
            user_id: Telegram user ID
            personality: Personality name
            action: 'summary', 'chat', 'judge'

        Returns:
            True if successful
        """
        try:
            from datetime import date as date_type
            today = date_type.today()

            # Map action to field name
            action_field_map = {
                'summary': 'summary_count',
                'chat': 'chat_count',
                'judge': 'judge_count'
            }

            field_name = action_field_map.get(action, 'summary_count')

            # Get current usage
            current_usage = await self.get_personality_usage(user_id, personality, today)

            if current_usage:
                # Increment existing record
                new_value = current_usage.get(field_name, 0) + 1
                self.client.table('personality_usage')\
                    .update({field_name: new_value})\
                    .eq('user_id', user_id)\
                    .eq('personality_name', personality)\
                    .eq('date', today.isoformat())\
                    .execute()
            else:
                # Create new record
                self.client.table('personality_usage').insert({
                    'user_id': user_id,
                    'personality_name': personality,
                    'date': today.isoformat(),
                    field_name: 1
                }).execute()

            return True
        except Exception as e:
            logger.error(f"Error incrementing personality usage for {user_id}, {personality}, {action}: {e}")
            return False

    async def get_top_personality_usage(
        self,
        user_id: int,
        date: 'date',
        limit: int = 3
    ) -> List[dict]:
        """
        Get top N most used personalities for a user on a specific date

        Args:
            user_id: Telegram user ID
            date: Date to check
            limit: Number of top personalities to return (default 3)

        Returns:
            List of personality usage records sorted by total usage descending
        """
        try:
            from datetime import date as date_type
            date_str = date.isoformat()

            response = self.client.table('personality_usage')\
                .select('*')\
                .eq('user_id', user_id)\
                .eq('date', date_str)\
                .execute()

            if not response.data:
                return []

            # Calculate total usage for each personality and sort
            for record in response.data:
                record['total_usage'] = (
                    record.get('summary_count', 0) +
                    record.get('chat_count', 0) +
                    record.get('judge_count', 0)
                )

            # Sort by total usage descending
            sorted_records = sorted(
                response.data,
                key=lambda x: x['total_usage'],
                reverse=True
            )

            # Return top N
            return sorted_records[:limit]

        except Exception as e:
            logger.error(f"Error getting top personality usage for {user_id}: {e}")
            return []

    # ================================================
    # MONETIZATION: GROUP MEMBERSHIP CACHE
    # ================================================

    async def get_group_membership_cache(self, user_id: int) -> Optional[dict]:
        """
        Get cached group membership status

        Args:
            user_id: Telegram user ID

        Returns:
            Cache dict or None
        """
        try:
            response = self.client.table('group_membership_cache')\
                .select('*')\
                .eq('user_id', user_id)\
                .single()\
                .execute()

            return response.data if response.data else None
        except Exception:
            # No cache found
            return None

    async def update_group_membership_cache(
        self,
        user_id: int,
        is_member: bool
    ) -> bool:
        """
        Update group membership cache

        Args:
            user_id: Telegram user ID
            is_member: Whether user is in the group

        Returns:
            True if successful
        """
        try:
            self.client.table('group_membership_cache').upsert({
                'user_id': user_id,
                'is_member': is_member,
                'checked_at': datetime.now(timezone.utc).isoformat()
            }).execute()

            return True
        except Exception as e:
            logger.error(f"Error updating group membership cache for {user_id}: {e}")
            return False

    # ================================================
    # MONETIZATION: CUSTOM PERSONALITIES MANAGEMENT
    # ================================================

    async def get_active_custom_personalities_count(self, user_id: int) -> int:
        """
        Get count of active custom personalities for a user

        Args:
            user_id: Telegram user ID

        Returns:
            Count of active custom personalities
        """
        try:
            response = self.client.table('personalities')\
                .select('id', count='exact')\
                .eq('created_by_user_id', user_id)\
                .eq('is_custom', True)\
                .eq('is_active', True)\
                .execute()

            return response.count if response.count else 0
        except Exception as e:
            logger.error(f"Error counting custom personalities for {user_id}: {e}")
            return 0

    async def block_excess_custom_personalities(
        self,
        user_id: int,
        limit: int
    ) -> bool:
        """
        Block (soft-block) custom personalities exceeding the limit
        Uses is_blocked=True to keep personalities visible but inaccessible

        Args:
            user_id: Telegram user ID
            limit: Maximum allowed custom personalities

        Returns:
            True if successful
        """
        try:
            # Get all custom personalities for this user
            response = self.client.table('personalities')\
                .select('id, name')\
                .eq('created_by_user_id', user_id)\
                .eq('is_custom', True)\
                .eq('is_active', True)\
                .order('created_at', desc=False)\
                .execute()

            personalities = response.data

            # If count is within limit, unblock all and return
            if len(personalities) <= limit:
                # Unblock all custom personalities within limit
                for p in personalities:
                    self.client.table('personalities')\
                        .update({'is_blocked': False})\
                        .eq('id', p['id'])\
                        .execute()
                return True

            # Block the excess ones (keep the oldest `limit` personalities)
            # First, unblock the ones within limit
            for p in personalities[:limit]:
                self.client.table('personalities')\
                    .update({'is_blocked': False})\
                    .eq('id', p['id'])\
                    .execute()

            # Then block the excess ones
            to_block = personalities[limit:]
            for p in to_block:
                self.client.table('personalities')\
                    .update({'is_blocked': True})\
                    .eq('id', p['id'])\
                    .execute()

            logger.info(f"Blocked {len(to_block)} custom personalities for user {user_id}")
            return True

        except Exception as e:
            logger.error(f"Error blocking excess personalities for {user_id}: {e}")
            return False

    async def block_group_bonus_personalities(self, user_id: int) -> bool:
        """
        Block (soft-block) group bonus personalities when user leaves the group

        Args:
            user_id: Telegram user ID

        Returns:
            True if successful
        """
        try:
            # Set is_blocked = True for all group bonus personalities
            self.client.table('personalities')\
                .update({'is_blocked': True})\
                .eq('created_by_user_id', user_id)\
                .eq('is_group_bonus', True)\
                .eq('is_active', True)\
                .execute()

            logger.info(f"Blocked group bonus personalities for user {user_id}")
            return True

        except Exception as e:
            logger.error(f"Error blocking group bonus personalities for {user_id}: {e}")
            return False

    async def unblock_group_bonus_personalities(self, user_id: int) -> bool:
        """
        Unblock group bonus personalities when user joins the group

        Args:
            user_id: Telegram user ID

        Returns:
            True if successful
        """
        try:
            # Set is_blocked = False for all group bonus personalities
            self.client.table('personalities')\
                .update({'is_blocked': False})\
                .eq('created_by_user_id', user_id)\
                .eq('is_group_bonus', True)\
                .eq('is_active', True)\
                .execute()

            logger.info(f"Unblocked group bonus personalities for user {user_id}")
            return True

        except Exception as e:
            logger.error(f"Error unblocking group bonus personalities for {user_id}: {e}")
            return False
