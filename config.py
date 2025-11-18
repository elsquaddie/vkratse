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
SECRET_KEY = os.getenv('SECRET_KEY')
if not SECRET_KEY:
    raise ValueError(
        "❌ SECRET_KEY environment variable is required!\n"
        "Generate: python -c 'import secrets; print(secrets.token_hex(32))'\n"
        "Set in Vercel: Settings → Environment Variables → Add SECRET_KEY"
    )

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
# MONETIZATION SETTINGS (v2.1)
# ================================================

# Project Telegram group ID (for group bonus)
PROJECT_TELEGRAM_GROUP_ID = int(os.getenv('PROJECT_TELEGRAM_GROUP_ID', '0'))

# Project Telegram group link/username (for invitations)
PROJECT_GROUP_LINK = os.getenv('PROJECT_GROUP_LINK', 'https://t.me/choovakee')

# Tier limits configuration
TIER_LIMITS = {
    'free': {
        'messages_dm': 30,              # Direct messages per day
        'summaries_dm': 3,              # DM summaries per day
        'summaries_group': 3,           # Group summaries per day
        'judge': 2,                     # Judge requests per day
        'personality_summary': 5,       # Non-neutral personality uses for summary
        'personality_chat': 5,          # Non-neutral personality uses for chat
        'personality_judge': 5,         # Non-neutral personality uses for judge
        'custom_personalities': 0,      # Custom personalities (0 for free, 1 with group)
        'context_messages': 30,         # Context window size
        'cooldown_seconds': 60          # Cooldown between actions
    },
    'pro': {
        'messages_dm': 500,             # Direct messages per day
        'summaries_dm': 10,             # DM summaries per day
        'summaries_group': 20,          # Group summaries per day
        'judge': 20,                    # Judge requests per day
        # Pro users have unlimited personality usage (no personality_* limits)
        'custom_personalities': 3,      # Custom personalities (4 with group)
        'context_messages': 50,         # Context window size
        'cooldown_seconds': 30          # Cooldown between actions
    }
}

# Payment settings
TRIBUTE_URL = os.getenv('TRIBUTE_URL', 'https://tribute.to/your_bot_page')
ADMIN_USER_ID = int(os.getenv('ADMIN_USER_ID', '0'))  # Admin Telegram ID for manual operations

# YooKassa settings (optional, for automated payments)
YOOKASSA_SHOP_ID = os.getenv('YOOKASSA_SHOP_ID', '')
YOOKASSA_SECRET_KEY = os.getenv('YOOKASSA_SECRET_KEY', '')

# Payment DRY RUN mode (for testing payments without real money)
# When enabled, all payment flows will automatically succeed and grant subscription
# Set to 'true' to enable testing mode, 'false' for production
PAYMENT_DRY_RUN = os.getenv('PAYMENT_DRY_RUN', 'false').lower() == 'true'

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

    # SECURITY: Check SECRET_KEY strength
    if SECRET_KEY and len(SECRET_KEY) < 32:
        errors.append(
            "SECRET_KEY must be at least 32 characters long!\n"
            "Generate: python -c 'import secrets; print(secrets.token_hex(32))'"
        )

    # Check for weak/default SECRET_KEY values
    if SECRET_KEY:
        forbidden_values = [
            'your-secret-key-change-in-production',
            'default_secret_CHANGE_ME_in_production',
            'secret',
            'password',
            '12345',
            'changeme',
        ]
        if SECRET_KEY.lower() in [v.lower() for v in forbidden_values]:
            errors.append(
                "SECRET_KEY is using a default/weak value! Generate a strong key:\n"
                "python -c 'import secrets; print(secrets.token_hex(32))'"
            )

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
# DEBUG SETTINGS
# ================================================
# SECURITY: Debug mode enables detailed logging including sensitive data
# WARNING: NEVER enable DEBUG_MODE in production!
DEBUG_MODE = os.getenv('DEBUG_MODE', 'false').lower() == 'true'

# Environment detection
ENV = os.getenv('ENV', 'development')  # 'production' or 'development'

# Warn if DEBUG_MODE is enabled in production
if DEBUG_MODE and ENV == 'production':
    import logging
    logging.warning("⚠️ DEBUG_MODE is enabled in production! Secrets may be logged!")

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
