"""
Basic bot commands
/start and /help
"""

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
import config
from config import logger
from utils.security import sign_callback_data


async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Handle /start command
    Show welcome message with inline menu for action selection
    """
    user = update.effective_user

    # Unified welcome message for all chat types
    welcome_text = f"""👋 Привет, {user.first_name}!

Я бот с множественными личностями.

Я могу:
• Общаться с тобой в разных стилях
• Саммаризировать групповые чаты
• Рассуживать споры

Что будем делать?"""

    # Build inline keyboard
    keyboard = [
        [InlineKeyboardButton("💬 Общаться напрямую", callback_data=sign_callback_data("direct_chat"))],
        [InlineKeyboardButton("👥 Добавить в групповой чат", callback_data=sign_callback_data("add_to_group"))],
        [InlineKeyboardButton("🎭 Настроить личность", callback_data=sign_callback_data("setup_personality"))]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await update.message.reply_text(welcome_text, reply_markup=reply_markup)


async def handle_start_menu_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Handle callbacks from /start menu buttons

    Callbacks:
    - direct_chat: Show personality selection
    - add_to_group: Show instructions for adding bot to group
    - setup_personality: Redirect to /lichnost
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

        if action == "direct_chat":
            # Show personality selection menu
            await direct_chat.show_personality_selection(update, context, edit_message=True)

        elif action == "add_to_group":
            # Show group addition instructions (will be implemented in Phase 3 - onboarding module)
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

            await query.edit_message_text(text)

        elif action == "setup_personality":
            # Redirect to personality selection (same as direct_chat for now)
            await direct_chat.show_personality_selection(update, context, edit_message=True)

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
