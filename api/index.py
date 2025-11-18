"""
Telegram Bot Webhook Handler - FIXED VERSION
Entry point for Vercel serverless function

FIX: Removed Werkzeug dependency, using pure WSGI
FIX: Graceful degradation - no raise in imports
"""

import sys
import json
import asyncio
from datetime import datetime


def log(message):
    """Print log with timestamp to stderr (errors and warnings only)"""
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    print(f"[{timestamp}] {message}", file=sys.stderr, flush=True)


def verbose_log(message):
    """Print verbose log only if VERBOSE_LOGGING is enabled"""
    # Will be set after config import
    if hasattr(verbose_log, 'enabled') and verbose_log.enabled:
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        print(f"[{timestamp}] {message}", file=sys.stderr, flush=True)

# Default: disabled
verbose_log.enabled = False

# Import success flags
telegram_imported = False
config_imported = False
services_imported = False
modules_imported = False
bot_initialized = False

# ================================================
# CHECKPOINT 2: Import telegram
# ================================================
try:
    from telegram import Update
    from telegram.ext import (
        Application,
        CommandHandler,
        MessageHandler,
        CallbackQueryHandler,
        ConversationHandler,
        ChatMemberHandler,
        filters
    )
    from telegram.constants import ChatType
    telegram_imported = True
    verbose_log("✅ CHECKPOINT 2: telegram imports successful")
except Exception as e:
    log(f"❌ CHECKPOINT 2 FAILED: telegram import error: {e}")

# ================================================
# CHECKPOINT 3: Import config
# ================================================
try:
    import config
    from config import logger
    config_imported = True
    # Enable verbose logging if configured
    verbose_log.enabled = config.VERBOSE_LOGGING
    verbose_log("✅ CHECKPOINT 3: config import successful")
except Exception as e:
    log(f"❌ CHECKPOINT 3 FAILED: config import error: {e}")
    # Create dummy logger for diagnostics
    import logging
    logger = logging.getLogger(__name__)

# ================================================
# CHECKPOINT 4: Import services
# ================================================
try:
    from services import DBService, SupabasePersistence
    services_imported = True
    verbose_log("✅ CHECKPOINT 4: services import successful")
except Exception as e:
    log(f"❌ CHECKPOINT 4 FAILED: services import error: {e}")

# ================================================
# CHECKPOINT 5: Import modules
# ================================================
try:
    from modules.commands import (
        start_command,
        help_command,
        stats_command,
        premium_command,
        mystatus_command,
        grantpro_command,
        handle_start_menu_callback,
        handle_pre_checkout_query,
        handle_successful_payment
    )
    from modules.summaries import (
        summary_command,
        summary_callback,
        summary_personality_callback,
        summary_timeframe_callback,
        dm_summary_personality_callback,
        back_to_summary_personality_callback
    )
    from modules.judge import (
        judge_command,
        handle_judge_personality_callback,
        handle_judge_cancel_callback,
        receive_dispute_description,
        cancel_judge,
        AWAITING_DISPUTE_DESCRIPTION
    )
    from modules.personalities import (
        personality_command,
        personality_callback,
        receive_personality_name,
        receive_personality_description,
        cancel_personality_creation,
        edit_callback,
        receive_edited_name,
        receive_edited_emoji,
        receive_edited_description,
        AWAITING_NAME,
        AWAITING_DESCRIPTION,
        AWAITING_EDIT_CHOICE,
        AWAITING_EDIT_NAME,
        AWAITING_EDIT_EMOJI,
        AWAITING_EDIT_DESCRIPTION
    )
    from modules.direct_chat import (
        handle_personality_selection,
        handle_direct_message,
        handle_end_group_chat_callback,
        chat_command,
        stop_command,
        handle_start_chat_callback,
        handle_group_chat_message
    )
    modules_imported = True
    verbose_log("✅ CHECKPOINT 5: modules import successful")
except Exception as e:
    log(f"❌ CHECKPOINT 5 FAILED: modules import error: {e}")

verbose_log("✅ CHECKPOINT 6: All imports completed")

# Check if we can initialize bot
bot_initialized = telegram_imported and config_imported
if bot_initialized:
    verbose_log("✅ CHECKPOINT 7: Bot can be initialized (will create Application per request)")
else:
    log("⚠️ CHECKPOINT 7: Required imports missing, bot cannot be initialized")


