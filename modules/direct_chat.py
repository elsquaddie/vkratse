"""
Direct Chat Module
Handles 1-on-1 conversations with the bot in private chats
"""

from typing import Optional
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from telegram.constants import ChatType

import config
from config import logger
from services.db_service import DBService
from services.ai_service import AIService
from utils.security import sign_callback_data, verify_callback_data


db_service = DBService()
ai_service = AIService()


async def show_personality_selection(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    edit_message: bool = False
) -> None:
    """
    Show personality selection menu to the user.

    Args:
        update: Telegram update object
        context: Bot context
        edit_message: If True, edit existing message; if False, send new message
    """
    try:
        user_id = update.effective_user.id

        # Get all personalities (base + user's custom)
        all_personalities = db_service.get_all_personalities()

        # Separate base and custom personalities
        base_personalities = [p for p in all_personalities if not p.is_custom]
        custom_personalities = [p for p in all_personalities if p.is_custom and p.created_by_user_id == user_id]

        # Build inline keyboard (2 columns layout)
        keyboard = []

        # Add base personalities in rows of 2
        for i in range(0, len(base_personalities), 2):
            row = []
            for j in range(2):
                if i + j < len(base_personalities):
                    p = base_personalities[i + j]
                    callback_data = sign_callback_data(f"select_personality:{p.name}")
                    row.append(InlineKeyboardButton(
                        f"{p.emoji} {p.display_name}",
                        callback_data=callback_data
                    ))
            keyboard.append(row)

        # Add custom personalities
        if custom_personalities:
            # No separator button - just add custom personalities directly
            for i in range(0, len(custom_personalities), 2):
                row = []
                for j in range(2):
                    if i + j < len(custom_personalities):
                        p = custom_personalities[i + j]
                        callback_data = sign_callback_data(f"select_personality:{p.name}")
                        row.append(InlineKeyboardButton(
                            f"{p.emoji} {p.display_name}",
                            callback_data=callback_data
                        ))
                keyboard.append(row)

        # Add "Create custom personality" button (redirect to /lichnost)
        keyboard.append([InlineKeyboardButton(
            "➕ Создать свою личность",
            callback_data=sign_callback_data("create_personality")
        )])

        reply_markup = InlineKeyboardMarkup(keyboard)

        # Build text based on available personalities
        if custom_personalities:
            text = """🎭 Выбери личность для общения:

**Базовые личности:**
(первые {} варианта)

**Твои личности:**
(следующие {} варианта)""".format(len(base_personalities), len(custom_personalities))
        else:
            text = """🎭 Выбери личность для общения:

Каждая личность имеет свой уникальный стиль и подход к разговору."""

        if edit_message and update.callback_query:
            await update.callback_query.edit_message_text(
                text=text,
                reply_markup=reply_markup
            )
        else:
            await update.effective_message.reply_text(
                text=text,
                reply_markup=reply_markup
            )

        logger.info(f"Showed personality selection to user {user_id}")

    except Exception as e:
        logger.error(f"Error showing personality selection: {e}")
        await update.effective_message.reply_text(
            "❌ Ошибка при загрузке личностей. Попробуй /start"
        )


