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

Я бот с множественными личностями.

Я могу:
• Общаться с тобой в разных стилях
• Саммаризировать групповые чаты
• Рассуживать споры

Что будем делать?"""

    # Different buttons for private vs group chats
    if chat_type == ChatType.PRIVATE:
        # Private chat: 3 buttons
        keyboard = [
            [InlineKeyboardButton("💬 Общаться напрямую", callback_data=sign_callback_data("direct_chat"))],
            [InlineKeyboardButton("👥 Добавить в групповой чат", callback_data=sign_callback_data("add_to_group"))],
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

Я бот с множественными личностями.

Я могу:
• Общаться с тобой в разных стилях
• Саммаризировать групповые чаты
• Рассуживать споры

Что будем делать?"""

    # Different buttons for private vs group chats
    if chat_type == ChatType.PRIVATE:
        # Private chat: 3 buttons
        keyboard = [
            [InlineKeyboardButton("💬 Общаться напрямую", callback_data=sign_callback_data("direct_chat"))],
            [InlineKeyboardButton("👥 Добавить в групповой чат", callback_data=sign_callback_data("add_to_group"))],
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
    - add_to_group: Show instructions for adding bot to group
    - setup_personality: Redirect to /lichnost
    - group_summary: Start summary in group
    - group_judge: Start judge in group
    - back_to_main: Return to main menu
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

        elif action == "add_to_group":
            # Show group addition instructions with back button
            text = f"""🎉 Добавь меня в свою группу!

Я смогу:
✅ Саммаризировать обсуждения
✅ Рассуживать споры
✅ Общаться в разных стилях

💡 Чтобы добавить:
1. Нажми на моё имя вверху
2. Выбери "Add to Group"
3. Выбери нужную группу

После добавления используй команды:
• /{config.COMMAND_SUMMARY} — саммаризировать чат
• /{config.COMMAND_CHAT} — начать общение
• /{config.COMMAND_JUDGE} — рассудить спор"""

            keyboard = [[InlineKeyboardButton("◀️ Назад", callback_data=sign_callback_data("back_to_main"))]]
            reply_markup = InlineKeyboardMarkup(keyboard)
            await query.edit_message_text(text, reply_markup=reply_markup)

        elif action == "setup_personality":
            # Redirect to personality selection (same as direct_chat for now)
            await direct_chat.show_personality_selection(update, context, edit_message=True, show_back_button=True)

        elif action == "group_summary":
            # Show instructions for /summary command with back button
            text = f"""📝 Сделать саммари

Чтобы я создал саммари обсуждения, используй команду:

/{config.COMMAND_SUMMARY}

Опционально можно указать количество сообщений:
/{config.COMMAND_SUMMARY} 100 — последние 100 сообщений
/{config.COMMAND_SUMMARY} 200 — последние 200 сообщений

Я предложу выбрать личность для саммари и подведу итоги обсуждения! 🎭"""

            keyboard = [[InlineKeyboardButton("◀️ Назад", callback_data=sign_callback_data("back_to_main"))]]
            reply_markup = InlineKeyboardMarkup(keyboard)
            await query.edit_message_text(text, reply_markup=reply_markup)

        elif action == "group_judge":
            # Show instructions for /rassudi command with back button
            text = f"""⚖️ Рассудить спор

Чтобы я рассудил спор, используй команду:

/{config.COMMAND_JUDGE} @user1 @user2 описание спора

Пример:
/{config.COMMAND_JUDGE} @ivan @petya Кто прав насчет выбора фреймворка?

Я проанализирую последние сообщения участников и вынесу вердикт в выбранном стиле личности! 🎭"""

            keyboard = [[InlineKeyboardButton("◀️ Назад", callback_data=sign_callback_data("back_to_main"))]]
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
