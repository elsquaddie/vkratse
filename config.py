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
BOT_USERNAME = os.getenv('BOT_USERNAME', 'chto_bilo_v_chate_bot')

# ================================================
# AI CONFIGURATION (Anthropic Claude)
# ================================================
ANTHROPIC_API_KEY = os.getenv('ANTHROPIC_API_KEY')
ANTHROPIC_MODEL = os.getenv('ANTHROPIC_MODEL', 'claude-3-5-sonnet-20241022')

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

# Message retention
MESSAGE_RETENTION_DAYS = int(os.getenv('MESSAGE_RETENTION_DAYS', 7))

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
MAX_MESSAGES_PER_SUMMARY = int(os.getenv('MAX_MESSAGES_PER_SUMMARY', 500))
DEFAULT_MESSAGE_LIMIT = int(os.getenv('DEFAULT_MESSAGE_LIMIT', 50))

# Custom personality limits
MAX_PERSONALITY_DESCRIPTION_LENGTH = int(os.getenv('MAX_PERSONALITY_DESCRIPTION_LENGTH', 500))
MIN_PERSONALITY_DESCRIPTION_LENGTH = int(os.getenv('MIN_PERSONALITY_DESCRIPTION_LENGTH', 10))

# ================================================
# COMMAND NAMES (updated to Russian)
# ================================================
COMMAND_SUMMARY = 'суть'
COMMAND_JUDGE = 'рассуди'
COMMAND_PERSONALITY = 'личность'
COMMAND_START = 'start'
COMMAND_HELP = 'help'

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
    print("✅ Configuration validated successfully")
except ValueError as e:
    # In production (Vercel), this is critical
    import sys
    print(f"❌ CRITICAL: Configuration validation failed!", file=sys.stderr)
    print(f"Missing environment variables:\n{e}", file=sys.stderr)
    print("\nPlease set these variables in Vercel dashboard:", file=sys.stderr)
    print("  vercel env add TELEGRAM_BOT_TOKEN", file=sys.stderr)
    print("  vercel env add ANTHROPIC_API_KEY", file=sys.stderr)
    print("  vercel env add SUPABASE_URL", file=sys.stderr)
    print("  vercel env add SUPABASE_KEY", file=sys.stderr)

    # Also print to stdout for Vercel logs
    print(f"❌ Configuration error: {e}")

    # Don't raise in production - let it be handled gracefully
    # The get_application() function will catch this

# ================================================
# LOGGING CONFIGURATION
# ================================================
import logging

LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO')

def setup_logging():
    """Setup logging configuration"""
    logging.basicConfig(
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        level=getattr(logging, LOG_LEVEL.upper(), logging.INFO)
    )
    return logging.getLogger(__name__)

logger = setup_logging()
