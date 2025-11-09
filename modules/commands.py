"""
Basic bot commands
/start and /help
"""

from telegram import Update
from telegram.ext import ContextTypes
import config
from config import logger


async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Handle /start command
    Show welcome message and basic instructions
    """
    user = update.effective_user
    logger.info(f"User {user.id} ({user.username}) started the bot")

    welcome_text = f"""👋 Привет, {user.first_name}!

Я — бот для саммаризации чатов с AI.

🎯 Что умею:
• /{config.COMMAND_SUMMARY} — саммари чата (дефолт: 24 часа)
• /{config.COMMAND_SUMMARY} 6ч — саммари за 6 часов
• /{config.COMMAND_SUMMARY} 30м — саммари за 30 минут
• /{config.COMMAND_SUMMARY} сегодня — с начала дня
• /{config.COMMAND_JUDGE} <текст> — рассудить спор
• /{config.COMMAND_PERSONALITY} — выбрать стиль AI

💡 Как использовать:
1. Добавь меня в группу
2. Напиши /{config.COMMAND_SUMMARY} в группе
3. Или напиши мне в ЛС и выбери чат

По умолчанию: нейтральный стиль 🎓

/{config.COMMAND_HELP} — полная справка"""

    await update.message.reply_text(welcome_text)


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
