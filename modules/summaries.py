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
    create_string_signature, verify_string_signature,
    validate_chat_access,
    parse_time_argument, get_default_period,
    build_personality_menu
)


def _build_timeframe_menu(user_id: int, chat_id: int, personality_id: int) -> InlineKeyboardMarkup:
    """
    Build inline keyboard with timeframe selection.

    Args:
        user_id: User ID for HMAC signature
        chat_id: Chat ID for callback data
        personality_id: Selected personality ID

    Returns:
        InlineKeyboardMarkup with timeframe buttons
    """
    from utils.security import sign_callback_data

    timeframes = [
        ("📝 50 сообщений", "50"),
        ("📝 100 сообщений", "100"),
        ("📝 200 сообщений", "200"),
        ("📝 500 сообщений", "500"),
        ("⏰ 1 час", "1h"),
        ("⏰ 2 часа", "2h"),
        ("⏰ 6 часов", "6h"),
        ("⏰ 12 часов", "12h"),
        ("📅 Сегодня", "today"),
    ]

    keyboard = []
    row = []

    for label, value in timeframes:
        # Callback format: summary_timeframe:<chat_id>:<personality_id>:<timeframe>:<signature>
        callback_base = f"{chat_id}:{personality_id}:{value}"
        signature = create_string_signature(callback_base, user_id)
        callback_data = f"summary_timeframe:{callback_base}:{signature}"

        row.append(InlineKeyboardButton(label, callback_data=callback_data))

        # 2 buttons per row
        if len(row) == 2:
            keyboard.append(row)
            row = []

    # Add last row if odd number
    if row:
        keyboard.append(row)

    # Add back button to return to personality selection
    # Callback format: back_to_summary_personality:<chat_id>:<signature>
    back_callback_base = f"{chat_id}"
    back_signature = create_string_signature(back_callback_base, user_id)
    back_callback = f"back_to_summary_personality:{back_callback_base}:{back_signature}"

    keyboard.append([InlineKeyboardButton(
        "◀️ Назад",
        callback_data=back_callback
    )])

    return InlineKeyboardMarkup(keyboard)


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
    """Handle /summary in a group chat - show personality selection menu"""
    user = update.effective_user
    chat = update.effective_chat
    db = DBService()

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

    # 3. Parse custom limit argument (if provided)
    custom_limit = None
    if context.args:
        try:
            custom_limit = str(int(context.args[0]))  # Validate it's a number
            logger.info(f"Custom message limit: {custom_limit}")
        except ValueError:
            await update.message.reply_text(
                f"❌ Неверный формат. Используй число сообщений:\n\n"
                f"Примеры:\n"
                f"/{config.COMMAND_SUMMARY} 100\n"
                f"/{config.COMMAND_SUMMARY} 200"
            )
            return

    # 4. Show personality selection menu using universal builder
    # Note: We don't pass current_personality to avoid confusing checkmark
    # in summary context (user's default personality is for direct chat)
    keyboard = build_personality_menu(
        user_id=user.id,
        callback_prefix="summary_personality",
        context="select",
        current_personality=None,  # No checkmark in summary context
        extra_callback_data={"chat_id": chat.id, "limit": custom_limit or "none"},
        show_create_button=False  # Don't show create button in summary context
    )

    await update.message.reply_text(
        "🎭 Выбери личность для саммари:",
        reply_markup=keyboard
    )

    logger.info(f"Showed personality menu to user {user.id} in chat {chat.id}")


