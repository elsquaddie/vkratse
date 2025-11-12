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
    logger.info(f"User {user.id} ({user.username}) started the bot in {chat_type}")

    # Different behavior for private vs group chats
    if chat_type == ChatType.PRIVATE:
        # Private chat: show full welcome with inline menu
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

    else:
        # Group chat: show brief help message
        group_text = f"""👋 Привет!

Я бот для саммаризации чатов и общения в разных стилях.

🎯 Основные команды:
• /{config.COMMAND_SUMMARY} — саммари чата
• /{config.COMMAND_JUDGE} — рассудить спор
• /{config.COMMAND_PERSONALITY} — выбрать личность

/{config.COMMAND_HELP} — полная справка"""

        await update.message.reply_text(group_text)


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
            text = """🎉 Добавь меня в свою группу!

Я смогу:
✅ Саммаризировать обсуждения
✅ Рассуживать споры
✅ Общаться в разных стилях

💡 Чтобы добавить:
1. Нажми на моё имя вверху
2. Выбери "Add to Group"
3. Выбери нужную группу

После добавления используй команды:
• /summary — саммари обсуждений
• /rassudi — рассудить спор
• /help — полная справка"""

            await query.edit_message_text(text)

        elif action == "setup_personality":
            # Redirect to personality selection (same as direct_chat for now)
            await direct_chat.show_personality_selection(update, context, edit_message=True)

        else:
            await query.edit_message_text("❌ Неизвестное действие. Попробуй /start")

        logger.info(f"Handled start menu callback: {action} from user {update.effective_user.id}")

    except Exception as e:
        logger.error(f"Error handling start menu callback: {e}")
        await query.edit_message_text("❌ Ошибка. Попробуй /start")


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Handle /help command
    Show detailed help information
    """
    logger.info(f"User {update.effective_user.id} requested help")

    help_text = f"""📖 Подробная справка

🔹 Команда /{config.COMMAND_SUMMARY}
Создаёт саммари чата с помощью AI.

В группе:
/{config.COMMAND_SUMMARY} — за последние 24 часа
/{config.COMMAND_SUMMARY} 6ч — за 6 часов
/{config.COMMAND_SUMMARY} 30м — за 30 минут
/{config.COMMAND_SUMMARY} 2д — за 2 дня
/{config.COMMAND_SUMMARY} сегодня — с начала дня

В личных сообщениях:
Просто напиши /{config.COMMAND_SUMMARY}, и я покажу кнопки для выбора чата.

🔹 Команда /{config.COMMAND_JUDGE}
Рассуди спор в чате.

Примеры:
/{config.COMMAND_JUDGE} @вася говорит X, @петя говорит Y
/{config.COMMAND_JUDGE} Кто прав насчёт Python vs JavaScript?

🔹 Команда /{config.COMMAND_PERSONALITY}
Выбери стиль ответов AI.

Доступные стили:
🎓 Нейтральный — профессионально и по делу
🏭 Быдлан — заводчанин с планами
🧙 Философ — мудрые размышления
👟 Гопник — пацан из 2000-х
💼 Олигарх — про яхты и миллионы
😂 Стендапер — всё в шутку
🔬 Учёный — научный подход

Также можешь создать свой стиль!

⏱️ Ограничения:
• Cooldown между саммари: {config.COOLDOWN_SECONDS}с
• Rate limit: {config.RATE_LIMIT_REQUESTS} запросов за {config.RATE_LIMIT_WINDOW}с
• Сообщения хранятся {config.MESSAGE_RETENTION_DAYS} дней

❓ Вопросы? Проблемы?
Пиши @your_support_username (если есть)"""

    await update.message.reply_text(help_text)


async def stats_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Handle /stats command
    Show user statistics
    """
    from services import DBService

    user = update.effective_user
    logger.info(f"User {user.id} requested stats")

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
