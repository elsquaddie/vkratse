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
    """Print log with timestamp to stderr"""
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    print(f"[{timestamp}] {message}", file=sys.stderr, flush=True)


# ================================================
# CHECKPOINT 1: Module loaded
# ================================================
log("✅ CHECKPOINT 1: Module api/index.py loaded successfully")

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
        filters
    )
    from telegram.constants import ChatType
    telegram_imported = True
    log("✅ CHECKPOINT 2: telegram imports successful")
except Exception as e:
    log(f"❌ CHECKPOINT 2 FAILED: telegram import error: {e}")

# ================================================
# CHECKPOINT 3: Import config
# ================================================
try:
    import config
    from config import logger
    config_imported = True
    log("✅ CHECKPOINT 3: config import successful")
except Exception as e:
    log(f"❌ CHECKPOINT 3 FAILED: config import error: {e}")
    # Create dummy logger for diagnostics
    import logging
    logger = logging.getLogger(__name__)

# ================================================
# CHECKPOINT 4: Import services
# ================================================
try:
    from services import DBService
    services_imported = True
    log("✅ CHECKPOINT 4: services import successful")
except Exception as e:
    log(f"❌ CHECKPOINT 4 FAILED: services import error: {e}")

# ================================================
# CHECKPOINT 5: Import modules
# ================================================
try:
    from modules.commands import start_command, help_command
    from modules.summaries import summary_command, summary_callback
    from modules.judge import judge_command
    from modules.personalities import (
        personality_command,
        personality_callback,
        receive_personality_name,
        receive_personality_description,
        cancel_personality_creation,
        AWAITING_NAME,
        AWAITING_DESCRIPTION
    )
    modules_imported = True
    log("✅ CHECKPOINT 5: modules import successful")
except Exception as e:
    log(f"❌ CHECKPOINT 5 FAILED: modules import error: {e}")

log("✅ CHECKPOINT 6: All imports completed")

# Global bot application (will be set if initialization succeeds)
bot_application = None
bot_app_initialized = False  # Track if Application.initialize() was called

# ================================================
# CHECKPOINT 7: Initialize bot application
# ================================================
if telegram_imported and config_imported:
    try:
        bot_application = Application.builder().token(config.TELEGRAM_BOT_TOKEN).build()
        bot_initialized = True
        log("✅ CHECKPOINT 7: Bot application initialized")
    except Exception as e:
        log(f"❌ CHECKPOINT 7 FAILED: Bot initialization error: {e}")
        bot_initialized = False
else:
    log("⚠️ CHECKPOINT 7 SKIPPED: Required imports missing")


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

            # Save message
            db.save_message(
                chat_id=chat.id,
                user_id=user.id if user else None,
                username=user.username if user else None,
                message_text=message.text
            )

            # Update chat metadata
            db.save_chat_metadata(
                chat_id=chat.id,
                chat_title=chat.title,
                chat_type=chat.type
            )

            logger.debug(f"Logged message from {user.username if user else 'unknown'} in chat {chat.id}")


    async def handle_bot_added_to_chat(update: Update, context) -> None:
        """Handle bot being added to a chat"""
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

                # Send welcome message
                welcome_text = f"""👋 Привет! Я добавлен в чат.

🎯 Что умею:
• /{config.COMMAND_SUMMARY} — саммари чата
• /{config.COMMAND_JUDGE} — рассудить спор
• /{config.COMMAND_PERSONALITY} — выбрать стиль AI

/{config.COMMAND_HELP} — полная справка"""

                await message.reply_text(welcome_text)
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


