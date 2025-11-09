"""
Summary command (/суть)
Generate chat summaries with AI
"""

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from telegram.constants import ChatType
import config
from config import logger
from services import DBService, AIService
from utils import (
    check_cooldown, set_cooldown,
    check_rate_limit,
    create_signature, verify_signature,
    validate_chat_access,
    parse_time_argument, get_default_period
)


async def summary_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Handle /суть command

    In groups: Generate summary directly
    In DM: Show chat selection buttons
    """
    user = update.effective_user
    chat = update.effective_chat

    logger.info(f"Summary command from user {user.id} in chat {chat.id} ({chat.type})")

    # Check if in DM
    if chat.type == ChatType.PRIVATE:
        await _summary_in_dm(update, context)
    else:
        await _summary_in_group(update, context)


async def _summary_in_group(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /суть in a group chat"""
    user = update.effective_user
    chat = update.effective_chat
    db = DBService()
    ai = AIService()

    # 1. Rate limit check
    ok, remaining = check_rate_limit(user.id)
    if not ok:
        await update.message.reply_text(
            f"⏰ Слишком много запросов. Подожди {remaining} секунд."
        )
        return

    # 2. Cooldown check
    ok, remaining = check_cooldown(chat.id, 'summary')
    if not ok:
        await update.message.reply_text(
            f"⏰ Чат на кулдауне. Подожди {remaining} секунд."
        )
        return

    # 3. Parse time argument
    since, period_desc = get_default_period()

    if context.args:
        arg = context.args[0]
        parsed_since, parsed_desc = parse_time_argument(arg)

        if parsed_since is None:
            await update.message.reply_text(
                f"❌ Неверный формат времени: {parsed_desc}\n\n"
                f"Примеры:\n"
                f"/{config.COMMAND_SUMMARY} 30м\n"
                f"/{config.COMMAND_SUMMARY} 6ч\n"
                f"/{config.COMMAND_SUMMARY} сегодня"
            )
            return

        since = parsed_since
        period_desc = parsed_desc

    # 4. Get messages
    messages = db.get_messages(
        chat_id=chat.id,
        since=since,
        limit=config.MAX_MESSAGES_PER_SUMMARY
    )

    if not messages:
        await update.message.reply_text(
            f"📭 Нет сообщений {period_desc}."
        )
        return

    # 5. Get user's personality
    personality_name = db.get_user_personality(user.id)
    personality = db.get_personality(personality_name)

    if not personality:
        logger.error(f"Personality '{personality_name}' not found, using default")
        personality = db.get_personality(config.DEFAULT_PERSONALITY)

    # 6. Generate summary
    await update.message.reply_text("⏳ Генерирую саммари...")

    summary = ai.generate_summary(messages, personality, period_desc)

    # 7. Send summary
    await update.message.reply_text(summary)

    # 8. Set cooldown
    set_cooldown(chat.id, 'summary')

    # 9. Log event
    db.log_event(user.id, chat.id, 'summary', {
        'period': period_desc,
        'message_count': len(messages),
        'personality': personality_name
    })

    logger.info(f"Generated summary for chat {chat.id} ({len(messages)} messages)")


async def _summary_in_dm(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /суть in DM - show chat selection"""
    user = update.effective_user
    db = DBService()

    # Get all chats where bot is present
    # Note: We need to query Telegram API for this, not DB
    # For now, we'll query chats from chat_metadata table
    # TODO: Implement proper chat discovery via Telegram API

    await update.message.reply_text(
        "🔍 Функция выбора чата в ЛС будет доступна в следующей версии!\n\n"
        "Пока используй команду прямо в групповых чатах."
    )

    # Future implementation:
    # 1. Get all chats from chat_metadata
    # 2. Validate bot and user membership
    # 3. Show inline keyboard with chat buttons
    # 4. Each button has callback_data with HMAC signature


async def summary_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Handle callback from chat selection buttons

    Callback data format: summary:{chat_id}:{signature}
    """
    query = update.callback_query
    user = query.from_user
    db = DBService()
    ai = AIService()

    await query.answer()

    # Parse callback data
    try:
        _, chat_id_str, signature = query.data.split(':')
        chat_id = int(chat_id_str)
    except (ValueError, IndexError):
        await query.message.reply_text("❌ Неверные данные кнопки")
        return

    # 1. Verify signature
    if not verify_signature(chat_id, user.id, signature):
        await query.message.reply_text("❌ Неверная подпись. Попробуй заново.")
        return

    # 2. Validate access
    ok, error = await validate_chat_access(context.bot, chat_id, user.id)
    if not ok:
        await query.message.reply_text(error)
        return

    # 3. Rate limit check
    ok, remaining = check_rate_limit(user.id)
    if not ok:
        await query.message.reply_text(
            f"⏰ Слишком много запросов. Подожди {remaining} секунд."
        )
        return

    # 4. Get messages (default period)
    since, period_desc = get_default_period()
    messages = db.get_messages(
        chat_id=chat_id,
        since=since,
        limit=config.MAX_MESSAGES_PER_SUMMARY
    )

    if not messages:
        await query.message.reply_text(f"📭 Нет сообщений {period_desc}.")
        return

    # 5. Get personality
    personality_name = db.get_user_personality(user.id)
    personality = db.get_personality(personality_name)

    if not personality:
        personality = db.get_personality(config.DEFAULT_PERSONALITY)

    # 6. Generate summary
    await query.message.reply_text("⏳ Генерирую саммари...")

    summary = ai.generate_summary(messages, personality, period_desc)

    # 7. Send summary in DM
    await query.message.reply_text(f"📝 Саммари чата:\n\n{summary}")

    # 8. Log event
    db.log_event(user.id, chat_id, 'summary_dm', {
        'period': period_desc,
        'message_count': len(messages),
        'personality': personality_name
    })

    logger.info(f"Generated DM summary for user {user.id}, chat {chat_id}")
