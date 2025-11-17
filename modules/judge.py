"""
Judge command (/рассуди)
AI judges disputes in chat
"""

from telegram import Update
from telegram.ext import ContextTypes, ConversationHandler
import config
from config import logger
from services import DBService, AIService, SubscriptionService
from utils import (
    check_cooldown, set_cooldown,
    check_rate_limit,
    extract_mentions,
    verify_signature, create_signature
)
from utils.upgrade_messages import show_upgrade_message

# ConversationHandler states
AWAITING_DISPUTE_DESCRIPTION = 1


async def start_judge_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """
    Handle 'start_judge' callback - entry point via button instead of command
    Same logic as judge_command but triggered by inline button
    """
    from utils.security import verify_callback_data

    query = update.callback_query
    await query.answer()

    # Verify HMAC signature
    if not verify_callback_data(query.data):
        await query.edit_message_text("❌ Неверная подпись данных.")
        return ConversationHandler.END

    user = query.from_user
    chat = update.effective_chat
    db = DBService()
    subscription = SubscriptionService(db)

    # ================================================
    # MONETIZATION: Check usage limit for judge
    # ================================================
    limit_check = await subscription.check_usage_limit(user.id, 'judge')

    if not limit_check['can_proceed']:
        # User has exceeded their daily judge limit
        await show_upgrade_message(
            update=update,
            reason="Лимит судейства исчерпан",
            tier=limit_check['tier'],
            limit_type='judge',
            current=limit_check['current'],
            limit=limit_check['limit']
        )
        return ConversationHandler.END

    # Rate limit check
    ok, remaining = check_rate_limit(user.id)
    if not ok:
        await query.edit_message_text(
            f"⏰ Слишком много запросов. Подожди {remaining} секунд."
        )
        return ConversationHandler.END

    # Cooldown check
    ok, remaining = check_cooldown(chat.id, 'judge')
    if not ok:
        await query.edit_message_text(
            f"⏰ Чат на кулдауне. Подожди {remaining} секунд."
        )
        return ConversationHandler.END

    # Save chat_id and user_id in bot_data for persistence
    judge_key = f"judge_{chat.id}_{user.id}"
    context.bot_data[judge_key] = {
        'chat_id': chat.id,
        'user_id': user.id
    }

    # Ask user to describe the dispute
    await query.edit_message_text(
        "⚖️ Опиши спор в следующем сообщении!\n\n"
        "Например:\n"
        "• Дамирка и Настька поспорили о плоской земле. Кто прав?\n"
        "• Ребята поругались насчёт Python vs JavaScript\n\n"
        "Я проанализирую контекст беседы и рассужу спор в выбранном стиле!\n\n"
        "Чтобы отменить, напиши /cancel"
    )

    return AWAITING_DISPUTE_DESCRIPTION


async def judge_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """
    Handle /рассуди command - entry point for conversation

    NEW LOGIC: Simply asks user to describe the dispute in next message
    No more need to type everything in one command!
    """
    user = update.effective_user
    chat = update.effective_chat
    db = DBService()
    subscription = SubscriptionService(db)

    # ================================================
    # MONETIZATION: Check usage limit for judge
    # ================================================
    limit_check = await subscription.check_usage_limit(user.id, 'judge')

    if not limit_check['can_proceed']:
        # User has exceeded their daily judge limit
        await show_upgrade_message(
            update=update,
            reason="Лимит судейства исчерпан",
            tier=limit_check['tier'],
            limit_type='judge',
            current=limit_check['current'],
            limit=limit_check['limit']
        )
        return ConversationHandler.END

    # Rate limit check
    ok, remaining = check_rate_limit(user.id)
    if not ok:
        await update.message.reply_text(
            f"⏰ Слишком много запросов. Подожди {remaining} секунд."
        )
        return ConversationHandler.END

    # Cooldown check
    ok, remaining = check_cooldown(chat.id, 'judge')
    if not ok:
        await update.message.reply_text(
            f"⏰ Чат на кулдауне. Подожди {remaining} секунд."
        )
        return ConversationHandler.END

    # Save chat_id and user_id in bot_data for persistence
    # Using bot_data instead of user_data for better serverless persistence
    judge_key = f"judge_{chat.id}_{user.id}"
    context.bot_data[judge_key] = {
        'chat_id': chat.id,
        'user_id': user.id
    }

    # Ask user to describe the dispute
    await update.message.reply_text(
        "⚖️ Опиши спор в следующем сообщении!\n\n"
        "Например:\n"
        "• Дамирка и Настька поспорили о плоской земле. Кто прав?\n"
        "• Ребята поругались насчёт Python vs JavaScript\n\n"
        "Я проанализирую контекст беседы и рассужу спор в выбранном стиле!\n\n"
        "Чтобы отменить, напиши /cancel"
    )

    return AWAITING_DISPUTE_DESCRIPTION


