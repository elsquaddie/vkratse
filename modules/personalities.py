"""
Personality command (/личность)
Select AI personality and create custom ones
"""

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, ConversationHandler
from telegram.constants import ParseMode
import config
from config import logger
from services import DBService
from utils import sanitize_personality_prompt, is_valid_personality_name

# Conversation states
AWAITING_NAME = 1
AWAITING_EMOJI = 2
AWAITING_DESCRIPTION = 3


async def personality_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Handle /личность command
    Show personality selection with inline keyboard
    """
    user = update.effective_user
    db = DBService()

    logger.info(f"Personality command from user {user.id}")

    # 1. Get all personalities
    all_personalities = db.get_all_personalities()

    if not all_personalities:
        await update.message.reply_text("❌ Личности не найдены. Проверь БД.")
        return

    # 2. Split into base and custom (user's own)
    base_personalities = [p for p in all_personalities if not p.is_custom]
    custom_personalities = [
        p for p in all_personalities
        if p.is_custom and p.created_by_user_id == user.id
    ]

    # 3. Get current personality
    current_personality_name = db.get_user_personality(user.id)
    current_personality = db.get_personality(current_personality_name)
    current_display = current_personality.display_name if current_personality else "Нейтральный"

    # 4. Build keyboard
    keyboard = []

    # Base personalities in 2 columns
    row = []
    for p in base_personalities:
        button_text = f"{p.emoji} {p.display_name}"
        if p.name == current_personality_name:
            button_text += " ✓"  # Mark current

        row.append(InlineKeyboardButton(
            button_text,
            callback_data=f"pers:select:{p.name}"
        ))

        if len(row) == 2:
            keyboard.append(row)
            row = []

    if row:  # Add remaining
        keyboard.append(row)

    # Custom personalities
    if custom_personalities:
        keyboard.append([InlineKeyboardButton(
            "─── Мои личности ───",
            callback_data="pers:noop"
        )])

        for p in custom_personalities:
            button_text = f"🎭 {p.display_name}"
            if p.name == current_personality_name:
                button_text += " ✓"

            keyboard.append([InlineKeyboardButton(
                button_text,
                callback_data=f"pers:select:{p.name}"
            )])

    # Create button
    keyboard.append([InlineKeyboardButton(
        "➕ Создать свою личность",
        callback_data="pers:create_start"
    )])

    reply_markup = InlineKeyboardMarkup(keyboard)

    message_text = f"""🎭 Выбери личность AI

Текущая: {current_display}

Личность определяет стиль ответов бота на твои команды."""

    await update.message.reply_text(message_text, reply_markup=reply_markup)


async def personality_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """
    Handle callback from personality buttons

    Callback data formats:
    - pers:select:{name} - select personality
    - pers:create_start - start creation dialog
    - pers:noop - do nothing (section header)
    """
    query = update.callback_query
    user = query.from_user
    db = DBService()

    await query.answer()

    # Parse callback data
    parts = query.data.split(':')
    if len(parts) < 2:
        return ConversationHandler.END

    action = parts[1]

    # Handle selection
    if action == "select":
        if len(parts) < 3:
            return ConversationHandler.END

        personality_name = parts[2]

        # Update user settings
        db.update_user_personality(user.id, personality_name, user.username)

        personality = db.get_personality(personality_name)
        if personality:
            await query.message.edit_text(
                f"✅ Личность изменена на: {personality}\n\n"
                f"Теперь /{config.COMMAND_SUMMARY} и /{config.COMMAND_JUDGE} "
                f"будут отвечать в этом стиле."
            )
            logger.info(f"User {user.id} selected personality '{personality_name}'")
        else:
            await query.message.edit_text("❌ Личность не найдена")

        return ConversationHandler.END

    # Handle create start
    elif action == "create_start":
        await query.message.reply_text(
            "🎭 Создание своей личности\n\n"
            "Шаг 1 из 2\n\n"
            "Как назовём личность?\n\n"
            "💡 Примеры:\n"
            "• Пират\n"
            "• Мастер по ноготочкам\n"
            "• Космический ковбой\n\n"
            "Напиши название или /cancel для отмены."
        )
        return AWAITING_NAME

    # No-op (section header)
    elif action == "noop":
        return ConversationHandler.END

    return ConversationHandler.END


async def receive_personality_name(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Receive personality name (step 1)"""
    logger.info("🔥🔥🔥 receive_personality_name CALLED!")

    user = update.effective_user
    name = update.message.text.strip().lower()

    logger.info(f"User {user.id} proposed personality name: {name}")

    # Validate name
    is_valid, error_msg = is_valid_personality_name(name)
    if not is_valid:
        await update.message.reply_text(
            f"❌ {error_msg}\n\n"
            "Попробуй другое название или /cancel для отмены."
        )
        return AWAITING_NAME

    # Check if already exists
    db = DBService()
    if db.personality_exists(name):
        await update.message.reply_text(
            f"❌ Личность '{name}' уже существует.\n\n"
            "Попробуй другое название или /cancel для отмены."
        )
        return AWAITING_NAME

    # Save name in context
    context.user_data['personality_name'] = name
    context.user_data['personality_emoji'] = '🎭'  # Default emoji

    # Ask for description (skip emoji step)
    await update.message.reply_text(
        f"🎭 Создание личности \"{name}\"\n\n"
        f"Шаг 2 из 2\n\n"
        f"Опиши стиль общения этой личности.\n"
        f"(от {config.MIN_PERSONALITY_DESCRIPTION_LENGTH} до "
        f"{config.MAX_PERSONALITY_DESCRIPTION_LENGTH} символов)\n\n"
        f"💡 Пример:\n"
        f"Говорит как мастер маникюра, использует профессиональный жаргон "
        f"про формы ногтей, покрытия и дизайн. Дает советы по уходу за ногтями. "
        f"Дружелюбная и внимательная к деталям.\n\n"
        f"Напиши описание или /cancel для отмены."
    )

    return AWAITING_DESCRIPTION