# ================================================
# Message handlers (only if bot initialized)
# ================================================
if bot_initialized:
    async def log_message_to_db(update: Update, context) -> None:
        """Log all text messages to database"""
        if not update.message or not update.message.text:
            return

        message = update.message
        chat = message.chat
        user = message.from_user

        # Only log messages from groups
        if chat.type in [ChatType.GROUP, ChatType.SUPERGROUP]:
            db = DBService()

            # Save message - use first_name instead of username
            db.save_message(
                chat_id=chat.id,
                user_id=user.id if user else None,
                username=user.first_name if user else None,  # FIX: Use first_name instead of username
                message_text=message.text
            )

            # Update chat metadata
            db.save_chat_metadata(
                chat_id=chat.id,
                chat_title=chat.title,
                chat_type=chat.type
            )

            logger.debug(f"Logged message from {user.first_name if user else 'unknown'} in chat {chat.id}")


    async def handle_bot_added_to_chat(update: Update, context) -> None:
        """Handle bot being added to a chat"""
        from telegram import InlineKeyboardButton, InlineKeyboardMarkup
        from utils.security import sign_callback_data

        message = update.message
        chat = message.chat

        # Check if bot was added
        for member in message.new_chat_members:
            if member.id == context.bot.id:
                logger.info(f"Bot added to chat {chat.id} ({chat.title})")

                # Save chat metadata
                db = DBService()
                db.save_chat_metadata(
                    chat_id=chat.id,
                    chat_title=chat.title,
                    chat_type=chat.type
                )

                # Send welcome message with inline buttons
                welcome_text = f"""👋 Привет! Я бот с разными личностями.

📝 **Важно:** Я могу саммаризировать и рассуждать только те сообщения, которые появятся **после** моего добавления в чат. История до моего прихода мне не видна!

🎭 **Выбери что сделать:**"""

                # Create inline keyboard (same as /start for groups)
                keyboard = [
                    [InlineKeyboardButton("📝 Сделать саммари", callback_data=sign_callback_data("group_summary"))],
                    [InlineKeyboardButton("💬 Общаться напрямую", callback_data=sign_callback_data("direct_chat"))],
                    [InlineKeyboardButton("⚖️ Рассудить", callback_data=sign_callback_data("group_judge"))],
                    [InlineKeyboardButton("🎭 Настроить личность", callback_data=sign_callback_data("setup_personality"))]
                ]
                reply_markup = InlineKeyboardMarkup(keyboard)

                try:
                    await context.bot.send_message(
                        chat_id=chat.id,
                        text=welcome_text,
                        reply_markup=reply_markup
                    )
                    logger.info(f"Welcome message sent to chat {chat.id}")
                except Exception as e:
                    logger.error(f"Error sending welcome message: {e}")

                break


    async def handle_bot_removed_from_chat(update: Update, context) -> None:
        """Handle bot being removed from a chat"""
        message = update.message
        chat = message.chat
        left_member = message.left_chat_member

        # Check if bot was removed
        if left_member and left_member.id == context.bot.id:
            logger.info(f"Bot removed from chat {chat.id} ({chat.title})")

            # Delete all data for this chat
            db = DBService()
            db.delete_messages_by_chat(chat.id)
            db.delete_chat_metadata(chat.id)

            logger.info(f"Deleted all data for chat {chat.id}")


    async def handle_chat_member_update(update: Update, context) -> None:
        """
        Handle user joining or leaving a chat
        Used to track membership in the project group for bonus features
        """
        try:
            # Get chat member update
            chat_member_update = update.chat_member

            if not chat_member_update:
                return

            # Check if this is the project group
            if not config.PROJECT_TELEGRAM_GROUP_ID:
                return

            if chat_member_update.chat.id != config.PROJECT_TELEGRAM_GROUP_ID:
                return

            # Get user and status changes
            user_id = chat_member_update.new_chat_member.user.id
            old_status = chat_member_update.old_chat_member.status
            new_status = chat_member_update.new_chat_member.status

            # Determine if user joined or left
            was_member = old_status in ['member', 'administrator', 'creator']
            is_member = new_status in ['member', 'administrator', 'creator']

            # Only process if membership changed
            if was_member != is_member:
                logger.info(f"Group membership changed for user {user_id}: was_member={was_member}, is_member={is_member}")

                # Initialize subscription service
                from services.subscription import get_subscription_service
                subscription_service = get_subscription_service()

                # Handle membership change
                await subscription_service.handle_group_membership_change(
                    user_id=user_id,
                    is_member=is_member,
                    bot=context.bot
                )

        except Exception as e:
            logger.error(f"Error handling chat member update: {e}")