# ================================================
# CHECKPOINT 8: Setup handlers
# ================================================
if bot_initialized and modules_imported:
    try:
        # Basic commands
        bot_application.add_handler(CommandHandler("start", start_command))
        bot_application.add_handler(CommandHandler(config.COMMAND_HELP, help_command))

        # Summary command
        bot_application.add_handler(CommandHandler(config.COMMAND_SUMMARY, summary_command))
        bot_application.add_handler(CallbackQueryHandler(
            summary_callback,
            pattern="^summary:"
        ))

        # Judge command
        bot_application.add_handler(CommandHandler(config.COMMAND_JUDGE, judge_command))

        # Personality command with conversation for creating custom ones
        personality_conv = ConversationHandler(
            entry_points=[
                CommandHandler(config.COMMAND_PERSONALITY, personality_command),
                CallbackQueryHandler(personality_callback, pattern="^pers:")
            ],
            states={
                AWAITING_NAME: [
                    MessageHandler(filters.TEXT & ~filters.COMMAND, receive_personality_name)
                ],
                AWAITING_DESCRIPTION: [
                    MessageHandler(filters.TEXT & ~filters.COMMAND, receive_personality_description)
                ]
            },
            fallbacks=[
                CommandHandler("cancel", cancel_personality_creation)
            ],
            name="personality_conversation",
            persistent=False
        )
        bot_application.add_handler(personality_conv)

        # Log all messages to database
        bot_application.add_handler(MessageHandler(
            filters.TEXT & ~filters.COMMAND,
            log_message_to_db
        ))

        # Handle bot being added/removed from chats
        bot_application.add_handler(MessageHandler(
            filters.StatusUpdate.NEW_CHAT_MEMBERS,
            handle_bot_added_to_chat
        ))
        bot_application.add_handler(MessageHandler(
            filters.StatusUpdate.LEFT_CHAT_MEMBER,
            handle_bot_removed_from_chat
        ))

        logger.info("All handlers registered")
        log("✅ CHECKPOINT 8: All handlers registered successfully")
    except Exception as e:
        log(f"❌ CHECKPOINT 8 FAILED: Handler setup error: {e}")
else:
    log("⚠️ CHECKPOINT 8 SKIPPED: Bot not initialized or modules missing")


# ================================================
# CHECKPOINT 9: Webhook processing
# ================================================
async def process_update(update_data: dict):
    """Process a single update from Telegram"""
    global bot_app_initialized

    if not bot_initialized:
        log("⚠️ Cannot process update: bot not initialized")
        return

    try:
        # Initialize Application on first use (lazy initialization)
        if not bot_app_initialized:
            log("⚠️ Initializing bot application (first request)...")
            await bot_application.initialize()
            bot_app_initialized = True
            log("✅ Bot application initialized successfully")

        log(f"✅ CHECKPOINT 9: Processing update {update_data.get('update_id', 'unknown')}")
        update = Update.de_json(update_data, bot_application.bot)
        await bot_application.process_update(update)
        log(f"✅ CHECKPOINT 10: Update processed successfully")
    except Exception as e:
        logger.error(f"Error processing update: {e}", exc_info=True)
        log(f"❌ CHECKPOINT 10 FAILED: Update processing error: {e}")


# ================================================
# Pure WSGI Application for Vercel
# ================================================
def application(environ, start_response):
    """
    Pure WSGI application - Vercel Python runtime calls this

    FIX: Using pure WSGI instead of Werkzeug
    """
    try:
        log("✅ CHECKPOINT 11: WSGI application() called")

        # Get request info from WSGI environ
        method = environ.get('REQUEST_METHOD', 'UNKNOWN')
        path = environ.get('PATH_INFO', 'UNKNOWN')

        log(f"✅ CHECKPOINT 12: Request = {method} {path}")

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
            log(f"✅ CHECKPOINT 13: Parsed webhook data, update_id={update_data.get('update_id', 'unknown')}")
        else:
            log("⚠️ Empty request body")
            status = '400 Bad Request'
            headers = [('Content-Type', 'application/json')]
            start_response(status, headers)
            return [json.dumps({'error': 'Empty request body'}).encode('utf-8')]

        # Process update asynchronously
        log("✅ CHECKPOINT 14: Running async update processing")
        asyncio.run(process_update(update_data))

        log("✅ CHECKPOINT 15: Webhook processed successfully")

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

log(f"✅ CHECKPOINT 16: Module fully loaded (bot_initialized={bot_initialized})")


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
