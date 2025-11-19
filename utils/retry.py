"""
Retry decorators for external API calls (ШАГ 9: Security Fix)

Provides automatic retry logic for transient failures in:
- Supabase DB operations (network timeouts, rate limits)
- Claude API calls (429 errors, timeouts)

Prevents data loss from temporary network glitches.
"""

import logging
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type,
    before_sleep_log
)

logger = logging.getLogger(__name__)

# ================================================
# DATABASE RETRY DECORATOR
# ================================================

# Retry для Supabase (3 attempts, exponential backoff)
db_retry = retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=1, max=10),
    retry=retry_if_exception_type((
        # Postgrest/Supabase errors
        Exception,  # Catch-all для всех DB ошибок
        # Можно уточнить когда появятся конкретные типы:
        # PostgrestAPIError,
        # ConnectionError,
        # TimeoutError,
    )),
    before_sleep=before_sleep_log(logger, logging.WARNING),
    reraise=True
)

# ================================================
# AI API RETRY DECORATOR
# ================================================

# Retry для Claude API (2 attempts, longer backoff)
# API calls дороже, поэтому меньше попыток
ai_retry = retry(
    stop=stop_after_attempt(2),
    wait=wait_exponential(multiplier=2, min=2, max=20),
    retry=retry_if_exception_type((
        # Anthropic API errors
        Exception,  # Catch-all для всех AI ошибок
        # Можно уточнить когда появятся конкретные типы:
        # RateLimitError,
        # APIError,
        # TimeoutError,
    )),
    before_sleep=before_sleep_log(logger, logging.WARNING),
    reraise=True
)

# ================================================
# USAGE EXAMPLE
# ================================================
"""
from utils.retry import db_retry, ai_retry

class DBService:
    @db_retry
    def save_message(self, chat_id: int, user_id: int, ...):
        # Automatically retries on transient failures
        self.client.table('messages').insert({...}).execute()

class AIService:
    @ai_retry
    def generate_summary(self, messages: list, ...):
        # Automatically retries on rate limit or timeout
        response = self.client.messages.create(...)
        return response
"""
