"""
Telegram Bot Webhook Handler
Entry point for Vercel serverless function
Simplified version using standard Vercel handler pattern
"""

import sys
import traceback
import json
import asyncio
import logging
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

# Setup basic logging first
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Try to import config
try:
    import config
    logger.info("✅ Config imported successfully")
except Exception as e:
    logger.error(f"❌ FATAL ERROR importing config: {e}", exc_info=True)
    print(f"FATAL ERROR importing config: {e}", file=sys.stderr)
    traceback.print_exc()
    raise

# Try to import services
try:
    from services import DBService
    logger.info("✅ Services imported successfully")
except Exception as e:
    logger.error(f"❌ FATAL ERROR importing services: {e}", exc_info=True)
    print(f"FATAL ERROR importing services: {e}", file=sys.stderr)
    traceback.print_exc()
    raise

# Try to import command handlers
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
    logger.info("✅ Modules imported successfully")
except Exception as e:
    logger.error(f"❌ FATAL ERROR importing modules: {e}", exc_info=True)
    print(f"FATAL ERROR importing modules: {e}", file=sys.stderr)
    traceback.print_exc()
    raise


# ================================================
# MESSAGE HANDLERS
# ================================================

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
# TELEGRAM APPLICATION SETUP
# ================================================

def create_application():
    """Create and configure Telegram application"""
    logger.info("🔧 Creating Telegram Application...")

    if not config.TELEGRAM_BOT_TOKEN:
        raise ValueError("TELEGRAM_BOT_TOKEN not set!")

    application = Application.builder().token(config.TELEGRAM_BOT_TOKEN).build()

    logger.info("📝 Registering handlers...")

    # Basic commands
    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(CommandHandler(config.COMMAND_HELP, help_command))

    # Summary command
    application.add_handler(CommandHandler(config.COMMAND_SUMMARY, summary_command))
    application.add_handler(CallbackQueryHandler(summary_callback, pattern="^summary:"))

    # Judge command
    application.add_handler(CommandHandler(config.COMMAND_JUDGE, judge_command))

    # Personality command with conversation
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
        fallbacks=[CommandHandler("cancel", cancel_personality_creation)],
        name="personality_conversation",
        persistent=False
    )
    application.add_handler(personality_conv)

    # Log messages to database
    application.add_handler(MessageHandler(
        filters.TEXT & ~filters.COMMAND,
        log_message_to_db
    ))

    # Handle bot being added/removed
    application.add_handler(MessageHandler(
        filters.StatusUpdate.NEW_CHAT_MEMBERS,
        handle_bot_added_to_chat
    ))
    application.add_handler(MessageHandler(
        filters.StatusUpdate.LEFT_CHAT_MEMBER,
        handle_bot_removed_from_chat
    ))

    logger.info("✅ Application configured successfully")
    return application


# ================================================
# VERCEL HANDLER (Simplified)
# ================================================

async def process_webhook(body_bytes: bytes):
    """Process Telegram webhook update"""
    try:
        # Parse update
        update_data = json.loads(body_bytes.decode('utf-8'))
        logger.info(f"📨 Processing update: {update_data.get('update_id', 'unknown')}")

        # Create application
        application = create_application()

        # Initialize
        await application.initialize()

        try:
            # Create Update object and process it
            update = Update.de_json(update_data, application.bot)
            await application.process_update(update)

            logger.info("✅ Update processed successfully")
            return {'ok': True}

        finally:
            # Always shutdown
            await application.shutdown()

    except Exception as e:
        logger.error(f"❌ Error processing webhook: {e}", exc_info=True)
        return {'error': str(e)}, 500


def handler(request):
    """
    Vercel serverless function handler
    This is the entry point for all HTTP requests
    """
    try:
        logger.info(f"📥 Received {request.method} request")

        # GET = health check
        if request.method == 'GET':
            logger.info("🏥 Health check requested")
            return {
                'statusCode': 200,
                'headers': {'Content-Type': 'application/json'},
                'body': json.dumps({
                    'status': 'ok',
                    'bot': config.BOT_USERNAME,
                    'config': {
                        'telegram_configured': bool(config.TELEGRAM_BOT_TOKEN),
                        'anthropic_configured': bool(config.ANTHROPIC_API_KEY),
                        'supabase_configured': bool(config.SUPABASE_URL and config.SUPABASE_KEY),
                    }
                })
            }

        # POST = webhook from Telegram
        if request.method == 'POST':
            # Get request body
            body = request.body
            if isinstance(body, str):
                body = body.encode('utf-8')

            # Process webhook asynchronously
            result = asyncio.run(process_webhook(body))

            # Check if it's a tuple (result, status) or just result
            if isinstance(result, tuple):
                response_data, status_code = result
            else:
                response_data = result
                status_code = 200

            return {
                'statusCode': status_code,
                'headers': {'Content-Type': 'application/json'},
                'body': json.dumps(response_data)
            }

        # Other methods not allowed
        return {
            'statusCode': 405,
            'headers': {'Content-Type': 'application/json'},
            'body': json.dumps({'error': 'Method not allowed'})
        }

    except Exception as e:
        logger.error(f"💥 CRITICAL ERROR in handler: {e}", exc_info=True)
        print(f"CRITICAL ERROR: {e}", file=sys.stderr)
        traceback.print_exc()

        return {
            'statusCode': 500,
            'headers': {'Content-Type': 'application/json'},
            'body': json.dumps({'error': f'Internal error: {str(e)}'})
        }


# For local testing with Flask
if __name__ == '__main__':
    from flask import Flask, request as flask_request

    flask_app = Flask(__name__)

    @flask_app.route('/', methods=['POST', 'GET'])
    def webhook():
        class FakeRequest:
            def __init__(self, flask_req):
                self.method = flask_req.method
                self.body = flask_req.get_data()
                self.headers = flask_req.headers

        fake_req = FakeRequest(flask_request)
        result = handler(fake_req)

        return (
            result.get('body', '{}'),
            result.get('statusCode', 200),
            {'Content-Type': 'application/json'}
        )

    logger.info("🚀 Starting local test server on http://0.0.0.0:8000")
    flask_app.run(host='0.0.0.0', port=8000, debug=True)