async def receive_personality_emoji(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Receive personality emoji (step 2)"""
    user = update.effective_user
    emoji = update.message.text.strip()
    name = context.user_data.get('personality_name')

    if not name:
        await update.message.reply_text("❌ Ошибка: имя личности не найдено. Начни заново с /личность")
        return ConversationHandler.END

    logger.info(f"User {user.id} proposed emoji: {emoji} for personality '{name}'")

    # Validate emoji (should be 1-4 characters, allowing for complex emoji)
    if len(emoji) > 10 or len(emoji) == 0:
        await update.message.reply_text(
            "❌ Пожалуйста, отправь только один emoji.\n\n"
            "Попробуй ещё раз или /cancel для отмены."
        )
        return AWAITING_EMOJI

    # Save emoji in context
    context.user_data['personality_emoji'] = emoji

    # Ask for description
    await update.message.reply_text(
        f"🎭 Создание личности \"{name}\" {emoji}\n\n"
        f"Шаг 3 из 3\n\n"
        f"Опиши стиль общения этой личности.\n"
        f"(от {config.MIN_PERSONALITY_DESCRIPTION_LENGTH} до "
        f"{config.MAX_PERSONALITY_DESCRIPTION_LENGTH} символов)\n\n"
        f"💡 Пример:\n"
        f"Говорит как морской пират, использует слова \"йо-хо-хо\", "
        f"\"авось\", \"семь футов под килем\". Рассказывает про приключения "
        f"и сокровища. Весёлый и дружелюбный.\n\n"
        f"Напиши описание или /cancel для отмены."
    )

    return AWAITING_DESCRIPTION


async def receive_personality_description(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Receive personality description (step 3)"""
    user = update.effective_user
    description = update.message.text.strip()
    name = context.user_data.get('personality_name')
    emoji = context.user_data.get('personality_emoji', '🎭')

    if not name:
        await update.message.reply_text("❌ Ошибка: имя личности не найдено. Начни заново с /личность")
        return ConversationHandler.END

    logger.info(f"User {user.id} provided description for personality '{name}'")

    # Sanitize description
    try:
        safe_prompt = sanitize_personality_prompt(description)
    except ValueError as e:
        await update.message.reply_text(
            f"❌ {str(e)}\n\n"
            "Попробуй другое описание или /cancel для отмены."
        )
        return AWAITING_DESCRIPTION

    # Create personality
    db = DBService()
    personality_id = db.create_personality(
        name=name,
        display_name=name.capitalize(),
        system_prompt=safe_prompt,
        created_by_user_id=user.id,
        emoji=emoji
    )

    if not personality_id:
        await update.message.reply_text(
            "❌ Ошибка при создании личности. Попробуй позже."
        )
        return ConversationHandler.END

    # Auto-select new personality
    db.update_user_personality(user.id, name, user.username)

    # Success!
    await update.message.reply_text(
        f"✅ Личность \"{name.capitalize()}\" {emoji} создана и выбрана!\n\n"
        f"Теперь /{config.COMMAND_SUMMARY} и /{config.COMMAND_JUDGE} "
        f"будут отвечать в этом стиле.\n\n"
        f"Попробуй команду /{config.COMMAND_SUMMARY} в своём чате!"
    )

    logger.info(f"User {user.id} created personality '{name}' {emoji} (ID: {personality_id})")

    # Clear context
    context.user_data.clear()

    return ConversationHandler.END


async def cancel_personality_creation(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Cancel personality creation"""
    logger.info(f"User {update.effective_user.id} cancelled personality creation")

    await update.message.reply_text(
        "❌ Создание личности отменено.\n\n"
        f"Используй /{config.COMMAND_PERSONALITY} чтобы выбрать существующую."
    )

    context.user_data.clear()
    return ConversationHandler.END