# ================================================
# CHECKPOINT 8: Create bot application function
# ================================================
def create_bot_application():
    """
    Create and configure a new bot Application instance

    FIX: Creating new Application per request to avoid event loop issues in serverless
    FIX: Added persistence for ConversationHandler in serverless environment
    """
    if not bot_initialized or not modules_imported:
        raise RuntimeError("Cannot create bot application - imports failed")

    # Create persistence for ConversationHandler
    persistence = SupabasePersistence()

    app = Application.builder()\
        .token(config.TELEGRAM_BOT_TOKEN)\
        .persistence(persistence)\
        .build()

    # Initialize subscription service (needed for personality limits, etc.)
    from services.subscription import init_subscription_service
    db = DBService()
    init_subscription_service(db)
    verbose_log("✅ Subscription service initialized")

    # Basic commands
    app.add_handler(CommandHandler("start", start_command))
    app.add_handler(CommandHandler(config.COMMAND_HELP, help_command))
    app.add_handler(CommandHandler("stats", stats_command))
    app.add_handler(CommandHandler("premium", premium_command))
    app.add_handler(CommandHandler("mystatus", mystatus_command))
    app.add_handler(CommandHandler("grantpro", grantpro_command))  # ADMIN ONLY

    # Summary command
    app.add_handler(CommandHandler(config.COMMAND_SUMMARY, summary_command))
    app.add_handler(CallbackQueryHandler(
        summary_callback,
        pattern="^summary:"
    ))
    app.add_handler(CallbackQueryHandler(
        summary_personality_callback,
        pattern="^summary_personality:"
    ))
    app.add_handler(CallbackQueryHandler(
        summary_timeframe_callback,
        pattern="^summary_timeframe:"
    ))
    app.add_handler(CallbackQueryHandler(
        dm_summary_personality_callback,
        pattern="^dm_summary_personality:"
    ))
    app.add_handler(CallbackQueryHandler(
        back_to_summary_personality_callback,
        pattern="^back_to_summary_personality:"
    ))

    # Chat commands (group chat sessions)
    app.add_handler(CommandHandler(config.COMMAND_CHAT, chat_command))
    app.add_handler(CommandHandler(config.COMMAND_STOP, stop_command))

    # Judge command with ConversationHandler (groups only)
    judge_conv = ConversationHandler(
        entry_points=[
            CommandHandler(config.COMMAND_JUDGE, judge_command, filters=filters.ChatType.GROUPS)
        ],
        states={
            AWAITING_DISPUTE_DESCRIPTION: [
                MessageHandler(filters.TEXT & ~filters.COMMAND & filters.ChatType.GROUPS, receive_dispute_description)
            ]
        },
        fallbacks=[
            CommandHandler("cancel", cancel_judge, filters=filters.ChatType.GROUPS)
        ],
        name="judge_conversation",
        persistent=True  # Enable persistence for serverless environment
    )
    app.add_handler(judge_conv)

    # Judge personality selection callback (outside ConversationHandler)
    app.add_handler(CallbackQueryHandler(
        handle_judge_personality_callback,
        pattern="^judge_personality:"
    ))

    # Judge cancel callback (back button during personality selection)
    app.add_handler(CallbackQueryHandler(
        handle_judge_cancel_callback,
        pattern="^judge_cancel:"
    ))

    # Personality command with conversation for creating/editing custom ones
    personality_conv = ConversationHandler(
        entry_points=[
            CommandHandler(config.COMMAND_PERSONALITY, personality_command),
            CallbackQueryHandler(personality_callback, pattern="^pers:")
        ],
        states={
            AWAITING_NAME: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, receive_personality_name)
            ],
            # AWAITING_EMOJI step removed - using default emoji 🎭
            AWAITING_DESCRIPTION: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, receive_personality_description)
            ],
            AWAITING_EDIT_CHOICE: [
                CallbackQueryHandler(edit_callback, pattern="^edit:")
            ],
            AWAITING_EDIT_NAME: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, receive_edited_name)
            ],
            AWAITING_EDIT_EMOJI: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, receive_edited_emoji)
            ],
            AWAITING_EDIT_DESCRIPTION: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, receive_edited_description)
            ]
        },
        fallbacks=[
            CommandHandler("cancel", cancel_personality_creation)
        ],
        name="personality_conversation",
        persistent=True  # FIX: Enable persistence for serverless environment
    )
    app.add_handler(personality_conv)

    # Direct chat handlers (Phase 2)
    # Handle /start menu callbacks
    app.add_handler(CallbackQueryHandler(
        handle_start_menu_callback,
        pattern="^(direct_chat|setup_personality|dm_summary|group_summary|group_judge|back_to_main):"
    ))

    # Handle personality selection callbacks
    app.add_handler(CallbackQueryHandler(
        handle_personality_selection,
        pattern="^sel_pers:"
    ))

    # NOTE: "pers:create_start" callback is handled by personality_conv ConversationHandler above

    # Handle group chat session start callback
    app.add_handler(CallbackQueryHandler(
        handle_start_chat_callback,
        pattern="^start_chat:"
    ))

    # Handle group chat session end callback
    app.add_handler(CallbackQueryHandler(
        handle_end_group_chat_callback,
        pattern="^end_group_chat:"
    ))

    # Handle direct messages in private chats (must be after ConversationHandler)
    app.add_handler(MessageHandler(
        filters.TEXT & ~filters.COMMAND & filters.ChatType.PRIVATE,
        handle_direct_message
    ))

    # Log all messages to database FIRST (for groups) - must run before other handlers
    app.add_handler(MessageHandler(
        filters.TEXT & ~filters.COMMAND & filters.ChatType.GROUPS,
        log_message_to_db
    ))

    # Handle group chat messages during active sessions (runs after logging)
    app.add_handler(MessageHandler(
        filters.TEXT & ~filters.COMMAND & filters.ChatType.GROUPS,
        handle_group_chat_message
    ))

    # Handle bot being added/removed from chats
    app.add_handler(MessageHandler(
        filters.StatusUpdate.NEW_CHAT_MEMBERS,
        handle_bot_added_to_chat
    ))
    app.add_handler(MessageHandler(
        filters.StatusUpdate.LEFT_CHAT_MEMBER,
        handle_bot_removed_from_chat
    ))

    # Handle chat member updates (for group membership tracking)
    app.add_handler(ChatMemberHandler(
        handle_chat_member_update,
        ChatMemberHandler.CHAT_MEMBER
    ))

    # ================================================
    # TELEGRAM STARS PAYMENT HANDLERS
    # ================================================
    # Handle pre-checkout query (before payment is processed)
    from telegram.ext import PreCheckoutQueryHandler
    app.add_handler(PreCheckoutQueryHandler(handle_pre_checkout_query))

    # Handle successful payment (after payment is processed)
    app.add_handler(MessageHandler(
        filters.SUCCESSFUL_PAYMENT,
        handle_successful_payment
    ))

    verbose_log("✅ CHECKPOINT 8: Created new bot Application with all handlers")
    return app

