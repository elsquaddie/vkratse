"""
Direct Chat Module
Handles 1-on-1 conversations with the bot in private chats
"""

from typing import Optional
from datetime import datetime, timedelta
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from telegram.constants import ChatType

import config
from config import logger
from services.db_service import DBService
from services.ai_service import AIService
from services.subscription import SubscriptionService
from utils.security import sign_callback_data, verify_callback_data
from utils.upgrade_messages import show_upgrade_message


db_service = DBService()
ai_service = AIService()
subscription_service = SubscriptionService(db_service)


async def show_personality_selection(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    edit_message: bool = False,
    show_back_button: bool = False
) -> None:
    """
    Show personality selection menu to the user (unified version).

    Args:
        update: Telegram update object
        context: Bot context
        edit_message: If True, edit existing message; if False, send new message
        show_back_button: If True, show back button to main menu
    """
    try:
        from utils import build_personality_menu, save_personality_menu_context

        user_id = update.effective_user.id

        # Save context for later restoration after edit/delete
        save_personality_menu_context(
            user_id=user_id,
            callback_prefix="sel_pers",
            extra_data=None,
            bot_data=context.bot_data
        )

        # Build menu using universal function
        reply_markup = build_personality_menu(
            user_id=user_id,
            callback_prefix="sel_pers",
            context="select",
            current_personality=None,  # No checkmark - user always makes conscious choice
            show_create_button=True,
            show_back_button=show_back_button,
            back_callback="back_to_main"
        )

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

    except Exception as e:
        logger.error(f"Error showing personality selection: {e}", exc_info=True)
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

        # Extract callback data (format: "sel_pers:ID:HMAC")
        parts = query.data.split(":")
        if len(parts) < 2:
            await query.edit_message_text("❌ Неверный формат данных. Попробуй /start")
            return

        personality_id = int(parts[1])  # Extract ID

        user_id = update.effective_user.id
        username = update.effective_user.username

        # Get personality from DB by ID
        personality = db_service.get_personality_by_id(personality_id)
        if not personality:
            await query.edit_message_text("❌ Личность не найдена. Попробуй /start")
            return

        # Check if personality is blocked
        if personality.is_blocked:
            # Check if user is actually in the group now (force check to bypass cache)
            is_member = await subscription_service.is_in_project_group(
                user_id=user_id,
                bot=context.bot,
                force_check=True
            )

            if is_member:
                # User is back in the group! Unblock all their group bonus personalities
                logger.info(f"User {user_id} is in group, auto-unblocking personality {personality.id}")
                await db_service.unblock_group_bonus_personalities(user_id)

                # Refresh personality data to get updated is_blocked status
                personality = db_service.get_personality_by_id(personality_id)
                if not personality:
                    await query.edit_message_text("❌ Ошибка при обновлении личности. Попробуй /start")
                    return

                # Continue with normal flow (personality is now unblocked)
                logger.info(f"Personality {personality.id} unblocked, continuing with selection")
            else:
                # User is NOT in the group - show helpful message
                message_text = (
                    "🔒 Эта личность заблокирована.\n\n"
                    "**Причина:** ты вышел из группы проекта.\n\n"
                    "💡 **Как разблокировать:**\n"
                    "Вернись в группу, чтобы снова использовать эту личность!"
                )

                keyboard = []
                if config.PROJECT_GROUP_LINK:
                    keyboard.append([InlineKeyboardButton(
                        "🔗 Вернуться в группу",
                        url=config.PROJECT_GROUP_LINK
                    )])
                keyboard.append([InlineKeyboardButton(
                    "◀️ Назад к личностям",
                    callback_data=sign_callback_data("setup_personality")
                )])

                reply_markup = InlineKeyboardMarkup(keyboard)
                await query.edit_message_text(
                    text=message_text,
                    reply_markup=reply_markup
                )
                return

        # Save user's personality choice
        db_service.update_user_personality(user_id, personality.name, username)

        # Get or generate greeting
        greeting = personality.greeting_message
        if not greeting:
            # Generate greeting for custom personalities without pre-set greeting
            greeting = ai_service.generate_greeting(personality)

        # Send greeting with "Back to menu" button
        greeting_text = f"✨ Выбрана личность: {personality.display_name} {personality.emoji}\n\n{greeting}\n\n💬 Теперь можешь писать мне - я буду отвечать в этом стиле!"

        # Add inline keyboard with "Back to menu" button
        keyboard = [[InlineKeyboardButton(
            "◀️ Назад в меню",
            callback_data=sign_callback_data("back_to_main")
        )]]
        reply_markup = InlineKeyboardMarkup(keyboard)

        await query.edit_message_text(greeting_text, reply_markup=reply_markup)

        # Log analytics
        db_service.log_event(
            user_id=user_id,
            chat_id=update.effective_chat.id,
            event_type="personality_selected",
            metadata={"personality": personality.name}
        )

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
        # ================================================
        # MONETIZATION: Check usage limit for DM messages
        # ================================================
        limit_check = await subscription_service.check_usage_limit(user_id, 'messages_dm')

        if not limit_check['can_proceed']:
            # User has exceeded their daily message limit
            await show_upgrade_message(
                update=update,
                reason="Лимит сообщений исчерпан",
                tier=limit_check['tier'],
                limit_type='messages',
                current=limit_check['current'],
                limit=limit_check['limit']
            )
            return

        # Check if user has selected a personality
        personality_name = db_service.get_user_personality(user_id)
        if not personality_name:
            await update.message.reply_text(
                "🎭 Сначала выбери личность для общения!\n\n"
                f"Используй команду /{config.COMMAND_PERSONALITY} чтобы выбрать стиль общения."
            )
            return

        # Get personality from DB
        personality = db_service.get_personality(personality_name)
        if not personality:
            await update.message.reply_text(
                f"❌ Личность не найдена. Выбери другую: /{config.COMMAND_PERSONALITY}"
            )
            return

        # Check if personality is blocked
        if personality.is_blocked:
            # Check if user is actually in the group now (force check to bypass cache)
            is_member = await subscription_service.is_in_project_group(
                user_id=user_id,
                bot=context.bot,
                force_check=True
            )

            if is_member:
                # User is back in the group! Unblock all their group bonus personalities
                logger.info(f"User {user_id} is in group, auto-unblocking personalities")
                await db_service.unblock_group_bonus_personalities(user_id)

                # Refresh personality data to get updated is_blocked status
                personality = db_service.get_personality(personality_name)
                if not personality or personality.is_blocked:
                    await update.message.reply_text(
                        f"❌ Ошибка при обновлении личности. Попробуй выбрать другую: /{config.COMMAND_PERSONALITY}"
                    )
                    return

                # Continue with normal flow (personality is now unblocked)
                logger.info(f"Personality {personality.name} unblocked, continuing with message handling")
            else:
                # User is NOT in the group - show helpful message with button
                message_text = (
                    "🔒 Выбранная личность заблокирована.\n\n"
                    "**Причина:** ты вышел из группы проекта.\n\n"
                    "💡 **Что делать:**\n"
                    "• Вернись в группу, чтобы разблокировать личность\n"
                    f"• Или выбери другую личность: /{config.COMMAND_PERSONALITY}"
                )

                keyboard = []
                if config.PROJECT_GROUP_LINK:
                    keyboard.append([InlineKeyboardButton(
                        "🔗 Вернуться в группу",
                        url=config.PROJECT_GROUP_LINK
                    )])
                keyboard.append([InlineKeyboardButton(
                    "🎭 Выбрать другую личность",
                    callback_data=sign_callback_data("setup_personality")
                )])

                reply_markup = InlineKeyboardMarkup(keyboard)
                await update.message.reply_text(
                    text=message_text,
                    reply_markup=reply_markup
                )
                return

        # ================================================
        # MONETIZATION: Check personality usage limit for chat
        # ================================================
        personality_check = await subscription_service.check_personality_limit(
            user_id=user_id,
            personality=personality.name,
            action='chat'
        )

        if not personality_check['can_proceed']:
            # User has exceeded personality usage limit
            await update.message.reply_text(
                f"⚠️ Лимит использования личности '{personality.display_name}' исчерпан "
                f"({personality_check['current']}/{personality_check['limit']}).\n\n"
                f"💎 Pro-подписка дает безлимитное использование всех личностей!\n"
                f"Узнать больше: /premium"
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

        # ================================================
        # MONETIZATION: Increment usage counter after successful response
        # ================================================
        await subscription_service.increment_usage(user_id, 'messages_dm')

        # Increment personality usage counter
        await subscription_service.increment_personality_usage(
            user_id=user_id,
            personality=personality.name,
            action='chat'
        )

        # Log analytics
        db_service.log_event(
            user_id=user_id,
            chat_id=chat_id,
            event_type="direct_chat_message",
            metadata={"personality": personality_name}
        )

    except Exception as e:
        logger.error(f"Error handling direct message: {e}")
        await update.message.reply_text(
            "❌ Ошибка при генерации ответа. Попробуй ещё раз или /start"
        )


async def chat_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Handle /chat command - unified personality selection for all chat types.

    In groups: Start chat session with selected personality
    In DM: Show personality selection menu (same as /lichnost for chat context)

    Args:
        update: Telegram update object
        context: Bot context
    """
    user = update.effective_user
    chat = update.effective_chat

    try:
        from utils import build_personality_menu, save_personality_menu_context

        # In DM: show unified personality selection menu
        if chat.type == ChatType.PRIVATE:
            # Save context for later restoration after edit/delete
            save_personality_menu_context(
                user_id=user.id,
                callback_prefix="sel_pers",
                extra_data=None,
                bot_data=context.bot_data
            )

            reply_markup = build_personality_menu(
                user_id=user.id,
                callback_prefix="sel_pers",
                context="select",
                current_personality=None,  # No checkmark
                show_create_button=True,  # UNIFIED: same as all other contexts
                show_back_button=True,  # UNIFIED: show back button everywhere
                back_callback="back_to_main"
            )

            text = (
                "🎭 Выбери личность для общения:\n\n"
                "💬 После выбора можешь просто писать мне сообщения - "
                "я буду отвечать в выбранном стиле!"
            )

            await update.message.reply_text(text, reply_markup=reply_markup)
            return

        # In groups: show unified personality selection menu for session
        # Save context for later restoration after edit/delete
        save_personality_menu_context(
            user_id=user.id,
            callback_prefix="start_chat",
            extra_data={"user_id": user.id},
            bot_data=context.bot_data
        )

        reply_markup = build_personality_menu(
            user_id=user.id,
            callback_prefix="start_chat",
            context="select",
            current_personality=None,  # No checkmark
            extra_callback_data={"user_id": user.id},  # Include initiator's user_id
            show_create_button=True,  # UNIFIED: allow creating personalities from any command
            show_back_button=True,  # UNIFIED: show back button everywhere
            back_callback="back_to_main"
        )

        # Build text
        text = (
            "🎭 Выбери личность для общения в этом чате:\n\n"
            "💬 После выбора я буду отвечать только на твои сообщения "
            "(через reply или @упоминание)"
        )

        await update.message.reply_text(text, reply_markup=reply_markup)

    except Exception as e:
        logger.error(f"Error in chat_command: {e}")
        await update.message.reply_text(
            "❌ Ошибка при загрузке личностей. Попробуй ещё раз."
        )


async def stop_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Handle /stop command to end active chat session in groups.

    Args:
        update: Telegram update object
        context: Bot context
    """
    user = update.effective_user
    chat = update.effective_chat

    # Only work in groups
    if chat.type == ChatType.PRIVATE:
        await update.message.reply_text(
            "В личных сообщениях нет активных сессий для завершения."
        )
        return

    # Check if session exists
    if 'group_chat_sessions' not in context.bot_data:
        await update.message.reply_text(
            f"❌ У тебя нет активной сессии.\n"
            f"Начни сессию: /{config.COMMAND_CHAT}"
        )
        return

    session_key = (chat.id, user.id)
    session = context.bot_data['group_chat_sessions'].get(session_key)

    if not session:
        await update.message.reply_text(
            f"❌ У тебя нет активной сессии.\n"
            f"Начни сессию: /{config.COMMAND_CHAT}"
        )
        return

    # End session
    del context.bot_data['group_chat_sessions'][session_key]

    # Log analytics
    db_service.log_event(
        user_id=user.id,
        chat_id=chat.id,
        event_type="group_chat_session_ended",
        metadata={"personality": session['personality']}
    )

    await update.message.reply_text(
        f"✅ Сессия завершена.\n\n"
        f"Начать новую: /{config.COMMAND_CHAT}"
    )


async def handle_start_chat_callback(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
) -> None:
    """
    Handle callback when user selects personality for group chat session.
    Creates an active session and sends greeting message.

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

        # Extract callback data (format: "start_chat:personality_id:user_id:HMAC")
        parts = query.data.split(":")
        if len(parts) < 3:
            await query.edit_message_text("❌ Неверный формат данных.")
            return

        personality_id = int(parts[1])
        expected_user_id = int(parts[2])
        actual_user_id = query.from_user.id
        chat_id = query.message.chat_id

        # Security check: ensure the callback is from the same user who initiated /chat
        if actual_user_id != expected_user_id:
            await query.answer("❌ Эта кнопка предназначена для другого пользователя.", show_alert=True)
            return

        # Get personality from DB
        personality = db_service.get_personality_by_id(personality_id)
        if not personality:
            await query.edit_message_text("❌ Личность не найдена.")
            return

        # Create active session in bot_data (in-memory storage)
        # Format: context.bot_data['group_chat_sessions'] = {(chat_id, user_id): {'personality': name, 'started_at': timestamp}}
        if 'group_chat_sessions' not in context.bot_data:
            context.bot_data['group_chat_sessions'] = {}

        session_key = (chat_id, actual_user_id)
        context.bot_data['group_chat_sessions'][session_key] = {
            'personality': personality.name,
            'started_at': datetime.now()
        }

        # Generate greeting
        greeting = personality.greeting_message
        if not greeting:
            greeting = ai_service.generate_greeting(personality)

        # Send session started message with "End session" button
        response_text = (
            f"✅ Начата сессия общения с {personality.display_name} {personality.emoji}\n\n"
            f"{greeting}\n\n"
            f"💬 Пиши мне через reply на мои сообщения или @упоминание.\n"
            f"⏱️ Сессия автоматически завершится через {config.DIRECT_CHAT_SESSION_TIMEOUT // 60} минут."
        )

        # Add inline keyboard with "End session" button
        # Note: Only the user who started the session can click this button (checked by user_id)
        from utils.security import sign_callback_data
        keyboard = [[InlineKeyboardButton(
            "🛑 Завершить сессию",
            callback_data=sign_callback_data(f"end_group_chat:{actual_user_id}")
        )]]
        reply_markup = InlineKeyboardMarkup(keyboard)

        await query.edit_message_text(response_text, reply_markup=reply_markup)

        # Log analytics
        db_service.log_event(
            user_id=actual_user_id,
            chat_id=chat_id,
            event_type="group_chat_session_started",
            metadata={"personality": personality.name}
        )

    except Exception as e:
        logger.error(f"Error handling start_chat callback: {e}")
        await query.edit_message_text(
            "❌ Ошибка при создании сессии. Попробуй ещё раз."
        )


async def handle_group_chat_message(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
) -> None:
    """
    Handle messages in group chats during active chat sessions.
    Only responds to messages from users with active sessions.

    Args:
        update: Telegram update object
        context: Bot context
    """
    # Only handle group messages
    if update.effective_chat.type not in [ChatType.GROUP, ChatType.SUPERGROUP]:
        return

    user_id = update.effective_user.id
    chat_id = update.effective_chat.id
    message = update.message

    # Check if there's an active session
    if 'group_chat_sessions' not in context.bot_data:
        return

    session_key = (chat_id, user_id)
    session = context.bot_data['group_chat_sessions'].get(session_key)

    if not session:
        # No active session for this user
        return

    # Check session timeout (15 minutes)
    session_age = datetime.now() - session['started_at']
    if session_age > timedelta(seconds=config.DIRECT_CHAT_SESSION_TIMEOUT):
        # Session expired
        del context.bot_data['group_chat_sessions'][session_key]
        await message.reply_text(
            f"⏱️ Сессия завершена (таймаут {config.DIRECT_CHAT_SESSION_TIMEOUT // 60} минут).\n"
            f"Начни новую: /{config.COMMAND_CHAT}"
        )
        return

    # Check if message is addressed to bot (reply or mention)
    is_reply_to_bot = (
        message.reply_to_message and
        message.reply_to_message.from_user and
        message.reply_to_message.from_user.id == context.bot.id
    )
    is_mention = f"@{context.bot.username}" in message.text if message.text else False

    if not is_reply_to_bot and not is_mention:
        # Message not addressed to bot
        return

    try:
        # Get personality
        personality = db_service.get_personality(session['personality'])
        if not personality:
            await message.reply_text("❌ Ошибка: личность не найдена.")
            return

        # Get chat history for context
        history = db_service.get_chat_history(
            chat_id=chat_id,
            user_id=user_id,
            limit=config.DIRECT_CHAT_CONTEXT_MESSAGES
        )

        # Generate response
        response = ai_service.generate_chat_response(
            user_message=message.text,
            personality=personality,
            history=history
        )

        # Send response
        await message.reply_text(response)

        # Update session activity timestamp
        session['started_at'] = datetime.now()

        # Log analytics
        db_service.log_event(
            user_id=user_id,
            chat_id=chat_id,
            event_type="group_chat_message",
            metadata={"personality": session['personality']}
        )

    except Exception as e:
        logger.error(f"Error handling group chat message: {e}")
        await message.reply_text(
            "❌ Ошибка при генерации ответа. Попробуй ещё раз."
        )


async def handle_end_group_chat_callback(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
) -> None:
    """
    Handle "End session" button click in group chats.
    Only the user who started the session can end it.

    Args:
        update: Telegram update object
        context: Bot context
    """
    query = update.callback_query
    await query.answer()

    try:
        # Verify HMAC signature
        if not verify_callback_data(query.data):
            await query.answer("❌ Неверная подпись данных.", show_alert=True)
            return

        # Extract user_id from callback_data (format: "end_group_chat:user_id:HMAC")
        parts = query.data.split(":")
        if len(parts) < 2:
            await query.answer("❌ Неверный формат данных.", show_alert=True)
            return

        session_user_id = int(parts[1])
        actual_user_id = query.from_user.id
        chat_id = query.message.chat_id

        # Security check: only the user who started the session can end it
        if actual_user_id != session_user_id:
            await query.answer("❌ Эта сессия принадлежит другому пользователю.", show_alert=True)
            return

        # Check if session exists
        if 'group_chat_sessions' not in context.bot_data:
            await query.edit_message_text("❌ Сессия уже завершена.")
            return

        session_key = (chat_id, actual_user_id)
        session = context.bot_data['group_chat_sessions'].get(session_key)

        if not session:
            await query.edit_message_text("❌ Сессия уже завершена.")
            return

        # End session
        del context.bot_data['group_chat_sessions'][session_key]

        # Log analytics
        db_service.log_event(
            user_id=actual_user_id,
            chat_id=chat_id,
            event_type="group_chat_session_ended",
            metadata={"personality": session['personality']}
        )

        await query.edit_message_text(
            f"✅ Сессия завершена.\n\n"
            f"Начать новую: /{config.COMMAND_CHAT}"
        )

    except Exception as e:
        logger.error(f"Error handling end group chat callback: {e}")
        await query.answer("❌ Ошибка при завершении сессии.", show_alert=True)


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
            f"/{config.COMMAND_PERSONALITY}\n\n"
            "Там ты сможешь выбрать 'Создать свою' и описать уникальный стиль!"
        )

    except Exception as e:
        logger.error(f"Error handling create personality callback: {e}")
        await query.edit_message_text(f"❌ Ошибка. Попробуй /{config.COMMAND_PERSONALITY}")
