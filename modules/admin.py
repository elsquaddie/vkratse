"""
Admin Commands Module
Commands for manual subscription management (testing and support)
"""

from datetime import datetime, date, timezone
from telegram import Update
from telegram.ext import ContextTypes

import config
from config import logger
from services.db_service import DBService
from services.subscription import get_subscription_service


# ================================================
# ADMIN COMMANDS
# ================================================

async def setplan_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Admin command to manually set user subscription plan

    Usage:
        /setplan <user_id> <tier> [days]
        /setplan 123456789 pro 30
        /setplan 987654321 free 0

    Args:
        user_id: Target user's Telegram ID
        tier: 'free' or 'pro'
        days: Duration in days (default: 30 for pro, 0 for free)
    """
    admin_id = update.effective_user.id

    # Check admin rights
    if admin_id != config.ADMIN_USER_ID:
        await update.message.reply_text("⛔ Доступ запрещен")
        return

    # Parse arguments
    try:
        args = context.args
        if len(args) < 2:
            await update.message.reply_text(
                "❌ Неверный формат команды\n\n"
                "Использование:\n"
                "/setplan <user_id> <tier> [days]\n\n"
                "Примеры:\n"
                "/setplan 123456789 pro 30\n"
                "/setplan 987654321 free 0"
            )
            return

        target_user_id = int(args[0])
        tier = args[1].lower()
        duration_days = int(args[2]) if len(args) > 2 else (30 if tier == 'pro' else 0)

        # Validate tier
        if tier not in ['free', 'pro']:
            await update.message.reply_text("❌ Тариф должен быть 'free' или 'pro'")
            return

    except (ValueError, IndexError) as e:
        await update.message.reply_text(
            f"❌ Ошибка парсинга аргументов: {e}\n\n"
            "Использование: /setplan <user_id> <tier> [days]"
        )
        return

    # Get subscription service
    try:
        sub_service = get_subscription_service()
    except RuntimeError:
        await update.message.reply_text(
            "❌ Subscription service не инициализирован"
        )
        return

    # Create/update subscription
    success = await sub_service.create_or_update_subscription(
        user_id=target_user_id,
        tier=tier,
        duration_days=duration_days,
        payment_method='manual',
        transaction_id=f'admin_{admin_id}_{int(datetime.now(timezone.utc).timestamp())}'
    )

    if success:
        # Format response
        tier_emoji = "💎" if tier == 'pro' else "🆓"
        tier_name = "Pro" if tier == 'pro' else "Free"

        message = f"✅ Подписка установлена!\n\n"
        message += f"User ID: {target_user_id}\n"
        message += f"Тариф: {tier_emoji} {tier_name}\n"
        message += f"Срок: {duration_days} дней\n"

        if duration_days > 0:
            expires_at = datetime.now(timezone.utc).replace(hour=23, minute=59, second=59)
            from datetime import timedelta
            expires_at += timedelta(days=duration_days)
            message += f"Истекает: {expires_at.strftime('%Y-%m-%d')}\n"

        await update.message.reply_text(message)

        # Try to notify user
        try:
            if tier == 'pro':
                user_message = (
                    f"🎉 Поздравляем!\n\n"
                    f"Вам активирована Pro-подписка на {duration_days} дней.\n"
                    f"Наслаждайтесь безлимитными возможностями!\n\n"
                    f"Проверить статус: /mystatus"
                )
            else:
                user_message = (
                    f"ℹ️ Ваш тариф изменен на Free.\n\n"
                    f"Проверить статус: /mystatus"
                )

            await context.bot.send_message(
                chat_id=target_user_id,
                text=user_message
            )

            await update.message.reply_text("✅ Пользователь уведомлен")

        except Exception as e:
            logger.warning(f"Could not notify user {target_user_id}: {e}")
            await update.message.reply_text(
                "⚠️ Не удалось уведомить пользователя (возможно, он не запускал бота)"
            )

    else:
        await update.message.reply_text("❌ Ошибка при установке подписки")


async def checkplan_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Admin command to check user's subscription plan

    Usage:
        /checkplan <user_id>
        /checkplan 123456789
    """
    admin_id = update.effective_user.id

    # Check admin rights
    if admin_id != config.ADMIN_USER_ID:
        await update.message.reply_text("⛔ Доступ запрещен")
        return

    # Parse arguments
    try:
        args = context.args
        if len(args) < 1:
            await update.message.reply_text(
                "❌ Использование: /checkplan <user_id>\n"
                "Пример: /checkplan 123456789"
            )
            return

        target_user_id = int(args[0])

    except (ValueError, IndexError) as e:
        await update.message.reply_text(f"❌ Ошибка: {e}")
        return

    # Get subscription service
    try:
        sub_service = get_subscription_service()
    except RuntimeError:
        await update.message.reply_text("❌ Subscription service не инициализирован")
        return

    # Get user's tier
    tier = await sub_service.get_user_tier(target_user_id)

    # Get subscription details
    sub_details = await sub_service.db.get_subscription(target_user_id)

    # Get usage stats
    usage = await sub_service.db.get_usage_limits(target_user_id, date.today())

    # Format response
    tier_emoji = "💎" if tier == 'pro' else "🆓"
    tier_name = "Pro" if tier == 'pro' else "Free"

    message = f"📊 Информация о пользователе {target_user_id}\n\n"
    message += f"Тариф: {tier_emoji} {tier_name}\n"

    if sub_details:
        message += f"Активна: {'✅ Да' if sub_details.get('is_active') else '❌ Нет'}\n"

        if sub_details.get('expires_at'):
            expires_at = sub_details['expires_at']
            if isinstance(expires_at, str):
                expires_at = datetime.fromisoformat(expires_at.replace('Z', '+00:00'))
            message += f"Истекает: {expires_at.strftime('%Y-%m-%d %H:%M:%S UTC')}\n"

            days_left = (expires_at - datetime.now(timezone.utc)).days
            message += f"Осталось: {days_left} дней\n"

        if sub_details.get('payment_method'):
            message += f"Способ оплаты: {sub_details['payment_method']}\n"
    else:
        message += "Подписка: Не найдена (Free по умолчанию)\n"

    # Usage stats
    if usage:
        limits = config.TIER_LIMITS[tier]
        message += f"\n📈 Использование сегодня:\n"
        message += f"💬 Сообщения: {usage.get('messages_count', 0)}/{limits.get('messages_dm', '∞')}\n"
        message += f"📝 Саммари (ЛС): {usage.get('summaries_dm_count', 0)}/{limits.get('summaries_dm', '∞')}\n"
        message += f"📝 Саммари (группы): {usage.get('summaries_count', 0)}/{limits.get('summaries_group', '∞')}\n"
        message += f"⚖️ Судейство: {usage.get('judge_count', 0)}/{limits.get('judge', '∞')}\n"
    else:
        message += f"\n📈 Использование сегодня: 0 (нет активности)\n"

    await update.message.reply_text(message)


