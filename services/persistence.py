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
            logger.info(f"🔥 PERSISTENCE: Loading conversations for '{name}'")
            response = self.db.client.table('conversation_states')\
                .select('user_id, state')\
                .eq('conversation_name', name)\
                .execute()

            logger.info(f"🔥 PERSISTENCE: Got {len(response.data)} rows from DB")

            # Convert to ConversationDict format: {(chat_id, user_id): state}
            conversations = {}
            for row in response.data:
                # user_id is stored as "chat_id:user_id" composite key
                composite_key = row['user_id']
                state = row.get('state')

                logger.info(f"🔥 PERSISTENCE: Row: composite_key={composite_key}, state={state} (type: {type(state)})")

                if state and ':' in str(composite_key):
                    # Parse composite key: "chat_id:user_id"
                    parts = str(composite_key).split(':')
                    if len(parts) == 2:
                        try:
                            chat_id = int(parts[0])
                            user_id = int(parts[1])
                            state_int = int(state)
                            conversations[(chat_id, user_id)] = state_int
                            logger.info(f"🔥 PERSISTENCE: Added conversation key ({chat_id}, {user_id}) -> state {state_int}")
                        except (ValueError, TypeError) as e:
                            logger.warning(f"Invalid composite key or state '{composite_key}' / '{state}': {e}")
                    else:
                        logger.warning(f"Invalid composite key format '{composite_key}', expected 'chat_id:user_id'")

            logger.info(f"🔥 PERSISTENCE: Final conversations dict: {conversations}")
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
            # Store as composite key "chat_id:user_id"
            chat_id = key[0] if len(key) >= 1 else 0
            user_id = key[-1]  # Last element is always user_id
            composite_key = f"{chat_id}:{user_id}"

            logger.info(f"🔥 PERSISTENCE: update_conversation called: name={name}, key={key}, composite_key={composite_key}, new_state={new_state}")

            if new_state is None:
                # Delete conversation
                self.db.client.table('conversation_states')\
                    .delete()\
                    .eq('user_id', composite_key)\
                    .eq('conversation_name', name)\
                    .execute()

                logger.info(f"🔥 PERSISTENCE: Deleted conversation state for composite_key {composite_key}, conversation '{name}'")
            else:
                # Upsert conversation state (use composite key as user_id)
                self.db.client.table('conversation_states')\
                    .upsert({
                        'user_id': composite_key,
                        'conversation_name': name,
                        'state': str(new_state),
                        'updated_at': datetime.now(timezone.utc).isoformat()
                    })\
                    .execute()

                logger.info(f"🔥 PERSISTENCE: Saved conversation state for composite_key {composite_key}, conversation '{name}', state: {new_state}")

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
            logger.info("🔥 PERSISTENCE: get_user_data() called")
            response = self.db.client.table('conversation_states')\
                .select('user_id, data')\
                .eq('conversation_name', 'user_data')\
                .execute()

            logger.info(f"🔥 PERSISTENCE: Found {len(response.data)} user_data rows")

            user_data = {}
            for row in response.data:
                user_id_str = row['user_id']
                data = row.get('data', {})

                logger.info(f"🔥 PERSISTENCE: Row user_id={user_id_str}, data={data}")

                if isinstance(data, str):
                    data = json.loads(data)

                # Convert string user_id back to int for user_data dict
                try:
                    user_id_int = int(user_id_str)
                    user_data[user_id_int] = data or {}
                    logger.info(f"🔥 PERSISTENCE: Added user_data[{user_id_int}] = {data}")
                except ValueError:
                    logger.warning(f"Invalid user_id format in user_data: {user_id_str}")

            logger.info(f"🔥 PERSISTENCE: Final user_data dict: {user_data}")
            return user_data

        except Exception as e:
            logger.error(f"Error loading user_data: {e}")
            return {}

    async def update_user_data(self, user_id: int, data: Dict) -> None:
        """Save user_data to database"""
        try:
            # Store user_data with string user_id (not composite key)
            # Use conversation_name='user_data' to distinguish from conversation states
            self.db.client.table('conversation_states')\
                .upsert({
                    'user_id': str(user_id),  # Convert int to string for VARCHAR column
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
                .eq('user_id', str(user_id))\
                .eq('conversation_name', 'user_data')\
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
