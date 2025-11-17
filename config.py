"""
Configuration file for "Что было в чате" bot
All environment variables and settings
"""

import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# ================================================
# TELEGRAM CONFIGURATION
# ================================================
TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
BOT_USERNAME = os.getenv('BOT_USERNAME', 'chto_bilo_v_chate_bot')  # Bot username for deep-links

# ================================================
# AI CONFIGURATION (Anthropic Claude)
# ================================================
ANTHROPIC_API_KEY = os.getenv('ANTHROPIC_API_KEY')
ANTHROPIC_MODEL = os.getenv('ANTHROPIC_MODEL', 'claude-3-7-sonnet-20250219')

# ================================================
# DATABASE CONFIGURATION (Supabase)
# ================================================
SUPABASE_URL = os.getenv('SUPABASE_URL')
SUPABASE_KEY = os.getenv('SUPABASE_KEY')

# ================================================
# SECURITY
# ================================================
SECRET_KEY = os.getenv('SECRET_KEY', 'default_secret_CHANGE_ME_in_production')

# ================================================
# BOT SETTINGS
# ================================================

# Message retention (days) - auto-delete messages older than this
MESSAGE_RETENTION_DAYS = int(os.getenv('MESSAGE_RETENTION_DAYS', 3))

# Default summary period (in hours)
DEFAULT_SUMMARY_HOURS = int(os.getenv('DEFAULT_SUMMARY_HOURS', 24))

# Default personality
DEFAULT_PERSONALITY = os.getenv('DEFAULT_PERSONALITY', 'neutral')

# Cooldown settings (seconds)
COOLDOWN_SECONDS = int(os.getenv('COOLDOWN_SECONDS', 60))

# Rate limiting
RATE_LIMIT_REQUESTS = int(os.getenv('RATE_LIMIT_REQUESTS', 10))
RATE_LIMIT_WINDOW = int(os.getenv('RATE_LIMIT_WINDOW', 60))  # seconds

# Message limits for summaries
MAX_MESSAGES_PER_SUMMARY = int(os.getenv('MAX_MESSAGES_PER_SUMMARY', 400))
DEFAULT_MESSAGE_LIMIT = int(os.getenv('DEFAULT_MESSAGE_LIMIT', 50))

# Custom personality limits
MAX_PERSONALITY_DESCRIPTION_LENGTH = int(os.getenv('MAX_PERSONALITY_DESCRIPTION_LENGTH', 1500))
MIN_PERSONALITY_DESCRIPTION_LENGTH = int(os.getenv('MIN_PERSONALITY_DESCRIPTION_LENGTH', 10))
MAX_CUSTOM_PERSONALITIES_PER_USER = int(os.getenv('MAX_CUSTOM_PERSONALITIES_PER_USER', 5))

# Direct chat settings (Phase 2)
DIRECT_CHAT_CONTEXT_MESSAGES = int(os.getenv('DIRECT_CHAT_CONTEXT_MESSAGES', 30))  # Number of messages in context
DIRECT_CHAT_SESSION_TIMEOUT = int(os.getenv('DIRECT_CHAT_SESSION_TIMEOUT', 900))  # 15 minutes in seconds

# ================================================
# COMMAND NAMES (Latin characters - Telegram API requirement)
# ================================================
COMMAND_SUMMARY = 'summary'
COMMAND_CHAT = 'chat'
COMMAND_JUDGE = 'rassudi'
COMMAND_PERSONALITY = 'lichnost'
COMMAND_START = 'start'
COMMAND_HELP = 'help'
COMMAND_STOP = 'stop'

# ================================================
# VALIDATION
# Ensure all required env variables are set
# ================================================
def validate_config():
    """Validate that all required configuration is present"""
    errors = []

    if not TELEGRAM_BOT_TOKEN:
        errors.append("TELEGRAM_BOT_TOKEN не установлен!")

    if not ANTHROPIC_API_KEY:
        errors.append("ANTHROPIC_API_KEY не установлен!")

    if not SUPABASE_URL:
        errors.append("SUPABASE_URL не установлен!")

    if not SUPABASE_KEY:
        errors.append("SUPABASE_KEY не установлен!")

    if errors:
        raise ValueError("\n".join(errors))

# Validate on import
try:
    validate_config()
except ValueError as e:
    # In development, just warn. In production, this should fail hard.
    print(f"⚠️  WARNING: Configuration validation failed:\n{e}")
    print("Please set required environment variables in .env file")

# ================================================
# LOGGING CONFIGURATION
# ================================================
import logging

LOG_LEVEL = os.getenv('LOG_LEVEL', 'WARNING')  # Only warnings and errors by default

# Verbose logging (checkpoint logs) - disabled in production
# Set to 'true' in environment to enable detailed checkpoint logging
VERBOSE_LOGGING = os.getenv('VERBOSE_LOGGING', 'false').lower() == 'true'

def setup_logging():
    """Setup logging configuration"""
    logging.basicConfig(
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        level=getattr(logging, LOG_LEVEL.upper(), logging.WARNING)
    )

    # Disable noisy loggers from external libraries
    logging.getLogger('httpx').setLevel(logging.WARNING)
    logging.getLogger('httpcore').setLevel(logging.WARNING)
    logging.getLogger('telegram').setLevel(logging.WARNING)
    logging.getLogger('telegram.ext').setLevel(logging.WARNING)

    return logging.getLogger(__name__)

logger = setup_logging()
