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
    extract_mentions,
    verify_signature, create_signature
)


async def judge_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Handle /рассуди command

    Examples:
    /рассуди Дамирка и Настька поспорили о плоской земле. Кто прав?
    /рассуди Ребята поругались насчёт Python vs JavaScript
    """
    user = update.effective_user
    chat = update.effective_chat
    db = DBService()

    # 1. Validate command is not empty
    if not context.args or len(context.args) == 0:
        await update.message.reply_text(
            f"⚖️ Опиши спор!\n\n"
            f"Например:\n"
            f"/{config.COMMAND_JUDGE} Дамирка и Настька поспорили о плоской земле. Кто прав?\n\n"
            f"Я проанализирую контекст беседы и рассужу спор в выбранном стиле!"
        )
        return

    # 2. Get dispute description
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

    # 5. Save dispute description to context for callback handler
    context.user_data['judge_dispute_text'] = dispute_text
    context.user_data['judge_chat_id'] = chat.id

    # 6. Show personality selection menu
    from utils import build_personality_menu

    keyboard = build_personality_menu(
        user_id=user.id,
        callback_prefix="judge_personality",
        context="select",
        current_personality=None,  # No default selection - user must choose
        extra_callback_data={"chat_id": chat.id},
        show_create_button=False  # Don't show create button in judge context
    )

    await update.message.reply_text(
        "⚖️ Выбери стиль судейства:",
        reply_markup=keyboard
    )


async def handle_judge_personality_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Handle personality selection callback for judge command

    Callback format: judge_personality:<chat_id>:<personality_id>:<signature>
    """
    from utils.security import verify_string_signature

    query = update.callback_query
    await query.answer()

    user = query.from_user
    db = DBService()
    ai = AIService()

    try:
        # Parse callback data: judge_personality:<chat_id>:<personality_id>:<signature>
        parts = query.data.split(":")
        if len(parts) != 4:
            logger.error(f"Invalid judge callback format: expected 4 parts, got {len(parts)}")
            await query.edit_message_text("❌ Неверный формат данных")
            return

        _, chat_id_str, personality_id_str, signature = parts
        chat_id = int(chat_id_str)
        personality_id = int(personality_id_str)

        logger.info(f"[JUDGE SIGNATURE CHECK] Parsed: chat_id={chat_id}, personality_id={personality_id}, signature={signature}")

        # Verify HMAC signature (using group signature - no user_id check)
        # NOTE: We use verify_group_signature because in groups, ANY member can click the button
        from utils.security import verify_group_signature

        callback_base = f"{chat_id}:{personality_id}"
        logger.info(f"[JUDGE SIGNATURE CHECK] Verifying GROUP signature: callback_base='{callback_base}', received_signature={signature}")

        if not verify_group_signature(callback_base, signature):
            logger.error(f"[JUDGE SIGNATURE CHECK] FAILED for judge_personality: callback_base='{callback_base}', signature={signature}")
            await query.edit_message_text("❌ Неверная подпись данных. Попробуй /start")
            return

        logger.info(f"[JUDGE SIGNATURE CHECK] SUCCESS for judge_personality")

        # Get dispute description from context
        dispute_text = context.user_data.get('judge_dispute_text')
        if not dispute_text:
            await query.edit_message_text(
                "❌ Контекст спора потерян. Попробуй снова:\n"
                f"/{config.COMMAND_JUDGE} <описание спора>"
            )
            return

        # Get personality
        personality = db.get_personality_by_id(personality_id)
        if not personality:
            logger.error(f"Personality {personality_id} not found")
            await query.edit_message_text("❌ Личность не найдена")
            return

        # Get recent messages for context
        messages = db.get_messages(chat_id=chat_id, limit=50)

        # Update message to show processing
        await query.edit_message_text(
            f"⚖️ {personality.display_name} размышляет над спором...\n\n"
            f"Спор: {dispute_text[:100]}{'...' if len(dispute_text) > 100 else ''}"
        )

        # Generate verdict
        verdict = ai.generate_judge_verdict(dispute_text, messages, personality)

        # Send verdict
        verdict_message = f"⚖️ ВЕРДИКТ от {personality.emoji} {personality.display_name}:\n\n{verdict}"

        # Edit the message with verdict
        await query.edit_message_text(verdict_message)

        # Set cooldown
        set_cooldown(chat_id, 'judge')

        # Log event
        db.log_event(user.id, chat_id, 'judge', {
            'dispute': dispute_text[:200],
            'personality': personality.name
        })

        # Clear context
        context.user_data.pop('judge_dispute_text', None)
        context.user_data.pop('judge_chat_id', None)

    except Exception as e:
        logger.error(f"Error in judge personality callback: {e}")
        await query.edit_message_text(
            "❌ Ошибка при генерации вердикта. Попробуй позже."
        )
