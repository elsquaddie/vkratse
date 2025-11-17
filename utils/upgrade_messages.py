"""
Upgrade Messages Utility
Helper functions for showing upgrade prompts to users
"""

from typing import Optional
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from config import logger
from utils.security import sign_callback_data


async def show_upgrade_message(
    update: Update,
    reason: str,
    tier: str = 'free',
    limit_type: Optional[str] = None,
    current: Optional[int] = None,
    limit: Optional[int] = None
) -> None:
    """
    Show upgrade message to encourage user to upgrade to Pro

    Args:
        update: Telegram update object
        reason: Reason for showing upgrade message (e.g., "Лимит сообщений исчерпан")
        tier: User's current tier ('free' or 'pro')
        limit_type: Type of limit exceeded ('messages', 'summaries', 'personality')
        current: Current usage count
        limit: Limit value
    """
    try:
        # Build personalized message based on limit type
        if current is not None and limit is not None:
            limit_msg = f"⚠️ {reason} ({current}/{limit})\n\n"
        else:
            limit_msg = f"⚠️ {reason}\n\n"

        # Main upgrade pitch
        message = limit_msg
        message += "💎 Обновись до Pro и получи:\n\n"

        # Customize benefits based on what limit was hit
        if limit_type == 'messages':
            message += "✨ До 500 сообщений в день (вместо 30)\n"
            message += "✨ Безлимитное использование всех личностей\n"
            message += "✨ До 3 кастомных личностей\n"
            message += "✨ Расширенный контекст (50 сообщений)\n"
            message += "✨ Приоритетная обработка\n"
        elif limit_type == 'summaries':
            message += "✨ До 10 саммари в ЛС/день (вместо 3)\n"
            message += "✨ До 20 саммари в группах/день (вместо 3)\n"
            message += "✨ Безлимитное использование всех личностей\n"
            message += "✨ Сниженный кулдаун (30 сек вместо 60)\n"
        elif limit_type == 'personality':
            message += "✨ Безлимитное использование ВСЕХ личностей\n"
            message += "✨ До 3 кастомных личностей (4 с группой)\n"
            message += "✨ 500 сообщений в день\n"
            message += "✨ Расширенный контекст диалога\n"
        elif limit_type == 'judge':
            message += "✨ До 20 судейств/день (вместо 2)\n"
            message += "✨ Безлимитное использование всех личностей\n"
            message += "✨ Приоритетная обработка\n"
        else:
            # Generic benefits
            message += "✨ Безлимитные личности ♾️\n"
            message += "✨ До 500 сообщений/день\n"
            message += "✨ До 3 кастомных личностей\n"
            message += "✨ Приоритетная обработка\n"

        message += "\n💰 Всего $2.99/месяц"
        message += "\n\n👉 Узнать больше: /premium"

        # Create inline keyboard with premium button
        keyboard = [
            [InlineKeyboardButton(
                "💎 Узнать о Pro",
                callback_data=sign_callback_data("show_premium")
            )]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)

        # Send message
        if update.callback_query:
            # If called from callback, edit message
            await update.callback_query.message.reply_text(
                message,
                reply_markup=reply_markup
            )
        else:
            # If called from command, reply to message
            await update.message.reply_text(
                message,
                reply_markup=reply_markup
            )

    except Exception as e:
        logger.error(f"Error showing upgrade message: {e}")
        # Fallback to simple message without buttons
        try:
            simple_msg = f"{reason}\n\n💎 Обновись до Pro: /premium"
            if update.callback_query:
                await update.callback_query.message.reply_text(simple_msg)
            else:
                await update.message.reply_text(simple_msg)
        except Exception as fallback_error:
            logger.error(f"Error showing fallback upgrade message: {fallback_error}")


async def show_group_bonus_message(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    group_link: Optional[str] = None
) -> None:
    """
    Show message encouraging user to join project group for bonus features

    Args:
        update: Telegram update object
        context: Bot context
        group_link: Link to project group (optional)
    """
    try:
        message = "🎁 Вступи в группу проекта и получи БОНУС:\n\n"
        message += "✨ +1 кастомная личность (для Free пользователей)\n"
        message += "✨ +1 слот для Pro пользователей (всего 4)\n"
        message += "✨ Доступ к эксклюзивным обновлениям\n"
        message += "✨ Прямая связь с разработчиками\n\n"

        if group_link:
            message += f"👉 Присоединяйся: {group_link}"

            keyboard = [[InlineKeyboardButton(
                "👥 Вступить в группу",
                url=group_link
            )]]
            reply_markup = InlineKeyboardMarkup(keyboard)

            await update.message.reply_text(message, reply_markup=reply_markup)
        else:
            message += "👉 Спроси у администратора ссылку на группу"
            await update.message.reply_text(message)

    except Exception as e:
        logger.error(f"Error showing group bonus message: {e}")
