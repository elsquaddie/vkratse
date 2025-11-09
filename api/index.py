"""
Telegram Bot Webhook Handler
Entry point for Vercel serverless function
Based on working v3 code structure
"""

import sys
import traceback
import json
import asyncio
import logging
from http.server import BaseHTTPRequestHandler
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
# VERCEL HANDLER (BaseHTTPRequestHandler style)
# ================================================

class handler(BaseHTTPRequestHandler):
    """Vercel serverless function handler"""

    async def do_POST_async(self):
        """Process webhook POST request asynchronously"""
        try:
            logger.info("📥 Received POST request")

            # Validate config
            if not config.TELEGRAM_BOT_TOKEN:
                logger.error("❌ TELEGRAM_BOT_TOKEN not set!")
                self.send_response(500)
                self.end_headers()
                return

            # Initialize application
            logger.info("🔧 Initializing Telegram Application...")
            application = Application.builder().token(config.TELEGRAM_BOT_TOKEN).build()

            # Register handlers
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

            # Initialize the application
            logger.info("⚡ Initializing application...")
            await application.initialize()

            try:
                # Read and parse request body
                content_len = int(self.headers.get('Content-Length', 0))
                post_body = self.rfile.read(content_len)
                update_data = json.loads(post_body.decode('utf-8'))

                logger.info(f"📨 Processing update: {update_data.get('update_id', 'unknown')}")

                # Create Update object and process it
                update = Update.de_json(update_data, application.bot)
                await application.process_update(update)

                logger.info("✅ Update processed successfully")

                # Send success response
                self.send_response(200)
                self.send_header('Content-type', 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps({'ok': True}).encode())

            except Exception as e:
                logger.error(f"❌ Error processing update: {e}", exc_info=True)
                self.send_response(500)
                self.send_header('Content-type', 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps({'error': str(e)}).encode())

            finally:
                # Shutdown application
                logger.info("🔚 Shutting down application...")
                await application.shutdown()

        except Exception as e:
            logger.error(f"💥 CRITICAL ERROR in handler: {e}", exc_info=True)
            print(f"CRITICAL ERROR in handler: {e}", file=sys.stderr)
            traceback.print_exc()

            try:
                self.send_response(500)
                self.send_header('Content-type', 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps({'error': f'Internal error: {str(e)}'}).encode())
            except:
                pass

    def do_POST(self):
        """Handle POST request (entry point)"""
        try:
            # Run async handler
            asyncio.run(self.do_POST_async())
        except Exception as e:
            logger.error(f"💥 Error in do_POST: {e}", exc_info=True)
            print(f"Error in do_POST: {e}", file=sys.stderr)
            traceback.print_exc()

    def do_GET(self):
        """Handle GET request (health check)"""
        try:
            logger.info("🏥 Health check requested")

            health_data = {
                'status': 'ok',
                'bot': config.BOT_USERNAME,
                'config': {
                    'telegram_configured': bool(config.TELEGRAM_BOT_TOKEN),
                    'anthropic_configured': bool(config.ANTHROPIC_API_KEY),
                    'supabase_configured': bool(config.SUPABASE_URL and config.SUPABASE_KEY),
                }
            }

            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps(health_data).encode())

        except Exception as e:
            logger.error(f"❌ Error in health check: {e}", exc_info=True)
            self.send_response(500)
            self.end_headers()


# For local testing
if __name__ == '__main__':
    from flask import Flask, request as flask_request

    flask_app = Flask(__name__)

    @flask_app.route('/', methods=['POST'])
    def webhook():
        class FakeRequest:
            def __init__(self, flask_req):
                self.headers = flask_req.headers
                self.rfile = flask_req.stream

        fake_req = FakeRequest(flask_request)
        h = handler(fake_req, ('127.0.0.1', 0), None)
        h.do_POST()
        return {'ok': True}

    @flask_app.route('/health', methods=['GET'])
    def health():
        return {
            'status': 'ok',
            'bot': config.BOT_USERNAME
        }

    logger.info("🚀 Starting local test server...")
    flask_app.run(host='0.0.0.0', port=8000, debug=True)