async def receive_dispute_description(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """
    Receive dispute description from user and show personality selection menu
    """
    user = update.effective_user
    chat = update.effective_chat
    dispute_text = update.message.text.strip()

    # Get chat_id from bot_data
    judge_key = f"judge_{chat.id}_{user.id}"
    judge_data = context.bot_data.get(judge_key)

    if not judge_data:
        await update.message.reply_text(
            "❌ Сессия судейства потеряна. Попробуй снова:\n"
            f"/{config.COMMAND_JUDGE}"
        )
        return ConversationHandler.END

    chat_id = judge_data['chat_id']

    # Validate description length
    if len(dispute_text) < 10:
        await update.message.reply_text(
            "⚠️ Опиши спор подробнее (минимум 10 символов).\n\n"
            "Попробуй ещё раз или /cancel для отмены."
        )
        return AWAITING_DISPUTE_DESCRIPTION

    if len(dispute_text) > config.MAX_PERSONALITY_DESCRIPTION_LENGTH:
        await update.message.reply_text(
            f"⚠️ Описание слишком длинное (максимум {config.MAX_PERSONALITY_DESCRIPTION_LENGTH} символов).\n\n"
            "Сократи описание или /cancel для отмены."
        )
        return AWAITING_DISPUTE_DESCRIPTION

    # Save dispute description to bot_data for persistence
    context.bot_data[judge_key]['dispute_text'] = dispute_text

    # Show personality selection menu
    from utils import build_personality_menu

    keyboard = build_personality_menu(
        user_id=user.id,
        callback_prefix="judge_personality",
        context="select",
        current_personality=None,  # No default selection - user must choose
        extra_callback_data={"chat_id": chat_id},
        show_create_button=False,  # Don't show create button in judge context
        show_back_button=True,  # Show back button to cancel judge
        back_callback="judge_cancel"
    )

    await update.message.reply_text(
        "⚖️ Выбери стиль судейства:",
        reply_markup=keyboard
    )

    # End conversation - callback handler will take over
    return ConversationHandler.END


async def cancel_judge(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Cancel judge conversation"""
    user = update.effective_user
    chat = update.effective_chat

    # Clear bot_data
    judge_key = f"judge_{chat.id}_{user.id}"
    context.bot_data.pop(judge_key, None)

    await update.message.reply_text(
        "❌ Судейство отменено.\n\n"
        "Чтобы начать заново, используй /rassudi"
    )

    return ConversationHandler.END


async def handle_judge_cancel_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle 'Back' button click during judge personality selection"""
    from utils.security import verify_callback_data

    query = update.callback_query
    await query.answer()

    # Verify HMAC signature
    if not verify_callback_data(query.data):
        await query.edit_message_text("❌ Неверная подпись данных.")
        return

    user = query.from_user
    chat = update.effective_chat

    # Clear bot_data
    judge_key = f"judge_{chat.id}_{user.id}"
    context.bot_data.pop(judge_key, None)

    await query.edit_message_text(
        "❌ Судейство отменено.\n\n"
        "Чтобы начать заново, используй /rassudi"
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

        # Get dispute description from bot_data
        judge_key = f"judge_{chat_id}_{user.id}"
        judge_data = context.bot_data.get(judge_key)

        if not judge_data or 'dispute_text' not in judge_data:
            await query.edit_message_text(
                "❌ Контекст спора потерян. Попробуй снова:\n"
                f"/{config.COMMAND_JUDGE}"
            )
            return

        dispute_text = judge_data['dispute_text']

        # Get personality
        personality = db.get_personality_by_id(personality_id)
        if not personality:
            logger.error(f"Personality {personality_id} not found")
            await query.edit_message_text("❌ Личность не найдена")
            return

        # Check if personality is blocked
        if personality.is_blocked:
            await query.answer(
                "⚠️ Эта личность заблокирована.\n\n"
                "Причина: ты вышел из группы проекта.\n"
                "Вернись в группу, чтобы разблокировать её!",
                show_alert=True
            )
            return

        # ================================================
        # MONETIZATION: Check personality usage limit for judge
        # ================================================
        subscription = SubscriptionService(db)
        personality_check = await subscription.check_personality_limit(
            user_id=user.id,
            personality=personality.name,
            action='judge'
        )

        if not personality_check['can_proceed']:
            # User has exceeded personality usage limit
            await query.edit_message_text(
                f"⚠️ Лимит использования личности '{personality.display_name}' исчерпан "
                f"({personality_check['current']}/{personality_check['limit']}).\n\n"
                f"💎 Pro-подписка дает безлимитное использование всех личностей!\n"
                f"Узнать больше: /premium"
            )
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

        # ================================================
        # MONETIZATION: Increment usage counter after successful verdict
        # ================================================
        # subscription already initialized above
        await subscription.increment_usage(user.id, 'judge')

        # Increment personality usage counter
        await subscription.increment_personality_usage(
            user_id=user.id,
            personality=personality.name,
            action='judge'
        )

        # Set cooldown
        set_cooldown(chat_id, 'judge')

        # Log event
        db.log_event(user.id, chat_id, 'judge', {
            'dispute': dispute_text[:200],
            'personality': personality.name
        })

        # Clear bot_data
        judge_key = f"judge_{chat_id}_{user.id}"
        context.bot_data.pop(judge_key, None)

    except Exception as e:
        logger.error(f"Error in judge personality callback: {e}")
        await query.edit_message_text(
            "❌ Ошибка при генерации вердикта. Попробуй позже."
        )
