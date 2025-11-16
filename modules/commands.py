"""
Basic bot commands
/start and /help
"""

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from telegram.constants import ChatType
import config
from config import logger
from utils.security import sign_callback_data


async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Handle /start command
    Show welcome message with inline menu for action selection
    """
    user = update.effective_user
    chat_type = update.effective_chat.type

    # Unified welcome message for all chat types
    welcome_text = f"""👋 Привет, {user.first_name}!

Я бот с разными личностями.

Могу стать быдлом и пояснить за базар, могу превратиться в олигарха и обкашлять вопросик, могу стать философом и покопаться в смыслах, а могу зумером - лениться и стонать.

Короче, что хочешь - то и будет! 🎭

Что мне сделать?"""

    # Different buttons for private vs group chats
    if chat_type == ChatType.PRIVATE:
        # Private chat: 4 buttons
        keyboard = [
            [InlineKeyboardButton("💬 Общаться напрямую", callback_data=sign_callback_data("direct_chat"))],
            [InlineKeyboardButton("📊 Саммари групп", callback_data=sign_callback_data("dm_summary"))],
            [InlineKeyboardButton("👥 Добавить в групповой чат", url=f"https://t.me/{config.BOT_USERNAME}?startgroup=true")],
            [InlineKeyboardButton("🎭 Настроить личность", callback_data=sign_callback_data("setup_personality"))]
        ]
    else:
        # Group chat: 4 buttons
        keyboard = [
            [InlineKeyboardButton("📝 Сделать саммари", callback_data=sign_callback_data("group_summary"))],
            [InlineKeyboardButton("💬 Общаться напрямую", callback_data=sign_callback_data("direct_chat"))],
            [InlineKeyboardButton("⚖️ Рассудить", callback_data=sign_callback_data("group_judge"))],
            [InlineKeyboardButton("🎭 Настроить личность", callback_data=sign_callback_data("setup_personality"))]
        ]

    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(welcome_text, reply_markup=reply_markup)


async def show_main_menu(update: Update, context: ContextTypes.DEFAULT_TYPE, edit_message: bool = False) -> None:
    """
    Show main menu (reusable function for /start and back navigation)

    Args:
        update: Telegram update object
        context: Bot context
        edit_message: If True, edit existing message; if False, send new message
    """
    user = update.effective_user
    chat_type = update.effective_chat.type

    # Unified welcome message for all chat types
    welcome_text = f"""👋 Привет, {user.first_name}!

Я бот с разными личностями.

Могу стать быдлом и пояснить за базар, могу превратиться в олигарха и обкашлять вопросик, могу стать философом и покопаться в смыслах, а могу зумером - лениться и стонать.

Короче, что хочешь - то и будет! 🎭