async def handle_personality_selection(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
) -> None:
    """
    Handle personality selection callback.
    Saves user's choice and sends personalized greeting.

    Args:
        update: Telegram update object with callback_query
        context: Bot context
    """
    query = update.callback_query
    await query.answer()

    try:
        # Verify HMAC signature
        if not verify_callback_data(query.data):
            await query.edit_message_text("❌ Неверная подпись данных. Попробуй /start")
            return

        # Extract callback data
        callback_data = query.data.split(":")[0] + ":" + query.data.split(":")[1]  # Remove HMAC
        _, personality_name = callback_data.rsplit(":", 1)

        user_id = update.effective_user.id
        username = update.effective_user.username

        # Get personality from DB
        personality = db_service.get_personality(personality_name)
        if not personality:
            await query.edit_message_text("❌ Личность не найдена. Попробуй /start")
            return

        # Save user's personality choice
        db_service.update_user_personality(user_id, personality_name, username)

        # Get or generate greeting
        greeting = personality.greeting_message
        if not greeting:
            # Generate greeting for custom personalities without pre-set greeting
            greeting = ai_service.generate_greeting(personality)

        # Send greeting
        greeting_text = f"✨ Выбрана личность: **{personality.display_name}** {personality.emoji}\n\n{greeting}\n\n💬 Теперь можешь писать мне - я буду отвечать в этом стиле!"

        await query.edit_message_text(greeting_text)

        # Log analytics
        db_service.log_event(
            user_id=user_id,
            chat_id=update.effective_chat.id,
            event_type="personality_selected",
            metadata={"personality": personality_name}
        )

        logger.info(f"User {user_id} selected personality '{personality_name}'")

    except Exception as e:
        logger.error(f"Error handling personality selection: {e}")
        await query.edit_message_text(
            "❌ Ошибка при выборе личности. Попробуй /start"
        )


async def handle_direct_message(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
) -> None:
    """
    Handle regular messages in direct chat with the bot.
    Generates contextual responses using the selected personality.

    Args:
        update: Telegram update object
        context: Bot context
    """
    # Only handle private chats
    if update.effective_chat.type != ChatType.PRIVATE:
        return

    user_id = update.effective_user.id
    chat_id = update.effective_chat.id
    username = update.effective_user.username
    message_text = update.message.text

    try:
        # Check if user has selected a personality
        personality_name = db_service.get_user_personality(user_id)
        if not personality_name or personality_name == config.DEFAULT_PERSONALITY:
            await update.message.reply_text(
                "🎭 Сначала выбери личность для общения!\n\n"
                "Используй команду /lichnost чтобы выбрать стиль общения."
            )
            return

        # Get personality from DB
        personality = db_service.get_personality(personality_name)
        if not personality:
            await update.message.reply_text(
                "❌ Личность не найдена. Выбери другую: /lichnost"
            )
            return

        # Save user's message
        db_service.save_message(chat_id, user_id, username, message_text)

        # Get chat history for context
        history = db_service.get_chat_history(
            chat_id=chat_id,
            user_id=user_id,
            limit=config.DIRECT_CHAT_CONTEXT_MESSAGES
        )

        # Generate response using AI
        response = ai_service.generate_chat_response(
            user_message=message_text,
            personality=personality,
            history=history
        )

        # Send response
        await update.message.reply_text(response)

        # Save bot's response
        db_service.save_message(
            chat_id=chat_id,
            user_id=None,  # Bot messages have user_id=None
            username="bot",
            message_text=response
        )

        # Log analytics
        db_service.log_event(
            user_id=user_id,
            chat_id=chat_id,
            event_type="direct_chat_message",
            metadata={"personality": personality_name}
        )

        logger.info(f"Handled direct message from user {user_id} with personality '{personality_name}'")

    except Exception as e:
        logger.error(f"Error handling direct message: {e}")
        await update.message.reply_text(
            "❌ Ошибка при генерации ответа. Попробуй ещё раз или /start"
        )


async def handle_create_personality_callback(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
) -> None:
    """
    Handle "Create personality" button click.
    Redirects user to /lichnost command for personality creation flow.

    Args:
        update: Telegram update object
        context: Bot context
    """
    query = update.callback_query
    await query.answer()

    try:
        # Verify HMAC signature
        if not verify_callback_data(query.data):
            await query.edit_message_text("❌ Неверная подпись данных.")
            return

        await query.edit_message_text(
            "🎨 Чтобы создать свою личность, используй команду:\n\n"
            "/lichnost\n\n"
            "Там ты сможешь выбрать 'Создать свою' и описать уникальный стиль!"
        )

        logger.info(f"User {update.effective_user.id} clicked create personality button")

    except Exception as e:
        logger.error(f"Error handling create personality callback: {e}")
        await query.edit_message_text("❌ Ошибка. Попробуй /lichnost")
