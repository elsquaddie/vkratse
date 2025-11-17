"""
Analytics Service
Централизованный сервис для трекинга всех взаимодействий с ботом
"""

import uuid
from datetime import datetime, timezone
from typing import Optional, Dict, Any
from telegram import Update, User, Chat
from supabase import Client
import config
from config import logger


class AnalyticsService:
    """Service for tracking user interactions and button clicks"""

    def __init__(self, supabase_client: Client):
        """
        Initialize Analytics Service

        Args:
            supabase_client: Supabase client instance
        """
        self.client = supabase_client

    # ================================================
    # CORE TRACKING METHODS
    # ================================================

    async def track_button_click(
        self,
        update: Update,
        action_name: str,
        button_text: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
        session_id: Optional[str] = None
    ) -> None:
        """
        Track button click in button_analytics table

        Args:
            update: Telegram Update object
            action_name: Name of the action (e.g., 'select_personality', 'direct_chat')
            button_text: Text of the clicked button
            metadata: Additional metadata as dict
            session_id: Optional session ID for user journey tracking
        """
        try:
            user = update.effective_user
            chat = update.effective_chat
            callback_query = update.callback_query

            # Extract callback_data if available
            callback_data = callback_query.data if callback_query else None

            # Get previous action from context (if tracking user journey)
            previous_action = None
            if update.callback_query and update.callback_query.message:
                # Could extract from bot_data/user_data if needed
                pass

            # Insert into button_analytics
            self.client.table('button_analytics').insert({
                'user_id': user.id,
                'username': user.username,
                'chat_id': chat.id,
                'chat_type': chat.type,
                'action_type': 'button_click',
                'action_name': action_name,
                'button_text': button_text,
                'callback_data': callback_data,
                'previous_action': previous_action,
                'session_id': session_id,
                'metadata': metadata or {}
            }).execute()

            logger.debug(f"Tracked button click: {action_name} by user {user.id}")

        except Exception as e:
            # Don't fail the main flow if analytics fails
            logger.error(f"Error tracking button click: {e}", exc_info=True)

    async def track_command(
        self,
        update: Update,
        command_name: str,
        metadata: Optional[Dict[str, Any]] = None,
        session_id: Optional[str] = None
    ) -> None:
        """
        Track command usage

        Args:
            update: Telegram Update object
            command_name: Name of the command (e.g., '/start', '/summary')
            metadata: Additional metadata
            session_id: Optional session ID
        """
        try:
            user = update.effective_user
            chat = update.effective_chat

            self.client.table('button_analytics').insert({
                'user_id': user.id,
                'username': user.username,
                'chat_id': chat.id,
                'chat_type': chat.type,
                'action_type': 'command',
                'action_name': command_name,
                'button_text': None,
                'callback_data': None,
                'session_id': session_id,
                'metadata': metadata or {}
            }).execute()

            logger.debug(f"Tracked command: {command_name} by user {user.id}")

        except Exception as e:
            logger.error(f"Error tracking command: {e}", exc_info=True)

    async def track_message(
        self,
        update: Update,
        message_type: str = 'text',
        metadata: Optional[Dict[str, Any]] = None,
        session_id: Optional[str] = None
    ) -> None:
        """
        Track user message (for direct chat, etc.)

        Args:
            update: Telegram Update object
            message_type: Type of message ('text', 'voice', 'photo', etc.)
            metadata: Additional metadata
            session_id: Optional session ID
        """
        try:
            user = update.effective_user
            chat = update.effective_chat

            self.client.table('button_analytics').insert({
                'user_id': user.id,
                'username': user.username,
                'chat_id': chat.id,
                'chat_type': chat.type,
                'action_type': 'message',
                'action_name': f'message_{message_type}',
                'session_id': session_id,
                'metadata': metadata or {}
            }).execute()

            logger.debug(f"Tracked message: {message_type} by user {user.id}")

        except Exception as e:
            logger.error(f"Error tracking message: {e}", exc_info=True)

    async def track_ai_generation(
        self,
        user_id: int,
        chat_id: int,
        generation_type: str,
        personality: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> None:
        """
        Track AI generation events (summary, judge, chat response)

        Args:
            user_id: Telegram user ID
            chat_id: Telegram chat ID
            generation_type: Type of generation ('summary', 'judge', 'chat_response')
            personality: Personality used
            metadata: Additional metadata (e.g., tokens used, response time)
        """
        try:
            meta = metadata or {}
            meta['personality'] = personality

            self.client.table('button_analytics').insert({
                'user_id': user_id,
                'username': None,
                'chat_id': chat_id,
                'chat_type': None,
                'action_type': 'ai_generation',
                'action_name': generation_type,
                'metadata': meta
            }).execute()

            # Also log in legacy analytics table for compatibility
            self.client.table('analytics').insert({
                'user_id': user_id,
                'chat_id': chat_id,
                'event_type': generation_type,
                'metadata': meta
            }).execute()

            logger.debug(f"Tracked AI generation: {generation_type} with {personality}")

        except Exception as e:
            logger.error(f"Error tracking AI generation: {e}", exc_info=True)

    # ================================================
    # SESSION MANAGEMENT
    # ================================================

    def create_session(
        self,
        user_id: int,
        chat_id: int,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Optional[str]:
        """
        Create a new user session for journey tracking

        Args:
            user_id: Telegram user ID
            chat_id: Telegram chat ID
            metadata: Additional session metadata

        Returns:
            Session UUID as string, or None if creation failed
        """
        try:
            response = self.client.table('user_sessions').insert({
                'user_id': user_id,
                'chat_id': chat_id,
                'metadata': metadata or {}
            }).execute()

            if response.data and len(response.data) > 0:
                session_id = response.data[0]['id']
                logger.debug(f"Created session {session_id} for user {user_id}")
                return session_id

            return None

        except Exception as e:
            logger.error(f"Error creating session: {e}", exc_info=True)
            return None

    def end_session(self, session_id: str) -> bool:
        """
        End a user session

        Args:
            session_id: Session UUID

        Returns:
            True if ended successfully
        """
        try:
            self.client.table('user_sessions').update({
                'ended_at': datetime.now(timezone.utc).isoformat()
            }).eq('id', session_id).execute()

            logger.debug(f"Ended session {session_id}")
            return True

        except Exception as e:
            logger.error(f"Error ending session: {e}", exc_info=True)
            return False

    # ================================================
    # BACKWARD COMPATIBILITY
    # ================================================

    def log_event(
        self,
        user_id: int,
        chat_id: int,
        event_type: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> None:
        """
        Log event to legacy analytics table (for backward compatibility)

        Args:
            user_id: Telegram user ID
            chat_id: Telegram chat ID
            event_type: Type of event
            metadata: Additional metadata
        """
        try:
            self.client.table('analytics').insert({
                'user_id': user_id,
                'chat_id': chat_id,
                'event_type': event_type,
                'metadata': metadata or {}
            }).execute()

        except Exception as e:
            logger.error(f"Error logging event: {e}", exc_info=True)

    # ================================================
    # ANALYTICS QUERIES
    # ================================================

    def get_popular_buttons(self, days_back: int = 7, limit: int = 10) -> list:
        """
        Get most popular buttons clicked in the last N days

        Args:
            days_back: Number of days to look back
            limit: Maximum number of results

        Returns:
            List of dicts with button stats
        """
        try:
            # Use the SQL function we created
            response = self.client.rpc(
                'get_top_actions',
                {'days_back': days_back, 'limit_count': limit}
            ).execute()

            return response.data if response.data else []

        except Exception as e:
            logger.error(f"Error getting popular buttons: {e}", exc_info=True)
            return []

    def get_user_journey(self, user_id: int, days_back: int = 7) -> list:
        """
        Get a user's journey (sequence of actions)

        Args:
            user_id: Telegram user ID
            days_back: Number of days to look back

        Returns:
            List of actions in chronological order
        """
        try:
            response = self.client.table('button_analytics')\
                .select('action_type, action_name, button_text, created_at')\
                .eq('user_id', user_id)\
                .gte('created_at', f'now() - interval \'{days_back} days\'')\
                .order('created_at', desc=False)\
                .execute()

            return response.data if response.data else []

        except Exception as e:
            logger.error(f"Error getting user journey: {e}", exc_info=True)
            return []

    def get_conversion_funnel(self) -> list:
        """
        Get conversion funnel data (from materialized view)

        Returns:
            List of funnel steps with conversion rates
        """
        try:
            response = self.client.table('conversion_funnel')\
                .select('*')\
                .execute()

            return response.data if response.data else []

        except Exception as e:
            logger.error(f"Error getting conversion funnel: {e}", exc_info=True)
            return []


# ================================================
# HELPER FUNCTIONS (for easy import)
# ================================================

def get_analytics_service(supabase_client: Client) -> AnalyticsService:
    """
    Get or create analytics service instance

    Args:
        supabase_client: Supabase client

    Returns:
        AnalyticsService instance
    """
    return AnalyticsService(supabase_client)


# For backward compatibility with existing code
def track_event_simple(
    supabase_client: Client,
    user_id: int,
    chat_id: int,
    event_type: str,
    metadata: Optional[Dict[str, Any]] = None
) -> None:
    """
    Simple event tracking (legacy compatibility)

    Args:
        supabase_client: Supabase client
        user_id: User ID
        chat_id: Chat ID
        event_type: Event type
        metadata: Additional data
    """
    service = AnalyticsService(supabase_client)
    service.log_event(user_id, chat_id, event_type, metadata)
