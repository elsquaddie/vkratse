"""
Supabase-based persistence for ConversationHandler
Required for serverless environment
"""

from telegram.ext import BasePersistence, PersistenceInput
from telegram.ext._utils.types import ConversationDict, CDCData
from typing import Dict, Optional, Tuple
import json
from datetime import datetime, timedelta, timezone
from config import logger
from services.db_service import DBService


class SupabasePersistence(BasePersistence):
    """
    Store ConversationHandler states in Supabase

    This is required for serverless environment where each webhook
    creates a new Application instance
    """

    def __init__(self, store_data: Optional[PersistenceInput] = None):
        super().__init__(
            store_data=store_data or PersistenceInput(
                bot_data=False,
                chat_data=False,
                user_data=True,  # We need user_data for conversation context
                callback_data=False
            )
        )
        self.db = DBService()

    async def get_conversations(self, name: str) -> ConversationDict:
        """Load conversation states from database"""
        try:
            response = self.db.client.table('conversation_states')\
                .select('user_id, state')\
                .eq('conversation_name', name)\
                .execute()

            # Convert to ConversationDict format: {(chat_id, user_id): state}
            conversations = {}
            for row in response.data:
                user_id = row['user_id']
                state = row.get('state')

                if state:
                    # ConversationHandler expects (chat_id, user_id) as key
                    # For DMs chat_id == user_id
                    # Convert state from string to int
                    try:
                        state_int = int(state)
                        conversations[(user_id, user_id)] = state_int
                    except (ValueError, TypeError):
                        logger.warning(f"Invalid state '{state}' for user {user_id}, skipping")

            logger.debug(f"Loaded {len(conversations)} conversation states for '{name}'")
            return conversations

        except Exception as e:
            logger.error(f"Error loading conversations: {e}")
            return {}

    async def update_conversation(
        self,
        name: str,
        key: Tuple[int, ...],
        new_state: Optional[object]
    ) -> None:
        """Save conversation state to database"""
        try:
            # key is (chat_id, user_id) for group chats or (user_id, user_id) for DMs
            user_id = key[-1]  # Last element is always user_id

            if new_state is None:
                # Delete conversation
                self.db.client.table('conversation_states')\
                    .delete()\
                    .eq('user_id', user_id)\
                    .eq('conversation_name', name)\
                    .execute()

                logger.debug(f"Deleted conversation state for user {user_id}, conversation '{name}'")
            else:
                # Upsert conversation state
                self.db.client.table('conversation_states')\
                    .upsert({
                        'user_id': user_id,
                        'conversation_name': name,
                        'state': str(new_state),
                        'updated_at': datetime.now(timezone.utc).isoformat()
                    })\
                    .execute()

                logger.debug(f"Saved conversation state for user {user_id}, conversation '{name}', state: {new_state}")

            # Cleanup old conversations (older than 24 hours)
            threshold = datetime.now(timezone.utc) - timedelta(hours=24)
            self.db.client.table('conversation_states')\
                .delete()\
                .lt('updated_at', threshold.isoformat())\
                .execute()

        except Exception as e:
            logger.error(f"Error updating conversation: {e}")

    async def get_user_data(self) -> Dict[int, Dict]:
        """Load user_data from database"""
        try:
            response = self.db.client.table('conversation_states')\
                .select('user_id, data')\
                .execute()

            user_data = {}
            for row in response.data:
                user_id = row['user_id']
                data = row.get('data', {})

                if isinstance(data, str):
                    data = json.loads(data)

                user_data[user_id] = data or {}

            logger.debug(f"Loaded user_data for {len(user_data)} users")
            return user_data

        except Exception as e:
            logger.error(f"Error loading user_data: {e}")
            return {}

    async def update_user_data(self, user_id: int, data: Dict) -> None:
        """Save user_data to database"""
        try:
            # Update data field for existing conversation
            # or create new record if doesn't exist
            self.db.client.table('conversation_states')\
                .upsert({
                    'user_id': user_id,
                    'conversation_name': 'user_data',  # Special conversation for user_data
                    'data': json.dumps(data),
                    'updated_at': datetime.now(timezone.utc).isoformat()
                })\
                .execute()

            logger.debug(f"Saved user_data for user {user_id}")

        except Exception as e:
            logger.error(f"Error updating user_data: {e}")

    async def get_bot_data(self) -> Dict:
        """We don't store bot_data"""
        return {}

    async def update_bot_data(self, data: Dict) -> None:
        """We don't store bot_data"""
        pass

    async def get_chat_data(self) -> Dict[int, Dict]:
        """We don't store chat_data"""
        return {}

    async def update_chat_data(self, chat_id: int, data: Dict) -> None:
        """We don't store chat_data"""
        pass

    async def get_callback_data(self) -> Optional[CDCData]:
        """We don't store callback_data"""
        return None

    async def update_callback_data(self, data: CDCData) -> None:
        """We don't store callback_data"""
        pass

    async def drop_chat_data(self, chat_id: int) -> None:
        """We don't store chat_data"""
        pass

    async def drop_user_data(self, user_id: int) -> None:
        """Delete user_data from database"""
        try:
            self.db.client.table('conversation_states')\
                .delete()\
                .eq('user_id', user_id)\
                .execute()

            logger.debug(f"Dropped user_data for user {user_id}")

        except Exception as e:
            logger.error(f"Error dropping user_data: {e}")

    async def refresh_bot_data(self, bot_data: Dict) -> None:
        """We don't store bot_data"""
        pass

    async def refresh_chat_data(self, chat_id: int, chat_data: Dict) -> None:
        """We don't store chat_data"""
        pass

    async def refresh_user_data(self, user_id: int, user_data: Dict) -> None:
        """Refresh user_data in database"""
        await self.update_user_data(user_id, user_data)

    async def flush(self) -> None:
        """Flush any pending writes (not needed for Supabase)"""
        pass