async def _summary_in_dm(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /sut in DM - show chat selection"""
    user = update.effective_user
    db = DBService()

    # 1. Получить все чаты из БД
    all_chats = db.get_all_chats()

    if not all_chats:
        await update.message.reply_text(
            "📭 Бот пока не добавлен ни в один чат.\n\n"
            "Добавь меня в групповой чат, чтобы я мог делать саммари!"
        )
        return

    # 2. Фильтровать чаты где юзер является участником
    user_chats = []
    for chat in all_chats:
        # Проверка членства через Telegram API
        ok, _ = await validate_chat_access(context.bot, chat.chat_id, user.id)
        if ok:
            user_chats.append(chat)

    if not user_chats:
        await update.message.reply_text(
            "📭 У нас нет общих чатов.\n\n"
            "Добавь меня в чат, где ты состоишь!"
        )
        return

    # 3. Создать inline кнопки для каждого чата
    keyboard = []
    for chat in user_chats:
        # HMAC подпись для безопасности
        signature = create_signature(chat.chat_id, user.id)
        callback_data = f"summary:{chat.chat_id}:{signature}"

        # Эмодзи из модели Chat
        button_text = f"{chat.emoji} {chat.chat_title or 'Чат'}"

        keyboard.append([InlineKeyboardButton(
            button_text,
            callback_data=callback_data
        )])

    reply_markup = InlineKeyboardMarkup(keyboard)

    await update.message.reply_text(
        "📋 Выбери чат для саммари:",
        reply_markup=reply_markup
    )


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


async def summary_personality_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Handle personality selection callback.

    Callback data format: summary_personality:<chat_id>:<personality_id>:<custom_limit_or_none>:<signature>

    If custom_limit is provided -> execute summary immediately
    If custom_limit is "none" -> show timeframe menu
    """
    query = update.callback_query
    user = query.from_user
    db = DBService()

    await query.answer()

    # Parse callback data
    try:
        _, chat_id_str, personality_id_str, custom_limit, signature = query.data.split(':')
        chat_id = int(chat_id_str)
        personality_id = int(personality_id_str)
    except (ValueError, IndexError) as e:
        await query.message.reply_text("❌ Неверные данные кнопки")
        logger.error(f"Error parsing personality callback: {e}")
        return

    # Verify signature
    callback_base = f"{chat_id}:{personality_id}:{custom_limit}"
    if not verify_string_signature(callback_base, user.id, signature):
        await query.message.reply_text("❌ Неверная подпись. Попробуй заново.")
        logger.error(f"Invalid signature for summary_personality: callback_base='{callback_base}', user_id={user.id}")
        return

    # Get personality
    personality = db.get_personality_by_id(personality_id)
    if not personality:
        await query.message.reply_text("❌ Личность не найдена.")
        logger.error(f"Personality {personality_id} not found")
        return

    # If custom limit provided -> execute summary immediately
    if custom_limit != "none":
        try:
            limit = int(custom_limit)
            await _execute_summary(
                query=query,
                user=user,
                chat_id=chat_id,
                personality=personality,
                timeframe=str(limit),
                context=context
            )
        except ValueError:
            await query.message.reply_text("❌ Неверный формат количества сообщений.")
        return

    # Otherwise -> show timeframe menu
    keyboard = _build_timeframe_menu(user.id, chat_id, personality_id)

    await query.message.edit_text(
        f"🎭 Личность: {personality.emoji} {personality.display_name}\n\n"
        f"⏰ Выбери период для саммари:",
        reply_markup=keyboard
    )

    logger.info(f"User {user.id} selected personality {personality.name} for chat {chat_id}")


async def summary_timeframe_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Handle timeframe selection callback.

    Callback data format: summary_timeframe:<chat_id>:<personality_id>:<timeframe>:<signature>

    Execute summary with selected personality and timeframe.
    """
    query = update.callback_query
    user = query.from_user
    db = DBService()

    await query.answer()

    # Parse callback data
    try:
        _, chat_id_str, personality_id_str, timeframe, signature = query.data.split(':')
        chat_id = int(chat_id_str)
        personality_id = int(personality_id_str)
    except (ValueError, IndexError) as e:
        await query.message.reply_text("❌ Неверные данные кнопки")
        logger.error(f"Error parsing timeframe callback: {e}")
        return

    # Verify signature
    callback_base = f"{chat_id}:{personality_id}:{timeframe}"
    if not verify_string_signature(callback_base, user.id, signature):
        await query.message.reply_text("❌ Неверная подпись. Попробуй заново.")
        logger.error(f"Invalid signature for summary_timeframe: callback_base='{callback_base}', user_id={user.id}")
        return

    # Get personality
    personality = db.get_personality_by_id(personality_id)
    if not personality:
        await query.message.reply_text("❌ Личность не найдена.")
        logger.error(f"Personality {personality_id} not found")
        return

    # Execute summary
    await _execute_summary(
        query=query,
        user=user,
        chat_id=chat_id,
        personality=personality,
        timeframe=timeframe,
        context=context
    )


async def _execute_summary(
    query,
    user,
    chat_id: int,
    personality,
    timeframe: str,
    context: ContextTypes.DEFAULT_TYPE
) -> None:
    """
    Execute summary generation with given parameters.

    Args:
        query: CallbackQuery object
        user: User object
        chat_id: Chat ID to summarize
        personality: Personality object
        timeframe: Timeframe string (e.g., "50", "100", "1h", "2h", "today")
        context: Bot context
    """
    db = DBService()
    ai = AIService()

    # Parse timeframe
    if timeframe.isdigit():
        # Number of messages
        limit = int(timeframe)
        since = None
        period_desc = f"последние {limit} сообщений"
    else:
        # Time-based (1h, 2h, today)
        since, period_desc = parse_time_argument(timeframe)
        if since is None:
            await query.message.reply_text(f"❌ Неверный формат времени: {period_desc}")
            return
        limit = config.MAX_MESSAGES_PER_SUMMARY

    # Get messages
    messages = db.get_messages(
        chat_id=chat_id,
        since=since,
        limit=limit
    )

    if not messages:
        await query.message.edit_text(f"📭 Нет сообщений за период: {period_desc}")
        return

    # Generate summary
    await query.message.edit_text(
        f"⏳ Генерирую саммари...\n\n"
        f"🎭 Личность: {personality.emoji} {personality.display_name}\n"
        f"📊 Период: {period_desc}"
    )

    try:
        summary = ai.generate_summary(messages, personality, period_desc)

        # Send summary
        await query.message.edit_text(
            f"📝 Саммари готово!\n\n"
            f"🎭 {personality.emoji} {personality.display_name}\n"
            f"📊 {period_desc}\n"
            f"💬 Сообщений: {len(messages)}\n\n"
            f"{summary}"
        )

        # Set cooldown
        set_cooldown(chat_id, 'summary')

        # Log event
        db.log_event(user.id, chat_id, 'summary', {
            'period': period_desc,
            'message_count': len(messages),
            'personality': personality.name
        })

        logger.info(f"Generated summary for chat {chat_id} ({len(messages)} messages) with personality {personality.name}")

    except Exception as e:
        logger.error(f"Error generating summary: {e}")
        await query.message.edit_text(
            f"❌ Ошибка при генерации саммари. Попробуй позже.\n\n"
            f"Детали: {str(e)[:100]}"
        )


async def back_to_summary_personality_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Handle back button from timeframe menu to return to personality selection.

    Callback data format: back_to_summary_personality:<chat_id>:<signature>
    """
    query = update.callback_query
    user = query.from_user
    db = DBService()

    await query.answer()

    # Parse callback data
    try:
        _, chat_id_str, signature = query.data.split(':')
        chat_id = int(chat_id_str)
    except (ValueError, IndexError) as e:
        await query.message.edit_text("❌ Неверные данные кнопки")
        logger.error(f"Error parsing back_to_summary_personality callback: {e}")
        return

    # Verify signature
    callback_base = f"{chat_id}"
    if not verify_string_signature(callback_base, user.id, signature):
        await query.message.edit_text("❌ Неверная подпись. Попробуй заново.")
        logger.error(f"Invalid signature for back_to_summary_personality: callback_base='{callback_base}', user_id={user.id}")
        return

    # Show personality selection menu again
    # Note: We don't pass current_personality to avoid confusing checkmark
    keyboard = build_personality_menu(
        user_id=user.id,
        callback_prefix="summary_personality",
        context="select",
        current_personality=None,  # No checkmark in summary context
        extra_callback_data={"chat_id": chat_id, "limit": "none"},
        show_create_button=False
    )

    await query.message.edit_text(
        "🎭 Выбери личность для саммари:",
        reply_markup=keyboard
    )

    logger.info(f"User {user.id} returned to personality selection for summary in chat {chat_id}")
