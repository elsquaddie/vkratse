"""
Judge command (/рассуди)
AI judges disputes in chat
"""

from telegram import Update
from telegram.ext import ContextTypes
import config
from config import logger
from services import DBService, AIService
from utils import (
    check_cooldown, set_cooldown,
    check_rate_limit,
    extract_mentions
)


async def judge_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Handle /рассуди command

    Examples:
    /рассуди @вася says X, @петя says Y
    /рассуди Кто прав насчёт Python?
    """
    user = update.effective_user
    chat = update.effective_chat
    db = DBService()
    ai = AIService()

    logger.info(f"Judge command from user {user.id} in chat {chat.id}")

    # 1. Validate command is not empty
    if not context.args or len(context.args) == 0:
        await update.message.reply_text(
            f"⚖️ Укажи участников спора!\n\n"
            f"Используй:\n"
            f"/{config.COMMAND_JUDGE} @user1 @user2 описание\n\n"
            f"Пример:\n"
            f"/{config.COMMAND_JUDGE} @ivan @petya Кто прав?"
        )
        return

    # 2. Get dispute text
    dispute_text = " ".join(context.args)

    # 3. Rate limit check
    ok, remaining = check_rate_limit(user.id)
    if not ok:
        await update.message.reply_text(
            f"⏰ Слишком много запросов. Подожди {remaining} секунд."
        )
        return

    # 4. Cooldown check
    ok, remaining = check_cooldown(chat.id, 'judge')
    if not ok:
        await update.message.reply_text(
            f"⏰ Чат на кулдауне. Подожди {remaining} секунд."
        )
        return

    # 5. Extract mentioned users
    mentioned_usernames = extract_mentions(dispute_text)

    # 6. Get relevant messages
    messages = []
    if mentioned_usernames:
        # Get messages from mentioned users
        messages = db.get_messages_by_users(
            chat_id=chat.id,
            usernames=mentioned_usernames,
            limit=20
        )
        logger.debug(f"Found {len(messages)} messages from mentioned users")
    else:
        # No mentions - get more recent messages for context analysis
        messages = db.get_messages(
            chat_id=chat.id,
            limit=50  # Увеличил до 50 для лучшего контекста
        )
        logger.debug(f"Using {len(messages)} recent messages for analysis")

    # 7. Get user's personality
    personality_name = db.get_user_personality(user.id)
    personality = db.get_personality(personality_name)

    if not personality:
        logger.error(f"Personality '{personality_name}' not found, using default")
        personality = db.get_personality(config.DEFAULT_PERSONALITY)

    # 8. Generate verdict
    await update.message.reply_text("⚖️ Размышляю...")

    verdict = ai.generate_judge_verdict(dispute_text, messages, personality)

    # 9. Send verdict
    verdict_message = f"⚖️ ВЕРДИКТ:\n\n{verdict}"
    await update.message.reply_text(verdict_message)

    # 10. Set cooldown
    set_cooldown(chat.id, 'judge')

    # 11. Log event
    db.log_event(user.id, chat.id, 'judge', {
        'dispute': dispute_text[:200],  # First 200 chars
        'mentioned_users': mentioned_usernames,
        'personality': personality_name
    })

    logger.info(f"Generated verdict for chat {chat.id}")