if bot_initialized and modules_imported:
    verbose_log("✅ Bot application factory ready")
else:
    log("⚠️ Bot application cannot be created - imports failed")


# ================================================
# CHECKPOINT 9: Webhook processing
# ================================================
async def process_update(update_data: dict):
    """
    Process a single update from Telegram

    FIX: Creating new Application per request to avoid event loop issues
    """
    if not bot_initialized:
        log("⚠️ Cannot process update: bot not initialized")
        return

    app = None
    try:
        verbose_log(f"✅ CHECKPOINT 9: Processing update {update_data.get('update_id', 'unknown')}")

        # Create new Application for this request
        app = create_bot_application()

        # Initialize it
        await app.initialize()
        verbose_log("✅ Application initialized for this request")

        # Process the update
        update = Update.de_json(update_data, app.bot)
        await app.process_update(update)

        verbose_log(f"✅ CHECKPOINT 10: Update processed successfully")
    except Exception as e:
        logger.error(f"Error processing update: {e}", exc_info=True)
        log(f"❌ CHECKPOINT 10 FAILED: Update processing error: {e}")
    finally:
        # Clean up resources
        if app:
            try:
                await app.shutdown()
                verbose_log("✅ Application shutdown complete")
            except Exception as e:
                log(f"⚠️ Error during app shutdown: {e}")


