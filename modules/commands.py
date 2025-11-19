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
        # Private chat: 5 buttons (added Premium)
        keyboard = [
            [InlineKeyboardButton("💬 Общаться напрямую", callback_data=sign_callback_data("direct_chat"))],
            [InlineKeyboardButton("📊 Саммари групп", callback_data=sign_callback_data("dm_summary"))],
            [InlineKeyboardButton("💎 Premium", callback_data=sign_callback_data("show_premium"))],
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
        # Private chat: 5 buttons (added Premium)
        keyboard = [
            [InlineKeyboardButton("💬 Общаться напрямую", callback_data=sign_callback_data("direct_chat"))],
            [InlineKeyboardButton("📊 Саммари групп", callback_data=sign_callback_data("dm_summary"))],
            [InlineKeyboardButton("💎 Premium", callback_data=sign_callback_data("show_premium"))],
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
            from utils import build_personality_menu

            user = query.from_user
            chat_id = update.effective_chat.id

            # Build personality menu using universal builder
            keyboard = build_personality_menu(
                user_id=user.id,
                callback_prefix="summary_personality",
                context="select",
                current_personality=None,  # No checkmark - user must choose
                extra_callback_data={"chat_id": chat_id, "limit": "none"},
                show_create_button=True,  # Allow creating custom personality during summary
                show_back_button=True,  # Show back button to return to main menu
                back_callback="back_to_main"
            )

            await query.edit_message_text(
                "🎭 Выбери личность для саммари:",
                reply_markup=keyboard
            )

        elif action == "group_judge":
            # Show instructions for /rassudi command (no ReplyKeyboard - it doesn't disappear properly)
            text = f"""⚖️ Рассудить спор

Чтобы рассудить спор, просто введи команду:
/{config.COMMAND_JUDGE}

После этого:
1️⃣ Опиши спор в следующем сообщении
2️⃣ Выбери личность для судейства
3️⃣ Получи вердикт!

💡 Пример:
/{config.COMMAND_JUDGE}
Дамирка и Настька поспорили о плоской земле. Кто прав?"""

            # Just show instructions - no ReplyKeyboard
            await query.edit_message_text(text)

        elif action == "show_premium":
            # Show premium tiers (same logic as /premium command)
            from services import DBService, SubscriptionService

            user_id = query.from_user.id

            # Get user's current tier
            db = DBService()
            sub_service = SubscriptionService(db)
            current_tier = await sub_service.get_user_tier(user_id)

            # Build message
            message = "💎 Premium планы\n\n"

            # Free tier
            if current_tier == 'free':
                message += "🆓 FREE (текущий план)\n"
            else:
                message += "🆓 FREE\n"
            message += "• 30 сообщений/день\n"
            message += "• 3 саммари в ЛС/день\n"
            message += "• 3 саммари в группах/день\n"
            message += "• 5 использований личности/день\n"
            message += "• 0 кастомных личностей\n\n"

            # Pro tier
            if current_tier == 'pro':
                message += "⭐ PRO (текущий план)\n"
            else:
                message += "⭐ PRO - $2.99/мес\n"
            message += "• 500 сообщений/день\n"
            message += "• 10 саммари в ЛС/день\n"
            message += "• 20 саммари в группах/день\n"
            message += "• Безлимитные личности ♾️\n"
            message += "• 3 кастомные личности\n"
            message += "• Приоритетная обработка\n\n"

            # Group bonus info
            message += "🎁 Бонус за группу:\n"
            message += "Вступи в нашу группу и получи +1 кастомную личность!\n\n"

            # Buttons
            keyboard = []

            if current_tier != 'pro':
                # Show buy button only for non-Pro users
                keyboard.append([InlineKeyboardButton("💳 Купить Pro", callback_data=sign_callback_data("buy_pro"))])
            else:
                # Show cancel button only for active Pro users
                subscription = await db.get_subscription(user_id)
                if subscription and subscription.get('is_active'):
                    keyboard.append([InlineKeyboardButton("❌ Отменить подписку", callback_data=sign_callback_data("cancel_subscription"))])

            # Tribute donation link
            if config.TRIBUTE_URL and config.TRIBUTE_URL != 'https://tribute.to/your_bot_page':
                keyboard.append([InlineKeyboardButton("🎁 Поддержать (Tribute.to)", url=config.TRIBUTE_URL)])

            # Back button
            keyboard.append([InlineKeyboardButton("« Назад", callback_data=sign_callback_data("back_to_main"))])

            reply_markup = InlineKeyboardMarkup(keyboard)
            await query.edit_message_text(message, reply_markup=reply_markup)

        elif action == "buy_pro":
            # Show payment options for Pro subscription
            from services.payments import is_yookassa_configured

            message = "💳 Купить Pro подписку\n\n"
            message += "💵 Цена: $2.99/месяц (30 дней)\n\n"
            message += "Выбери способ оплаты:"

            keyboard = []

            # Telegram Stars payment (native, always available)
            keyboard.append([InlineKeyboardButton("⭐ Telegram Stars (300 ⭐)", callback_data=sign_callback_data("buy_pro_stars"))])

            # YooKassa payment (if configured OR dry run mode)
            if is_yookassa_configured() or config.PAYMENT_DRY_RUN:
                keyboard.append([InlineKeyboardButton("💳 Банковская карта", callback_data=sign_callback_data("buy_pro_card"))])

            # Tribute donation (if configured)
            if config.TRIBUTE_URL and config.TRIBUTE_URL != 'https://tribute.to/your_bot_page':
                keyboard.append([InlineKeyboardButton("🎁 Tribute.to (донат)", callback_data=sign_callback_data("buy_pro_tribute"))])

            # Back button
            keyboard.append([InlineKeyboardButton("« Назад", callback_data=sign_callback_data("show_premium"))])

            reply_markup = InlineKeyboardMarkup(keyboard)
            await query.edit_message_text(message, reply_markup=reply_markup)

        elif action == "buy_pro_card":
            # Create payment link via YooKassa
            from services.payments import create_payment_link, PaymentError, get_pricing_info
            from services.db_service import DBService
            from services.subscription import SubscriptionService
            from datetime import datetime

            user_id = query.from_user.id

            try:
                # DRY RUN MODE: Simulate successful payment
                if config.PAYMENT_DRY_RUN:
                    logger.info(f"[DRY RUN] Processing card payment for user {user_id}")

                    # Initialize services
                    db = DBService()
                    sub_service = SubscriptionService(db)

                    # Grant subscription
                    success = await sub_service.create_or_update_subscription(
                        user_id=user_id,
                        tier='pro',
                        payment_method='card_dryrun',
                        duration_days=30,
                        transaction_id=f'dryrun_card_{user_id}_{int(datetime.now().timestamp())}'
                    )

                    if not success:
                        logger.error(f"[DRY RUN] Failed to create subscription for user {user_id}")
                        await query.edit_message_text(
                            "❌ Ошибка при активации подписки (DRY RUN)\n\n"
                            "Проверь логи в Vercel.",
                            reply_markup=InlineKeyboardMarkup([[
                                InlineKeyboardButton("« Назад", callback_data=sign_callback_data("buy_pro"))
                            ]])
                        )
                        return

                    logger.info(f"[DRY RUN] Subscription created successfully for user {user_id}")

                    # Verify subscription was created
                    subscription = await db.get_subscription(user_id)
                    logger.info(f"[DRY RUN] Verification: subscription={subscription}")

                    # Show success message
                    message = "✅ Подписка активирована! (DRY RUN)\n\n"
                    message += "🎉 Теперь у тебя Pro подписка на 30 дней!\n\n"
                    message += "⚠️ Это тестовая активация.\n"
                    message += "Для реальных платежей отключи PAYMENT_DRY_RUN в настройках.\n\n"
                    message += "Проверь статус: /mystatus"

                    keyboard = [[InlineKeyboardButton("« Назад", callback_data=sign_callback_data("show_premium"))]]
                    reply_markup = InlineKeyboardMarkup(keyboard)
                    await query.edit_message_text(message, reply_markup=reply_markup)
                    return

                # Show loading message
                await query.edit_message_text("⏳ Создаю платежную ссылку...")

                # Get pricing
                pricing = get_pricing_info('pro_monthly')

                # Create payment
                payment_info = await create_payment_link(
                    user_id=user_id,
                    tier=pricing['tier'],
                    duration_days=pricing['duration_days'],
                    amount_usd=pricing['amount_usd']
                )

                # Show payment link
                message = "💳 Оплата Pro подписки\n\n"
                message += f"💵 Сумма: ${payment_info['amount']:.2f}\n"
                message += f"⏰ Срок: {pricing['duration_days']} дней\n\n"
                message += "После оплаты подписка активируется автоматически!\n\n"
                message += "⚠️ Ссылка действительна 1 час"

                keyboard = [
                    [InlineKeyboardButton("💳 Оплатить", url=payment_info['payment_url'])],
                    [InlineKeyboardButton("« Назад", callback_data=sign_callback_data("buy_pro"))]
                ]

                reply_markup = InlineKeyboardMarkup(keyboard)
                await query.edit_message_text(message, reply_markup=reply_markup)

            except PaymentError as e:
                logger.error(f"Payment error for user {user_id}: {e}")
                await query.edit_message_text(
                    f"❌ {str(e)}\n\n"
                    f"Попробуйте другой способ оплаты.",
                    reply_markup=InlineKeyboardMarkup([[
                        InlineKeyboardButton("« Назад", callback_data=sign_callback_data("buy_pro"))
                    ]])
                )
            except Exception as e:
                logger.error(f"Unexpected error creating payment: {e}", exc_info=True)
                await query.edit_message_text(
                    "❌ Произошла ошибка. Попробуйте позже или используйте другой способ оплаты.",
                    reply_markup=InlineKeyboardMarkup([[
                        InlineKeyboardButton("« Назад", callback_data=sign_callback_data("buy_pro"))
                    ]])
                )

        elif action == "buy_pro_tribute":
            # Show instructions for Tribute donation
            message = "🎁 Оплата через Tribute.to\n\n"
            message += "Для покупки Pro-подписки:\n\n"
            message += "1️⃣ Сделай донат $2.99 через Tribute.to\n"
            message += "2️⃣ Напиши админу с подтверждением оплаты\n"
            message += "3️⃣ Получи доступ к Pro функциям!\n\n"
            message += "💵 Цена: $2.99/месяц\n"
            message += "⏰ Срок: 30 дней\n\n"
            message += "После оплаты твоя подписка будет активирована вручную в течение 24 часов."

            keyboard = []
            if config.TRIBUTE_URL and config.TRIBUTE_URL != 'https://tribute.to/your_bot_page':
                keyboard.append([InlineKeyboardButton("🎁 Перейти к Tribute", url=config.TRIBUTE_URL)])
            keyboard.append([InlineKeyboardButton("« Назад", callback_data=sign_callback_data("buy_pro"))])

            reply_markup = InlineKeyboardMarkup(keyboard)
            await query.edit_message_text(message, reply_markup=reply_markup)

        elif action == "buy_pro_stars":
            # Create invoice for Telegram Stars payment
            from services.payments import create_stars_invoice, PaymentError, get_stars_pricing_info
            from services.db_service import DBService
            from services.subscription import SubscriptionService
            from datetime import datetime

            user_id = query.from_user.id

            try:
                # DRY RUN MODE: Simulate successful payment
                if config.PAYMENT_DRY_RUN:
                    logger.info(f"[DRY RUN] Processing Stars payment for user {user_id}")

                    # Initialize services
                    db = DBService()
                    sub_service = SubscriptionService(db)

                    # Grant subscription
                    success = await sub_service.create_or_update_subscription(
                        user_id=user_id,
                        tier='pro',
                        payment_method='stars_dryrun',
                        duration_days=30,
                        transaction_id=f'dryrun_stars_{user_id}_{int(datetime.now().timestamp())}'
                    )

                    if not success:
                        logger.error(f"[DRY RUN] Failed to create subscription for user {user_id}")
                        await query.edit_message_text(
                            "❌ Ошибка при активации подписки (DRY RUN)\n\n"
                            "Проверь логи в Vercel.",
                            reply_markup=InlineKeyboardMarkup([[
                                InlineKeyboardButton("« Назад", callback_data=sign_callback_data("buy_pro"))
                            ]])
                        )
                        return

                    logger.info(f"[DRY RUN] Subscription created successfully for user {user_id}")

                    # Verify subscription was created
                    subscription = await db.get_subscription(user_id)
                    logger.info(f"[DRY RUN] Verification: subscription={subscription}")

                    # Show success message
                    message = "✅ Подписка активирована! (DRY RUN)\n\n"
                    message += "🎉 Теперь у тебя Pro подписка на 30 дней!\n\n"
                    message += "⚠️ Это тестовая активация.\n"
                    message += "Для реальных платежей отключи PAYMENT_DRY_RUN в настройках.\n\n"
                    message += "Проверь статус: /mystatus"

                    keyboard = [[InlineKeyboardButton("« Назад", callback_data=sign_callback_data("show_premium"))]]
                    reply_markup = InlineKeyboardMarkup(keyboard)
                    await query.edit_message_text(message, reply_markup=reply_markup)
                    return

                # Get pricing info
                pricing = get_stars_pricing_info('pro_monthly')

                # Create Stars invoice (no loading message - happens instantly)
                result = await create_stars_invoice(
                    bot=context.bot,
                    user_id=user_id,
                    plan='pro_monthly'
                )

                # After invoice is sent, show confirmation message
                message = "⭐ Счёт для оплаты отправлен!\n\n"
                message += f"💰 Сумма: {pricing['stars_amount']} Stars (~${pricing['stars_amount']/100:.2f})\n"
                message += f"⏰ Срок: {pricing['duration_days']} дней\n\n"
                message += "После оплаты подписка активируется автоматически!\n\n"
                message += "ℹ️ Telegram Stars можно купить в приложении Telegram"

                keyboard = [
                    [InlineKeyboardButton("« Назад", callback_data=sign_callback_data("buy_pro"))]
                ]

                reply_markup = InlineKeyboardMarkup(keyboard)
                await query.edit_message_text(message, reply_markup=reply_markup)

                logger.info(f"Stars invoice created for user {user_id}")

            except PaymentError as e:
                logger.error(f"Stars payment error for user {user_id}: {e}")
                await query.edit_message_text(
                    f"❌ {str(e)}\n\n"
                    f"Попробуйте другой способ оплаты.",
                    reply_markup=InlineKeyboardMarkup([[
                        InlineKeyboardButton("« Назад", callback_data=sign_callback_data("buy_pro"))
                    ]])
                )
            except Exception as e:
                logger.error(f"Unexpected error creating Stars invoice: {e}", exc_info=True)
                await query.edit_message_text(
                    "❌ Произошла ошибка. Попробуйте позже или используйте другой способ оплаты.",
                    reply_markup=InlineKeyboardMarkup([[
                        InlineKeyboardButton("« Назад", callback_data=sign_callback_data("buy_pro"))
                    ]])
                )

        elif action == "cancel_subscription":
            # Show confirmation dialog for subscription cancellation
            from services import DBService, SubscriptionService

            user_id = query.from_user.id

            # Get subscription info
            db = DBService()
            sub_service = SubscriptionService(db)
            subscription = await db.get_subscription(user_id)

            if not subscription or not subscription.get('is_active'):
                await query.edit_message_text(
                    "❌ У тебя нет активной подписки.",
                    reply_markup=InlineKeyboardMarkup([[
                        InlineKeyboardButton("« Назад", callback_data=sign_callback_data("show_premium"))
                    ]])
                )
                return

            # Get expiry date
            expires_at_str = subscription.get('expires_at')
            if isinstance(expires_at_str, str):
                from datetime import datetime
                expires_at = datetime.fromisoformat(expires_at_str.replace('Z', '+00:00'))
                expiry_text = expires_at.strftime('%Y-%m-%d')
            else:
                expiry_text = "неизвестно"

            # Get payment method
            payment_method = subscription.get('payment_method', 'unknown')
            payment_method_text = {
                'telegram_stars': '⭐ Telegram Stars',
                'yookassa': '💳 Банковская карта',
                'card_dryrun': '💳 Карта (тест)',
                'stars_dryrun': '⭐ Stars (тест)',
                'tribute': '🎁 Tribute',
                'manual': '👤 Вручную'
            }.get(payment_method, payment_method)

            # Show confirmation
            message = "❌ Отмена подписки\n\n"
            message += "Ты уверен?\n\n"
            message += f"Способ оплаты: {payment_method_text}\n"
            message += f"Активна до: {expiry_text}\n\n"
            message += "После отмены:\n"
            message += "• Подписка будет деактивирована немедленно\n"
            message += "• Доступ к Pro функциям прекратится\n"
            message += "• Вернёшься на Free тариф\n"
            message += "• Возврат средств не предусмотрен\n\n"
            message += "⚠️ Это действие необратимо!"

            keyboard = [
                [InlineKeyboardButton("✅ Да, отменить", callback_data=sign_callback_data("confirm_cancel_subscription"))],
                [InlineKeyboardButton("❌ Нет, оставить", callback_data=sign_callback_data("show_premium"))]
            ]

            reply_markup = InlineKeyboardMarkup(keyboard)
            await query.edit_message_text(message, reply_markup=reply_markup)

        elif action == "confirm_cancel_subscription":
            # Actually cancel the subscription
            from services import DBService, SubscriptionService
            from datetime import datetime

            user_id = query.from_user.id

            try:
                # Initialize services
                db = DBService()
                sub_service = SubscriptionService(db)

                # Get subscription for logging
                subscription = await db.get_subscription(user_id)
                payment_method = subscription.get('payment_method', 'unknown') if subscription else 'unknown'

                # DRY RUN MODE: Just deactivate without any API calls
                if config.PAYMENT_DRY_RUN:
                    logger.info(f"[DRY RUN] Cancelling subscription for user {user_id}")

                    # Deactivate subscription
                    success = await db.deactivate_subscription(user_id)

                    if success:
                        # Block excess custom personalities (Pro->Free: keep 0, block all)
                        await db.block_excess_custom_personalities(user_id, limit=0)

                        message = "✅ Подписка отменена! (DRY RUN)\n\n"
                        message += "🎉 Отмена выполнена в тестовом режиме.\n\n"
                        message += "Ты вернулся на Free тариф:\n"
                        message += "• 30 сообщений/день\n"
                        message += "• 3 саммари в ЛС/день\n"
                        message += "• 3 саммари в группах/день\n"
                        message += "• 5 использований личности/день\n\n"
                        message += "⚠️ Это был тестовый режим.\n"
                        message += "Для реальной отмены отключи PAYMENT_DRY_RUN."

                        keyboard = [[InlineKeyboardButton("« К Premium", callback_data=sign_callback_data("show_premium"))]]
                        reply_markup = InlineKeyboardMarkup(keyboard)
                        await query.edit_message_text(message, reply_markup=reply_markup)
                        return

                # REAL MODE: Cancel subscription
                # Note: Both Telegram Stars and YooKassa in our implementation are one-time payments,
                # not recurring subscriptions. So we just deactivate the subscription in DB.
                # No API calls needed to payment providers.

                logger.info(
                    f"Cancelling subscription for user {user_id}, "
                    f"payment_method={payment_method}"
                )

                # Deactivate subscription
                success = await db.deactivate_subscription(user_id)

                if success:
                    # Block excess custom personalities (Pro->Free: keep 0, block all)
                    await db.block_excess_custom_personalities(user_id, limit=0)

                    message = "✅ Подписка отменена!\n\n"
                    message += "Ты вернулся на Free тариф:\n"
                    message += "• 30 сообщений/день\n"
                    message += "• 3 саммари в ЛС/день\n"
                    message += "• 3 саммари в группах/день\n"
                    message += "• 5 использований личности/день\n\n"
                    message += "💡 Ты всегда можешь вернуться к Pro!\n"
                    message += "Используй /premium для повторной подписки."

                    keyboard = [[InlineKeyboardButton("« К Premium", callback_data=sign_callback_data("show_premium"))]]
                    reply_markup = InlineKeyboardMarkup(keyboard)
                    await query.edit_message_text(message, reply_markup=reply_markup)

                    logger.info(f"Subscription cancelled successfully for user {user_id}")
                else:
                    logger.error(f"Failed to cancel subscription for user {user_id}")
                    await query.edit_message_text(
                        "❌ Ошибка при отмене подписки.\n\n"
                        "Попробуй позже или обратись в поддержку.",
                        reply_markup=InlineKeyboardMarkup([[
                            InlineKeyboardButton("« Назад", callback_data=sign_callback_data("show_premium"))
                        ]])
                    )

            except Exception as e:
                logger.error(f"Error cancelling subscription for user {user_id}: {e}", exc_info=True)
                await query.edit_message_text(
                    "❌ Критическая ошибка при отмене подписки.\n\n"
                    "Обратись в поддержку.",
                    reply_markup=InlineKeyboardMarkup([[
                        InlineKeyboardButton("« Назад", callback_data=sign_callback_data("show_premium"))
                    ]])
                )

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

💎 **Premium:**
/premium — узнать о Pro-подписке
/mystatus — проверить свой статус и использование

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


async def premium_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Handle /premium command
    Show available subscription tiers and pricing
    """
    from services import DBService, SubscriptionService

    user_id = update.effective_user.id

    # Get user's current tier
    db = DBService()
    sub_service = SubscriptionService(db)
    current_tier = await sub_service.get_user_tier(user_id)

    # Build message
    message = "💎 Premium планы\n\n"

    # Free tier
    if current_tier == 'free':
        message += "🆓 FREE (текущий план)\n"
    else:
        message += "🆓 FREE\n"
    message += "• 30 сообщений/день\n"
    message += "• 3 саммари в ЛС/день\n"
    message += "• 3 саммари в группах/день\n"
    message += "• 5 использований личности/день\n"
    message += "• 0 кастомных личностей\n\n"

    # Pro tier
    if current_tier == 'pro':
        message += "⭐ PRO (текущий план)\n"
    else:
        message += "⭐ PRO - $2.99/мес\n"
    message += "• 500 сообщений/день\n"
    message += "• 10 саммари в ЛС/день\n"
    message += "• 20 саммари в группах/день\n"
    message += "• Безлимитные личности ♾️\n"
    message += "• 3 кастомные личности\n"
    message += "• Приоритетная обработка\n\n"

    # Group bonus info
    message += "🎁 Бонус за группу:\n"
    message += "Вступи в нашу группу и получи +1 кастомную личность!\n\n"

    # Buttons
    keyboard = []

    if current_tier != 'pro':
        # Show buy button only for non-Pro users
        keyboard.append([InlineKeyboardButton("💳 Купить Pro", callback_data=sign_callback_data("buy_pro"))])
    else:
        # Show cancel button only for active Pro users
        subscription = await db.get_subscription(user_id)
        if subscription and subscription.get('is_active'):
            keyboard.append([InlineKeyboardButton("❌ Отменить подписку", callback_data=sign_callback_data("cancel_subscription"))])

    # Tribute donation link
    if config.TRIBUTE_URL and config.TRIBUTE_URL != 'https://tribute.to/your_bot_page':
        keyboard.append([InlineKeyboardButton("🎁 Поддержать (Tribute.to)", url=config.TRIBUTE_URL)])

    # Back button
    keyboard.append([InlineKeyboardButton("« Назад", callback_data=sign_callback_data("back_to_main"))])

    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(message, reply_markup=reply_markup)


async def mystatus_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Handle /mystatus command
    Show current subscription status and usage statistics
    """
    from services import DBService, SubscriptionService
    from datetime import datetime, date, timezone

    user_id = update.effective_user.id

    # Get services
    db = DBService()
    sub_service = SubscriptionService(db)

    # Get tier and usage
    tier = await sub_service.get_user_tier(user_id)
    usage = await db.get_usage_limits(user_id, date.today())

    # Emoji and name for tier
    tier_emoji = "💎" if tier == 'pro' else "🆓"
    tier_name = "Pro" if tier == 'pro' else "Free"

    message = f"📊 Твой статус\n\n"
    message += f"Тариф: {tier_emoji} {tier_name}\n"

    # If Pro - show expiration date
    if tier == 'pro':
        subscription = await db.get_subscription(user_id)
        if subscription and subscription.get('expires_at'):
            expires_at_str = subscription.get('expires_at')

            # Parse ISO string to datetime
            if isinstance(expires_at_str, str):
                expires_at = datetime.fromisoformat(expires_at_str.replace('Z', '+00:00'))
            else:
                expires_at = expires_at_str

            # Ensure timezone-aware datetime
            if expires_at.tzinfo is None:
                expires_at = expires_at.replace(tzinfo=timezone.utc)

            # Calculate days left
            days_left = (expires_at - datetime.now(timezone.utc)).days

            message += f"Активен до: {expires_at.strftime('%Y-%m-%d')}\n"
            message += f"Осталось: {days_left} дней\n"

    message += "\n"

    # Get limits for user's tier
    limits = config.TIER_LIMITS[tier]

    # Usage today
    message += "Использовано сегодня:\n"

    messages_count = usage.get('messages_count', 0) if usage else 0
    summaries_dm_count = usage.get('summaries_dm_count', 0) if usage else 0
    summaries_group_count = usage.get('summaries_count', 0) if usage else 0
    judge_count = usage.get('judge_count', 0) if usage else 0

    message += f"💬 Сообщения: {messages_count}/{limits['messages_dm']}\n"
    message += f"📝 Саммари (ЛС): {summaries_dm_count}/{limits['summaries_dm']}\n"
    message += f"📊 Саммари (группы): {summaries_group_count}/{limits['summaries_group']}\n"
    message += f"⚖️ Судейство: {judge_count}/{limits['judge']}\n"

    # Personality info
    if tier == 'pro':
        message += "\n✨ Личности: Безлимитно ♾️\n"
    else:
        message += "\n🎭 Личности: 5 использований/день (кроме Нейтральной)\n"

        # Show top 3 used personalities for Free users
        top_personalities = await db.get_top_personality_usage(user_id, date.today(), limit=3)
        if top_personalities:
            message += "\nИспользовано сегодня:\n"
            for pu in top_personalities:
                personality_name = pu.get('personality_name', 'Unknown')
                summary_count = pu.get('summary_count', 0)
                chat_count = pu.get('chat_count', 0)
                judge_count = pu.get('judge_count', 0)
                total = pu.get('total_usage', 0)

                # Get personality display name
                personality = db.get_personality(personality_name)
                display_name = personality.display_name if personality else personality_name

                message += f"  • {display_name}: {total}/15 "
                message += f"(📝{summary_count} 💬{chat_count} ⚖️{judge_count})\n"

    # Call to action for Free users
    if tier == 'free':
        message += "\n💡 Обновись до Pro: /premium"

    await update.message.reply_text(message)


async def grantpro_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    ADMIN ONLY: Grant Pro subscription to a user
    Usage: /grantpro <user_id> <days>

    Security features:
    - Admin ID verification
    - Input validation
    - Logging all operations
    - Error handling
    """
    from services import DBService, SubscriptionService
    from datetime import datetime

    admin_id = update.effective_user.id

    # === SECURITY: Admin verification ===
    if admin_id != config.ADMIN_USER_ID:
        logger.warning(f"Unauthorized /grantpro attempt by user {admin_id}")
        await update.message.reply_text("⛔ Доступ запрещён. Эта команда только для администратора.")
        return

    # === SECURITY: Input validation ===
    try:
        args = context.args
        if not args or len(args) < 1:
            await update.message.reply_text(
                "❌ Неверный формат команды.\n\n"
                "Использование: /grantpro <user_id> <days>\n"
                "Пример: /grantpro 123456789 30\n\n"
                "• user_id - Telegram ID пользователя\n"
                "• days - Количество дней (по умолчанию 30)"
            )
            return

        # Parse and validate user_id
        target_user_id = int(args[0])
        if target_user_id <= 0:
            await update.message.reply_text("❌ Неверный user_id. Должен быть положительным числом.")
            return

        # Parse and validate duration
        duration_days = int(args[1]) if len(args) > 1 else 30
        if duration_days <= 0 or duration_days > 3650:  # Max 10 years
            await update.message.reply_text("❌ Неверная длительность. Допустимо: 1-3650 дней.")
            return

    except ValueError as e:
        logger.error(f"Invalid input for /grantpro: {e}")
        await update.message.reply_text(
            "❌ Ошибка парсинга аргументов.\n\n"
            "Использование: /grantpro <user_id> <days>\n"
            "Оба параметра должны быть числами."
        )
        return

    # === SECURITY: Confirm before activation ===
    # Log the operation BEFORE executing
    logger.info(
        f"Admin {admin_id} initiating Pro subscription grant: "
        f"target_user={target_user_id}, duration={duration_days} days"
    )

    try:
        # Initialize services
        db = DBService()
        sub_service = SubscriptionService(db)

        # Activate subscription
        success = await sub_service.create_or_update_subscription(
            user_id=target_user_id,
            tier='pro',
            duration_days=duration_days,
            payment_method='tribute',
            transaction_id=f'manual_grant_{admin_id}_{int(datetime.now().timestamp())}'
        )

        if success:
            # Log successful activation
            logger.info(
                f"Pro subscription granted successfully: "
                f"user={target_user_id}, days={duration_days}, admin={admin_id}"
            )

            # Calculate expiry date
            from datetime import timedelta
            expires_at = datetime.now() + timedelta(days=duration_days)

            # Confirm to admin
            await update.message.reply_text(
                f"✅ Pro-подписка успешно активирована!\n\n"
                f"👤 User ID: {target_user_id}\n"
                f"⏰ Срок: {duration_days} дней\n"
                f"📅 Истекает: {expires_at.strftime('%Y-%m-%d %H:%M')}\n\n"
                f"Пользователь получит уведомление."
            )

            # === SECURITY: Notify user (but handle failures gracefully) ===
            try:
                await context.bot.send_message(
                    chat_id=target_user_id,
                    text=(
                        f"🎉 Поздравляем!\n\n"
                        f"Ваша Pro-подписка активирована на {duration_days} дней.\n"
                        f"Теперь доступны:\n"
                        f"• Безлимитные личности ♾️\n"
                        f"• 500 сообщений/день\n"
                        f"• 3 кастомные личности\n"
                        f"• Приоритетная обработка\n\n"
                        f"Проверить статус: /mystatus\n"
                        f"Подписка истекает: {expires_at.strftime('%Y-%m-%d')}"
                    )
                )
                logger.info(f"User {target_user_id} notified about Pro activation")
            except Exception as notify_error:
                logger.error(f"Failed to notify user {target_user_id}: {notify_error}")
                await update.message.reply_text(
                    f"⚠️ Подписка активирована, но не удалось отправить уведомление пользователю.\n"
                    f"Возможно, пользователь не начал диалог с ботом."
                )
        else:
            # Log failure
            logger.error(f"Failed to grant Pro subscription to user {target_user_id}")
            await update.message.reply_text("❌ Ошибка активации подписки. Проверьте логи.")

    except Exception as e:
        logger.error(f"Error in /grantpro command: {e}", exc_info=True)
        await update.message.reply_text(
            f"❌ Критическая ошибка при активации подписки.\n"
            f"Ошибка: {str(e)}\n\n"
            f"Проверьте логи для подробностей."
        )


# ================================================
# TELEGRAM STARS PAYMENT HANDLERS
# ================================================

async def handle_pre_checkout_query(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Handle PreCheckoutQuery for Telegram Stars payments

    This handler is called BEFORE the payment is processed.
    We need to answer OK to allow the payment to proceed.

    Security:
        - Validates payload format
        - Logs all pre-checkout attempts
        - Always answers OK (additional validation in SuccessfulPayment)

    Note:
        According to Telegram docs, we must answer within 10 seconds
    """
    query = update.pre_checkout_query
    user_id = query.from_user.id
    payload = query.invoice_payload

    try:
        logger.info(
            f"PreCheckoutQuery received: "
            f"user={user_id}, payload={payload}, "
            f"currency={query.currency}, amount={query.total_amount}"
        )

        # Validate payload format
        # Expected format: "stars_<user_id>_<tier>_<days>_<timestamp>"
        if not payload.startswith("stars_"):
            logger.warning(f"Invalid payload format: {payload}")
            await query.answer(
                ok=False,
                error_message="Недействительный счёт. Попробуйте создать новый."
            )
            return

        # Parse payload
        parts = payload.split("_")
        if len(parts) != 5:
            logger.warning(f"Invalid payload structure: {payload}")
            await query.answer(
                ok=False,
                error_message="Ошибка обработки счёта. Попробуйте создать новый."
            )
            return

        # Extract user_id from payload for verification
        payload_user_id = int(parts[1])

        # Verify user_id matches
        if payload_user_id != user_id:
            logger.error(
                f"User ID mismatch: payload={payload_user_id}, actual={user_id}"
            )
            await query.answer(
                ok=False,
                error_message="Ошибка безопасности. Обратитесь в поддержку."
            )
            return

        # All checks passed - approve payment
        await query.answer(ok=True)
        logger.info(f"PreCheckoutQuery approved for user {user_id}")

    except ValueError as e:
        logger.error(f"Error parsing payload '{payload}': {e}")
        await query.answer(
            ok=False,
            error_message="Ошибка обработки данных. Попробуйте создать новый счёт."
        )
    except Exception as e:
        logger.error(f"Error in PreCheckoutQuery handler: {e}", exc_info=True)
        # In case of error, still approve to avoid blocking user
        # Validation will happen in SuccessfulPayment handler
        await query.answer(ok=True)


async def handle_successful_payment(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Handle SuccessfulPayment for Telegram Stars

    This handler is called AFTER the payment has been successfully processed.
    We need to activate the subscription for the user.

    Security:
        - Verifies payload format and user_id
        - Creates unique transaction_id for audit trail
        - Full logging of all operations
        - Notifies user about activation

    Flow:
        1. Extract payment details from update
        2. Parse payload to get tier and duration
        3. Activate subscription in database
        4. Send confirmation to user
    """
    user_id = update.effective_user.id
    payment = update.message.successful_payment

    try:
        logger.info(
            f"SuccessfulPayment received: "
            f"user={user_id}, currency={payment.currency}, "
            f"amount={payment.total_amount}, payload={payment.invoice_payload}"
        )

        # Parse payload
        # Format: "stars_<user_id>_<tier>_<days>_<timestamp>"
        payload = payment.invoice_payload
        parts = payload.split("_")

        if len(parts) != 5 or parts[0] != "stars":
            logger.error(f"Invalid payment payload: {payload}")
            await update.message.reply_text(
                "❌ Ошибка обработки платежа.\n"
                "Обратитесь в поддержку с номером транзакции:\n"
                f"`{payment.telegram_payment_charge_id}`",
                parse_mode='Markdown'
            )
            return

        # Extract data
        payload_user_id = int(parts[1])
        tier = parts[2]
        duration_days = int(parts[3])
        timestamp = int(parts[4])

        # Verify user_id (double-check for security)
        if payload_user_id != user_id:
            logger.error(
                f"SuccessfulPayment: User ID mismatch! "
                f"payload={payload_user_id}, actual={user_id}"
            )
            await update.message.reply_text(
                "❌ Ошибка безопасности при обработке платежа.\n"
                "Обратитесь в поддержку."
            )
            return

        # Import subscription service
        from services import DBService, SubscriptionService
        from datetime import datetime, timedelta

        db = DBService()
        sub_service = SubscriptionService(db)

        # Create or update subscription
        success = await sub_service.create_or_update_subscription(
            user_id=user_id,
            tier=tier,
            duration_days=duration_days,
            payment_method='telegram_stars',
            transaction_id=payment.telegram_payment_charge_id
        )

        if success:
            # Calculate expiry date
            expires_at = datetime.now() + timedelta(days=duration_days)

            # Send success message
            await update.message.reply_text(
                f"🎉 Оплата прошла успешно!\n\n"
                f"Pro-подписка активирована на {duration_days} дней.\n\n"
                f"Теперь доступны:\n"
                f"• Безлимитные личности ♾️\n"
                f"• 500 сообщений/день\n"
                f"• 20 саммари в группах/день\n"
                f"• 3 кастомные личности\n"
                f"• Приоритетная обработка\n\n"
                f"Проверить статус: /mystatus\n"
                f"Подписка истекает: {expires_at.strftime('%Y-%m-%d')}"
            )

            logger.info(
                f"Pro subscription activated via Stars: "
                f"user={user_id}, tier={tier}, days={duration_days}, "
                f"tx_id={payment.telegram_payment_charge_id}"
            )
        else:
            logger.error(f"Failed to activate subscription for user {user_id}")
            await update.message.reply_text(
                "❌ Платеж получен, но возникла ошибка при активации подписки.\n\n"
                "Обратитесь в поддержку с номером транзакции:\n"
                f"`{payment.telegram_payment_charge_id}`",
                parse_mode='Markdown'
            )

    except ValueError as e:
        logger.error(f"Error parsing payment data: {e}")
        await update.message.reply_text(
            "❌ Ошибка обработки данных платежа.\n"
            "Обратитесь в поддержку."
        )
    except Exception as e:
        logger.error(f"Error in SuccessfulPayment handler: {e}", exc_info=True)
        await update.message.reply_text(
            "❌ Критическая ошибка при обработке платежа.\n"
            "Ваши средства не потеряны. Обратитесь в поддержку."
        )