Что мне сделать?"""

    # Different buttons for private vs group chats
    if chat_type == ChatType.PRIVATE:
        # Private chat: 4 buttons
        keyboard = [
            [InlineKeyboardButton("💬 Общаться напрямую", callback_data=sign_callback_data("direct_chat"))],
            [InlineKeyboardButton("📊 Саммари групп", callback_data=sign_callback_data("dm_summary"))],
            [InlineKeyboardButton("👥 Добавить в групповой чат", url=f"https://t.me/{config.BOT_USERNAME}?startgroup=true")],
            [InlineKeyboardButton("🎭 Настроить личность", callback_data=sign_callback_data("setup_personality"))]
        ]
    else:
        # Group chat: 4 buttons
        keyboard = [
            [InlineKeyboardButton("📝 Сделать саммари", callback_data=sign_callback_data("group_summary"))],
            [InlineKeyboardButton("💬 Общаться напрямую", callback_data=sign_callback_data("direct_chat"))],
            [InlineKeyboardButton("⚖️ Рассудить", callback_data=sign_callback_data("group_judge"))],
            [InlineKeyboardButton("🎭 Настроить личность", callback_data=sign_callback_data("setup_personality"))]
        ]

    reply_markup = InlineKeyboardMarkup(keyboard)

    if edit_message and update.callback_query:
        await update.callback_query.edit_message_text(welcome_text, reply_markup=reply_markup)
    else:
        await update.effective_message.reply_text(welcome_text, reply_markup=reply_markup)


async def handle_start_menu_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Handle callbacks from /start menu buttons

    Callbacks:
    - direct_chat: Show personality selection
    - dm_summary: Show chat selection for summary in DM
    - setup_personality: Redirect to /lichnost
    - group_summary: Start summary in group
    - group_judge: Start judge in group
    - back_to_main: Return to main menu

    Note: 'add_to_group' is now a URL button (deep-link) and doesn't trigger callback
    """
    from utils.security import verify_callback_data
    from modules import direct_chat

    query = update.callback_query
    await query.answer()

    try:
        # Verify HMAC signature
        if not verify_callback_data(query.data):
            await query.edit_message_text("❌ Неверная подпись данных. Попробуй /start")
            return

        # Extract action (remove HMAC part)
        action = query.data.split(":")[0]

        if action == "back_to_main":
            # Return to main menu
            await show_main_menu(update, context, edit_message=True)

        elif action == "direct_chat":
            # Show personality selection menu
            await direct_chat.show_personality_selection(update, context, edit_message=True, show_back_button=True)

        elif action == "setup_personality":
            # Redirect to personality selection (same as direct_chat for now)
            await direct_chat.show_personality_selection(update, context, edit_message=True, show_back_button=True)

        elif action == "dm_summary":
            # Show chat selection for summary in DM
            from modules import summaries
            from services import DBService

            user = query.from_user
            await query.edit_message_text("⏳ Загружаю список чатов...")

            # Get all chats where bot is present
            db = DBService()
            all_chats = db.get_all_chats()

            if not all_chats:
                # No chats yet - show button to add bot to a group
                keyboard = [
                    [InlineKeyboardButton("👥 Добавить в групповой чат", url=f"https://t.me/{config.BOT_USERNAME}?startgroup=true")],
                    [InlineKeyboardButton("◀️ Назад", callback_data=sign_callback_data("back_to_main"))]
                ]
                reply_markup = InlineKeyboardMarkup(keyboard)
                await query.edit_message_text(
                    "📭 Бот пока не добавлен ни в один чат.\n\n"
                    "Добавь меня в групповой чат, чтобы я мог делать саммари!",
                    reply_markup=reply_markup
                )
                return

            # Filter chats where user is a member
            from utils import validate_chat_access, create_signature
            user_chats = []
            for chat in all_chats:
                ok, _ = await validate_chat_access(context.bot, chat.chat_id, user.id)
                if ok:
                    user_chats.append(chat)

            if not user_chats:
                # Bot is in some chats, but user is not a member of any
                keyboard = [
                    [InlineKeyboardButton("👥 Добавить в свой чат", url=f"https://t.me/{config.BOT_USERNAME}?startgroup=true")],
                    [InlineKeyboardButton("◀️ Назад", callback_data=sign_callback_data("back_to_main"))]
                ]
                reply_markup = InlineKeyboardMarkup(keyboard)
                await query.edit_message_text(
                    "📭 У нас нет общих чатов.\n\n"
                    "Добавь меня в чат, где ты состоишь, чтобы я мог делать саммари!",
                    reply_markup=reply_markup
                )
                return

            # Create inline buttons for each chat
            keyboard = []
            for chat in user_chats:
                signature = create_signature(chat.chat_id, user.id)
                callback_data = f"summary:{chat.chat_id}:{signature}"
                button_text = f"{chat.emoji} {chat.chat_title or 'Чат'}"
                keyboard.append([InlineKeyboardButton(button_text, callback_data=callback_data)])

            # Add back button
            keyboard.append([InlineKeyboardButton("◀️ Назад", callback_data=sign_callback_data("back_to_main"))])

            reply_markup = InlineKeyboardMarkup(keyboard)
            await query.edit_message_text(
                "📋 Выбери чат для саммари:",
                reply_markup=reply_markup
            )

        elif action == "group_summary":
            # Show personality selection menu directly (no instructions)
            from services import DBService
            from utils import build_personality_menu

            db = DBService()
            chat_id = update.effective_chat.id

            # Get current personality for ✓ indicator
            current_personality = db.get_user_personality(user.id)

            # Build personality menu using universal builder
            keyboard = build_personality_menu(
                user_id=user.id,
                callback_prefix="summary_personality",
                context="select",
                current_personality=current_personality,
                extra_callback_data={"chat_id": chat_id, "limit": "none"},
                show_create_button=False,  # Don't show create button in summary context
                show_back_button=True  # Show back button to return to main menu
            )

            await query.edit_message_text(
                "🎭 Выбери личность для саммари:",
                reply_markup=keyboard
            )

        elif action == "group_judge":
            # Show concise instructions for /rassudi command with "Got it" button
            text = f"""⚖️ Рассудить спор

Используй:
/{config.COMMAND_JUDGE} @user1 @user2 описание

Пример:
/{config.COMMAND_JUDGE} @ivan @petya Кто прав?"""

            keyboard = [[InlineKeyboardButton("Понятно! ✓", callback_data=sign_callback_data("back_to_main"))]]
            reply_markup = InlineKeyboardMarkup(keyboard)
            await query.edit_message_text(text, reply_markup=reply_markup)

        else:
            await query.edit_message_text("❌ Неизвестное действие. Попробуй /start")

    except Exception as e:
        logger.error(f"Error handling start menu callback: {e}")
        await query.edit_message_text("❌ Ошибка. Попробуй /start")


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Handle /help command
    Show comprehensive help message with all commands
    """
    help_text = f"""📚 Справка по командам

🎭 **Личность AI:**
/{config.COMMAND_PERSONALITY} — выбрать или создать личность

💬 **Общение:**
• В ЛС: просто пиши мне после выбора личности
• В группе: /{config.COMMAND_CHAT} — начать сессию общения (в разработке)

📝 **Саммаризация:**
/{config.COMMAND_SUMMARY} — создать саммари обсуждения
• В группе: саммари текущего чата
• В ЛС: выбери чат для саммари

⚖️ **Судейство:**
/{config.COMMAND_JUDGE} — рассудить спор

📊 **Статистика:**
/stats — твоя статистика использования

❓ Остались вопросы? Напиши /{config.COMMAND_START}"""

    await update.message.reply_text(help_text)


async def stats_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Handle /stats command
    Show user statistics
    """
    from services import DBService

    user = update.effective_user
    db = DBService()
    stats = db.get_user_stats(user.id)

    if not stats:
        await update.message.reply_text(
            "📊 Статистика пока пуста.\n\n"
            f"Используй команды /{config.COMMAND_SUMMARY} и /{config.COMMAND_JUDGE} "
            f"чтобы накопить статистику!"
        )
        return

    # Format statistics
    summary_count = stats.get('summary', 0) + stats.get('summary_dm', 0)
    judge_count = stats.get('judge', 0)

    stats_text = f"""📊 Твоя статистика

🔍 Саммари создано: {summary_count}
⚖️ Споров рассужено: {judge_count}

Продолжай пользоваться ботом! 🚀"""

    await update.message.reply_text(stats_text)
