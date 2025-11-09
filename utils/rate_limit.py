"""
Rate limiting
Prevents abuse by limiting requests per user
"""

from collections import defaultdict
from time import time
from typing import Tuple
import config
from config import logger

# In-memory request history
# Format: {user_id: [timestamp1, timestamp2, ...]}
REQUEST_HISTORY = defaultdict(list)


def check_rate_limit(user_id: int) -> Tuple[bool, int]:
    """
    Check if user is within rate limit

    Args:
        user_id: User ID

    Returns:
        Tuple of (is_allowed, remaining_requests_or_wait_time)
    """
    now = time()

    # Clean up old requests outside the window
    REQUEST_HISTORY[user_id] = [
        ts for ts in REQUEST_HISTORY[user_id]
        if now - ts < config.RATE_LIMIT_WINDOW
    ]

    count = len(REQUEST_HISTORY[user_id])

    if count >= config.RATE_LIMIT_REQUESTS:
        # Rate limit exceeded
        oldest = REQUEST_HISTORY[user_id][0]
        wait_time = int(config.RATE_LIMIT_WINDOW - (now - oldest))
        logger.warning(f"Rate limit exceeded for user {user_id}")
        return False, wait_time

    # Record this request
    REQUEST_HISTORY[user_id].append(now)
    remaining = config.RATE_LIMIT_REQUESTS - count - 1

    logger.debug(f"Rate limit check for user {user_id}: {remaining} requests remaining")
    return True, remaining


def clear_rate_limit(user_id: int) -> None:
    """
    Clear rate limit for a user (for testing or admin purposes)

    Args:
        user_id: User ID
    """
    if user_id in REQUEST_HISTORY:
        del REQUEST_HISTORY[user_id]
        logger.info(f"Cleared rate limit for user {user_id}")