# ================================================
# Pure WSGI Application for Vercel
# ================================================
def application(environ, start_response):
    """
    Pure WSGI application - Vercel Python runtime calls this

    FIX: Using pure WSGI instead of Werkzeug
    """
    try:
        verbose_log("✅ CHECKPOINT 11: WSGI application() called")

        # Get request info from WSGI environ
        method = environ.get('REQUEST_METHOD', 'UNKNOWN')
        path = environ.get('PATH_INFO', 'UNKNOWN')

        verbose_log(f"✅ CHECKPOINT 12: Request = {method} {path}")

        # Only accept POST requests for webhook
        if method != 'POST':
            log(f"⚠️ Non-POST request: {method} {path}")
            status = '200 OK'
            headers = [('Content-Type', 'application/json')]
            start_response(status, headers)

            response_body = json.dumps({
                'status': 'ok',
                'message': 'Bot is running. Use POST for webhook.',
                'method': method,
                'path': path,
                'bot_initialized': bot_initialized
            }).encode('utf-8')

            return [response_body]

        # Check if bot is initialized
        if not bot_initialized:
            log("⚠️ Bot not initialized, cannot process webhook")
            status = '503 Service Unavailable'
            headers = [('Content-Type', 'application/json')]
            start_response(status, headers)

            response_body = json.dumps({
                'error': 'Bot not initialized',
                'telegram_imported': telegram_imported,
                'config_imported': config_imported,
                'services_imported': services_imported,
                'modules_imported': modules_imported
            }).encode('utf-8')

            return [response_body]

        # Read request body
        try:
            content_length = int(environ.get('CONTENT_LENGTH', 0))
        except ValueError:
            content_length = 0

        if content_length > 0:
            request_body = environ['wsgi.input'].read(content_length)
            update_data = json.loads(request_body.decode('utf-8'))
            verbose_log(f"✅ CHECKPOINT 13: Parsed webhook data, update_id={update_data.get('update_id', 'unknown')}")
        else:
            log("⚠️ Empty request body")
            status = '400 Bad Request'
            headers = [('Content-Type', 'application/json')]
            start_response(status, headers)
            return [json.dumps({'error': 'Empty request body'}).encode('utf-8')]

        # Process update asynchronously
        verbose_log("✅ CHECKPOINT 14: Running async update processing")

        # FIX: Use get_event_loop() or create new one for serverless
        try:
            loop = asyncio.get_event_loop()
            if loop.is_closed():
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

        # Run the update processing and wait for all tasks to complete
        loop.run_until_complete(process_update(update_data))

        # Give pending tasks a chance to complete (important for telegram API calls)
        pending = asyncio.all_tasks(loop)
        if pending:
            loop.run_until_complete(asyncio.gather(*pending, return_exceptions=True))

        verbose_log("✅ CHECKPOINT 15: Webhook processed successfully")

        # Return success
        status = '200 OK'
        headers = [('Content-Type', 'application/json')]
        start_response(status, headers)

        response_body = json.dumps({'ok': True}).encode('utf-8')
        return [response_body]

    except Exception as e:
        log(f"❌ ERROR in WSGI app: {e}")
        logger.error(f"Error in webhook handler: {e}", exc_info=True)

        # Error response
        status = '500 Internal Server Error'
        headers = [('Content-Type', 'application/json')]
        start_response(status, headers)

        error_body = json.dumps({
            'error': str(e),
            'ok': False
        }).encode('utf-8')

        return [error_body]


# Vercel looks for 'app' or 'application' in WSGI mode
app = application

verbose_log(f"✅ CHECKPOINT 16: Module fully loaded (bot_initialized={bot_initialized})")


# ================================================
# Local testing
# ================================================
if __name__ == '__main__':
    log("🧪 Running in local test mode")
    print("\n" + "="*60)
    print("Bot status:")
    print(f"  telegram_imported: {telegram_imported}")
    print(f"  config_imported: {config_imported}")
    print(f"  services_imported: {services_imported}")
    print(f"  modules_imported: {modules_imported}")
    print(f"  bot_initialized: {bot_initialized}")
    if bot_initialized:
        print(f"  handlers: {len(bot_application.handlers)}")
    print("="*60 + "\n")
