"""
Analytics Middleware
Автоматический трекинг всех взаимодействий пользователей с ботом
"""

from typing import Optional
from telegram import Update
from telegram.ext import ContextTypes, BaseHandler
from config import logger
from services.analytics_service import AnalyticsService


# ================================================
# MIDDLEWARE FUNCTION
# ================================================

async def analytics_middleware(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
) -> None:
    """
    Middleware для автоматического логирования всех взаимодействий

    Вызывается ПЕРЕД обработкой каждого update.
    Логирует:
    - Клики по кнопкам (callback_query)
    - Команды (message with command)
    - Обычные сообщения (message without command)

    Args:
        update: Telegram Update object
        context: Bot context
    """
    try:
        # Get or create analytics service
        if not hasattr(context.bot_data, 'analytics_service'):
            from services.db_service import DBService
            db_service = DBService()
            context.bot_data['analytics_service'] = AnalyticsService(db_service.client)

        analytics = context.bot_data['analytics_service']

        # Get session_id from user_data if exists
        session_id = context.user_data.get('session_id')

        # ================================================
        # 1. CALLBACK QUERY (button clicks)
        # ================================================
        if update.callback_query:
            callback_data = update.callback_query.data
            button_text = None

            # Try to extract button text from the message
            if update.callback_query.message and update.callback_query.message.reply_markup:
                # Find the clicked button text
                for row in update.callback_query.message.reply_markup.inline_keyboard:
                    for button in row:
                        if button.callback_data == callback_data:
                            button_text = button.text
                            break

            # Extract action name from callback_data (before first colon if HMAC signed)
            action_name = callback_data
            if ':' in callback_data:
                # Format: "action_name:param1:param2:hmac_signature"
                # We want just the action_name
                parts = callback_data.split(':')
                action_name = parts[0] if len(parts) > 0 else callback_data

            await analytics.track_button_click(
                update=update,
                action_name=action_name,
                button_text=button_text,
                session_id=session_id
            )

        # ================================================
        # 2. COMMAND (messages starting with /)
        # ================================================
        elif update.message and update.message.text and update.message.text.startswith('/'):
            command_text = update.message.text.split()[0]  # Get first word (command)

            await analytics.track_command(
                update=update,
                command_name=command_text,
                session_id=session_id
            )

        # ================================================
        # 3. REGULAR MESSAGE (text, voice, photo, etc.)
        # ================================================
        elif update.message:
            message_type = 'text'

            # Detect message type
            if update.message.voice:
                message_type = 'voice'
            elif update.message.photo:
                message_type = 'photo'
            elif update.message.document:
                message_type = 'document'
            elif update.message.video:
                message_type = 'video'
            elif update.message.sticker:
                message_type = 'sticker'

            # Only track if it's a direct chat or reply to bot
            chat_type = update.effective_chat.type
            is_direct_chat = chat_type == 'private'
            is_reply_to_bot = (
                update.message.reply_to_message and
                update.message.reply_to_message.from_user.id == context.bot.id
            )

            if is_direct_chat or is_reply_to_bot:
                await analytics.track_message(
                    update=update,
                    message_type=message_type,
                    session_id=session_id
                )

    except Exception as e:
        # Don't fail the main flow if analytics fails
        logger.error(f"Error in analytics middleware: {e}", exc_info=True)


# ================================================
# SESSION HELPERS
# ================================================

def create_user_session(
    context: ContextTypes.DEFAULT_TYPE,
    user_id: int,
    chat_id: int
) -> Optional[str]:
    """
    Create a new user session and store in user_data

    Args:
        context: Bot context
        user_id: Telegram user ID
        chat_id: Telegram chat ID

    Returns:
        Session ID (UUID) or None
    """
    try:
        if not hasattr(context.bot_data, 'analytics_service'):
            from services.db_service import DBService
            db_service = DBService()
            context.bot_data['analytics_service'] = AnalyticsService(db_service.client)

        analytics = context.bot_data['analytics_service']
        session_id = analytics.create_session(user_id, chat_id)

        if session_id:
            context.user_data['session_id'] = session_id
            logger.debug(f"Created session {session_id} for user {user_id}")

        return session_id

    except Exception as e:
        logger.error(f"Error creating user session: {e}", exc_info=True)
        return None


def end_user_session(context: ContextTypes.DEFAULT_TYPE) -> bool:
    """
    End the current user session

    Args:
        context: Bot context

    Returns:
        True if ended successfully
    """
    try:
        session_id = context.user_data.get('session_id')
        if not session_id:
            return False

        if not hasattr(context.bot_data, 'analytics_service'):
            from services.db_service import DBService
            db_service = DBService()
            context.bot_data['analytics_service'] = AnalyticsService(db_service.client)

        analytics = context.bot_data['analytics_service']
        success = analytics.end_session(session_id)

        if success:
            context.user_data.pop('session_id', None)
            logger.debug(f"Ended session {session_id}")

        return success

    except Exception as e:
        logger.error(f"Error ending user session: {e}", exc_info=True)
        return False


# ================================================
# TRACKING HELPERS (for manual tracking in handlers)
# ================================================

async def track_ai_generation(
    context: ContextTypes.DEFAULT_TYPE,
    user_id: int,
    chat_id: int,
    generation_type: str,
    personality: str,
    metadata: Optional[dict] = None
) -> None:
    """
    Track AI generation event

    Args:
        context: Bot context
        user_id: User ID
        chat_id: Chat ID
        generation_type: Type ('summary', 'judge', 'chat_response')
        personality: Personality used
        metadata: Additional metadata
    """
    try:
        if not hasattr(context.bot_data, 'analytics_service'):
            from services.db_service import DBService
            db_service = DBService()
            context.bot_data['analytics_service'] = AnalyticsService(db_service.client)

        analytics = context.bot_data['analytics_service']
        await analytics.track_ai_generation(
            user_id=user_id,
            chat_id=chat_id,
            generation_type=generation_type,
            personality=personality,
            metadata=metadata
        )

    except Exception as e:
        logger.error(f"Error tracking AI generation: {e}", exc_info=True)


async def track_error(
    context: ContextTypes.DEFAULT_TYPE,
    update: Update,
    error_type: str,
    error_message: str
) -> None:
    """
    Track error for debugging

    Args:
        context: Bot context
        update: Update that caused error
        error_type: Type of error
        error_message: Error message
    """
    try:
        if not hasattr(context.bot_data, 'analytics_service'):
            from services.db_service import DBService
            db_service = DBService()
            context.bot_data['analytics_service'] = AnalyticsService(db_service.client)

        analytics = context.bot_data['analytics_service']

        user = update.effective_user
        chat = update.effective_chat

        # Track as button_analytics entry with type 'error'
        analytics.client.table('button_analytics').insert({
            'user_id': user.id if user else None,
            'username': user.username if user else None,
            'chat_id': chat.id if chat else None,
            'chat_type': chat.type if chat else None,
            'action_type': 'error',
            'action_name': error_type,
            'metadata': {
                'error_message': error_message,
                'update_type': update.update_id
            }
        }).execute()

    except Exception as e:
        logger.error(f"Error tracking error: {e}", exc_info=True)
