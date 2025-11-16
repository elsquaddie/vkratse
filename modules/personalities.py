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
from utils import (
    sanitize_personality_prompt,
    extract_user_description,
    is_valid_personality_name,
    build_personality_menu,
    get_current_personality_display
)

# Conversation states
AWAITING_NAME = 1
AWAITING_EMOJI = 2
AWAITING_DESCRIPTION = 3
AWAITING_EDIT_CHOICE = 4
AWAITING_EDIT_NAME = 5
AWAITING_EDIT_EMOJI = 6
AWAITING_EDIT_DESCRIPTION = 7


async def personality_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Handle /личность command
    Show personality selection with inline keyboard
    """
    user = update.effective_user
    db = DBService()

    # Get current personality
    current_personality_name = db.get_user_personality(user.id)
    current_display = get_current_personality_display(user.id)

    # Build menu using universal function (management context)
    reply_markup = build_personality_menu(
        user_id=user.id,
        callback_prefix="pers:select",
        context="manage",
        current_personality=current_personality_name,
        show_create_button=True
    )

    message_text = f"""🎭 Выбери личность AI

Текущая: {current_display}

Личность определяет стиль ответов бота на твои команды.

💡 Кастомные личности можно редактировать ✏️ или удалять 🗑️"""

    await update.message.reply_text(message_text, reply_markup=reply_markup)


async def personality_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """
    Handle callback from personality buttons

    Callback data formats:
    - pers:select:{name} - select personality
    - pers:create_start - start creation dialog
    - pers:delete:{name} - delete custom personality
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

    # Handle edit
    elif action == "edit":
        if len(parts) < 3:
            return ConversationHandler.END

        personality_name = parts[2]

        # Get personality info
        personality = db.get_personality(personality_name)
        if not personality:
            await query.answer("❌ Личность не найдена", show_alert=True)
            return ConversationHandler.END

        # Verify ownership
        if personality.created_by_user_id != user.id:
            await query.answer("❌ Можно редактировать только свои личности", show_alert=True)
            return ConversationHandler.END

        # Store personality name in context
        context.user_data['editing_personality'] = personality_name

        # Show edit menu
        keyboard = [
            [InlineKeyboardButton("✏️ Изменить название", callback_data=f"edit:name:{personality_name}")],
            [InlineKeyboardButton("🎨 Изменить эмодзи", callback_data=f"edit:emoji:{personality_name}")],
            [InlineKeyboardButton("📝 Изменить описание", callback_data=f"edit:description:{personality_name}")],
            [InlineKeyboardButton("❌ Отмена", callback_data="edit:cancel")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)

        await query.message.edit_text(
            f"✏️ Редактирование личности\n\n"
            f"🎭 {personality.emoji} {personality.display_name}\n\n"
            f"Что хочешь изменить?",
            reply_markup=reply_markup
        )
        return AWAITING_EDIT_CHOICE

    # Handle delete
    elif action == "delete":
        if len(parts) < 3:
            return ConversationHandler.END

        personality_name = parts[2]

        # Get personality info before deleting
        personality = db.get_personality(personality_name)
        if not personality:
            await query.answer("❌ Личность не найдена", show_alert=True)
            return ConversationHandler.END

        # Attempt to delete
        success = db.delete_personality(personality_name, user.id)

        if success:
            # If user had this personality selected, switch to default
            current_personality = db.get_user_personality(user.id)
            if current_personality == personality_name:
                db.update_user_personality(user.id, config.DEFAULT_PERSONALITY, user.username)

            await query.message.edit_text(
                f"✅ Личность \"{personality.display_name}\" удалена.\n\n"
                f"Используй /{config.COMMAND_PERSONALITY} чтобы выбрать другую."
            )
        else:
            await query.answer("❌ Не удалось удалить личность", show_alert=True)

        return ConversationHandler.END

    # No-op (section header)
    elif action == "noop":
        return ConversationHandler.END

    return ConversationHandler.END


async def receive_personality_name(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Receive personality name (step 1)"""

    user = update.effective_user
    name = update.message.text.strip().lower()


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

    # Check if user has reached the limit of custom personalities
    current_count = db.count_user_custom_personalities(user.id)
    if current_count >= config.MAX_CUSTOM_PERSONALITIES_PER_USER:
        await update.message.reply_text(
            f"❌ Достигнут лимит кастомных личностей ({config.MAX_CUSTOM_PERSONALITIES_PER_USER}).\n\n"
            f"Удали одну из существующих личностей через /{config.COMMAND_PERSONALITY}, "
            f"чтобы создать новую."
        )
        return ConversationHandler.END

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


    # Clear context
    context.user_data.clear()

    return ConversationHandler.END


async def edit_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """
    Handle edit choice callback

    Callback data format: edit:{field}:{personality_name} or edit:cancel
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

    # Handle cancel
    if action == "cancel":
        await query.message.edit_text(
            "❌ Редактирование отменено.\n\n"
            f"Используй /{config.COMMAND_PERSONALITY} для управления личностями."
        )
        context.user_data.clear()
        return ConversationHandler.END

    # Get personality name
    if len(parts) < 3:
        return ConversationHandler.END

    personality_name = parts[2]
    personality = db.get_personality(personality_name)

    if not personality:
        await query.message.edit_text("❌ Личность не найдена")
        return ConversationHandler.END

    # Store what we're editing
    context.user_data['editing_personality'] = personality_name
    context.user_data['editing_field'] = action

    # Handle name edit
    if action == "name":
        await query.message.edit_text(
            f"✏️ Изменение названия\n\n"
            f"Текущее название: {personality.display_name}\n\n"
            f"Введи новое название или /cancel для отмены."
        )
        return AWAITING_EDIT_NAME

    # Handle emoji edit
    elif action == "emoji":
        await query.message.edit_text(
            f"🎨 Изменение эмодзи\n\n"
            f"Текущий эмодзи: {personality.emoji}\n\n"
            f"Отправь новый эмодзи или /cancel для отмены."
        )
        return AWAITING_EDIT_EMOJI

    # Handle description edit
    elif action == "description":
        # Extract original user description (without wrapper)
        original_description = extract_user_description(personality.system_prompt)

        await query.message.edit_text(
            f"📝 Изменение описания\n\n"
            f"Текущее описание:\n{original_description}\n\n"
            f"Введи новое описание (от {config.MIN_PERSONALITY_DESCRIPTION_LENGTH} "
            f"до {config.MAX_PERSONALITY_DESCRIPTION_LENGTH} символов)\n\n"
            f"Или /cancel для отмены."
        )
        return AWAITING_EDIT_DESCRIPTION

    return ConversationHandler.END


async def receive_edited_name(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Receive new personality name"""
    user = update.effective_user
    new_name = update.message.text.strip().lower()
    personality_name = context.user_data.get('editing_personality')

    if not personality_name:
        await update.message.reply_text("❌ Ошибка: личность не найдена. Начни заново.")
        return ConversationHandler.END

    # Validate name
    is_valid, error_msg = is_valid_personality_name(new_name)
    if not is_valid:
        await update.message.reply_text(
            f"❌ {error_msg}\n\n"
            "Попробуй другое название или /cancel для отмены."
        )
        return AWAITING_EDIT_NAME

    # Check if name already exists (and it's not the current one)
    db = DBService()
    if new_name != personality_name and db.personality_exists(new_name):
        await update.message.reply_text(
            f"❌ Личность '{new_name}' уже существует.\n\n"
            "Попробуй другое название или /cancel для отмены."
        )
        return AWAITING_EDIT_NAME

    # Update personality
    success = db.update_personality(
        personality_name,
        user.id,
        display_name=new_name.capitalize()
    )

    if success:
        await update.message.reply_text(
            f"✅ Название изменено на: {new_name.capitalize()}\n\n"
            f"Используй /{config.COMMAND_PERSONALITY} для дальнейшего управления."
        )
    else:
        await update.message.reply_text("❌ Ошибка при обновлении. Попробуй позже.")

    context.user_data.clear()
    return ConversationHandler.END


async def receive_edited_emoji(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Receive new personality emoji"""
    user = update.effective_user
    new_emoji = update.message.text.strip()
    personality_name = context.user_data.get('editing_personality')

    if not personality_name:
        await update.message.reply_text("❌ Ошибка: личность не найдена. Начни заново.")
        return ConversationHandler.END

    # Validate emoji
    if len(new_emoji) > 10 or len(new_emoji) == 0:
        await update.message.reply_text(
            "❌ Пожалуйста, отправь только один эмодзи.\n\n"
            "Попробуй ещё раз или /cancel для отмены."
        )
        return AWAITING_EDIT_EMOJI

    # Update personality
    db = DBService()
    success = db.update_personality(
        personality_name,
        user.id,
        emoji=new_emoji
    )

    if success:
        await update.message.reply_text(
            f"✅ Эмодзи изменён на: {new_emoji}\n\n"
            f"Используй /{config.COMMAND_PERSONALITY} для дальнейшего управления."
        )
    else:
        await update.message.reply_text("❌ Ошибка при обновлении. Попробуй позже.")

    context.user_data.clear()
    return ConversationHandler.END


async def receive_edited_description(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Receive new personality description"""
    user = update.effective_user
    new_description = update.message.text.strip()
    personality_name = context.user_data.get('editing_personality')

    if not personality_name:
        await update.message.reply_text("❌ Ошибка: личность не найдена. Начни заново.")
        return ConversationHandler.END

    # Sanitize description
    try:
        safe_prompt = sanitize_personality_prompt(new_description)
    except ValueError as e:
        await update.message.reply_text(
            f"❌ {str(e)}\n\n"
            "Попробуй другое описание или /cancel для отмены."
        )
        return AWAITING_EDIT_DESCRIPTION

    # Update personality
    db = DBService()
    success = db.update_personality(
        personality_name,
        user.id,
        system_prompt=safe_prompt
    )

    if success:
        await update.message.reply_text(
            f"✅ Описание обновлено!\n\n"
            f"Используй /{config.COMMAND_PERSONALITY} для дальнейшего управления."
        )
    else:
        await update.message.reply_text("❌ Ошибка при обновлении. Попробуй позже.")

    context.user_data.clear()
    return ConversationHandler.END


async def cancel_personality_creation(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Cancel personality creation or editing"""

    await update.message.reply_text(
        "❌ Операция отменена.\n\n"
        f"Используй /{config.COMMAND_PERSONALITY} чтобы выбрать существующую."
    )

    context.user_data.clear()
    return ConversationHandler.END
