"""
Telegram Bot Webhook Handler
Entry point for Vercel serverless function
"""

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
import json
import config
from config import logger
from services import DBService

# Import command handlers
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


# Initialize bot application (lazy initialization)
application = None


def get_application():
    """Get or create the Application instance"""
    global application
    if application is None:
        application = Application.builder().token(config.TELEGRAM_BOT_TOKEN).build()
        setup_handlers()
    return application


def setup_handlers():
    """Setup all command and message handlers"""
    global application

    # Basic commands
    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(CommandHandler(config.COMMAND_HELP, help_command))

    # Summary command
    application.add_handler(CommandHandler(config.COMMAND_SUMMARY, summary_command))
    application.add_handler(CallbackQueryHandler(
        summary_callback,
        pattern="^summary:"
    ))

    # Judge command
    application.add_handler(CommandHandler(config.COMMAND_JUDGE, judge_command))

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
    application.add_handler(personality_conv)

    # Log all messages to database
    application.add_handler(MessageHandler(
        filters.TEXT & ~filters.COMMAND,
        log_message_to_db
    ))

    # Handle bot being added/removed from chats
    application.add_handler(MessageHandler(
        filters.StatusUpdate.NEW_CHAT_MEMBERS,
        handle_bot_added_to_chat
    ))
    application.add_handler(MessageHandler(
        filters.StatusUpdate.LEFT_CHAT_MEMBER,
        handle_bot_removed_from_chat
    ))

    logger.info("All handlers registered")


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
# VERCEL SERVERLESS FUNCTION HANDLER
# ================================================

async def process_update(update_data: dict):
    """Process a single update from Telegram"""
    try:
        app = get_application()
        update = Update.de_json(update_data, app.bot)
        await app.process_update(update)
    except Exception as e:
        logger.error(f"Error processing update: {e}", exc_info=True)


def handler(request):
    """
    Vercel serverless function handler

    This is the entry point for webhook requests from Telegram
    """
    try:
        # Only accept POST requests
        if request.method != 'POST':
            return {
                'statusCode': 405,
                'body': json.dumps({'error': 'Method not allowed'})
            }

        # Parse update from request body
        if hasattr(request, 'get_json'):
            # Flask request object
            update_data = request.get_json(force=True)
        elif hasattr(request, 'json'):
            # Vercel request object
            update_data = request.json
        else:
            # Try to parse body as JSON
            import json as json_lib
            body = request.body if hasattr(request, 'body') else request.data
            if isinstance(body, bytes):
                body = body.decode('utf-8')
            update_data = json_lib.loads(body)

        logger.info(f"Received update: {update_data.get('update_id', 'unknown')}")

        # Process update asynchronously
        import asyncio
        asyncio.run(process_update(update_data))

        return {
            'statusCode': 200,
            'body': json.dumps({'ok': True})
        }

    except Exception as e:
        logger.error(f"Error in webhook handler: {e}", exc_info=True)
        return {
            'statusCode': 500,
            'body': json.dumps({'error': str(e)})
        }


# Export handler for Vercel
# Vercel Python runtime expects a callable named 'handler' or 'app'
def app(environ, start_response):
    """WSGI app for Vercel"""
    # Import request wrapper
    from werkzeug.wrappers import Request, Response

    request = Request(environ)
    result = handler(request)

    response = Response(
        result.get('body', '{}'),
        status=result.get('statusCode', 200),
        content_type='application/json'
    )
    return response(environ, start_response)


# For testing locally with Flask
if __name__ == '__main__':
    from flask import Flask, request as flask_request

    flask_app = Flask(__name__)

    @flask_app.route('/', methods=['POST'])
    def webhook():
        return handler(flask_request)

    @flask_app.route('/health', methods=['GET'])
    def health():
        return {'status': 'ok', 'bot': 'chto_bilo_v_chate_bot'}

    logger.info("Starting local test server...")
    flask_app.run(host='0.0.0.0', port=8000, debug=True)