async def resetusage_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Admin command to reset user's usage limits for today

    Usage:
        /resetusage <user_id>
        /resetusage 123456789
    """
    admin_id = update.effective_user.id

    # Check admin rights
    if admin_id != config.ADMIN_USER_ID:
        await update.message.reply_text("⛔ Доступ запрещен")
        return

    # Parse arguments
    try:
        args = context.args
        if len(args) < 1:
            await update.message.reply_text(
                "❌ Использование: /resetusage <user_id>\n"
                "Пример: /resetusage 123456789"
            )
            return

        target_user_id = int(args[0])

    except (ValueError, IndexError) as e:
        await update.message.reply_text(f"❌ Ошибка: {e}")
        return

    # Get db_service from context
    db_service: DBService = context.bot_data.get('db_service')
    if not db_service:
        await update.message.reply_text("❌ DB service не найден")
        return

    # Delete usage record for today
    try:
        today = date.today()
        db_service.client.table('usage_limits')\
            .delete()\
            .eq('user_id', target_user_id)\
            .eq('date', today.isoformat())\
            .execute()

        # Also reset personality usage
        db_service.client.table('personality_usage')\
            .delete()\
            .eq('user_id', target_user_id)\
            .eq('date', today.isoformat())\
            .execute()

        await update.message.reply_text(
            f"✅ Лимиты сброшены для пользователя {target_user_id}\n\n"
            f"Все счетчики обнулены на {today.isoformat()}"
        )

    except Exception as e:
        logger.error(f"Error resetting usage for {target_user_id}: {e}")
        await update.message.reply_text(f"❌ Ошибка при сбросе лимитов: {e}")


async def listadmin_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Show list of available admin commands
    """
    admin_id = update.effective_user.id

    # Check admin rights
    if admin_id != config.ADMIN_USER_ID:
        await update.message.reply_text("⛔ Доступ запрещен")
        return

    message = (
        "🔧 Админские команды для управления подписками\n\n"

        "📝 Установить план:\n"
        "/setplan <user_id> <tier> [days]\n"
        "  • tier: 'free' или 'pro'\n"
        "  • days: срок в днях (default: 30)\n"
        "Пример: /setplan 123456 pro 30\n\n"

        "🔍 Проверить план:\n"
        "/checkplan <user_id>\n"
        "Пример: /checkplan 123456\n\n"

        "🔄 Сбросить лимиты:\n"
        "/resetusage <user_id>\n"
        "Пример: /resetusage 123456\n\n"

        "ℹ️ Этот список:\n"
        "/adminhelp\n\n"

        "💡 Примечания:\n"
        "• Все команды работают только для админа\n"
        "• User ID можно узнать из логов или попросив пользователя запустить /start\n"
        "• При установке плана пользователь получит уведомление\n"
    )

    await update.message.reply_text(message)


# Alias for convenience
adminhelp_command = listadmin_command
