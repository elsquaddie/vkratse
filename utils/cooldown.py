"""
Cooldown management
Prevents spam by limiting command frequency per chat
"""

import time
from typing import Tuple
import config
from config import logger

# In-memory cooldown storage
# Format: {action: {chat_id: timestamp}}
COOLDOWNS = {
    'summary': {},
    'judge': {}
}


def check_cooldown(chat_id: int, action: str) -> Tuple[bool, int]:
    """
    Check if action is on cooldown for a chat

    Args:
        chat_id: Chat ID
        action: Action type ('summary' or 'judge')

    Returns:
        Tuple of (is_allowed, remaining_seconds)
    """
    if action not in COOLDOWNS:
        logger.warning(f"Unknown cooldown action: {action}")
        return True, 0

    last_time = COOLDOWNS[action].get(chat_id, 0)
    elapsed = time.time() - last_time

    if elapsed < config.COOLDOWN_SECONDS:
        remaining = int(config.COOLDOWN_SECONDS - elapsed)
        logger.debug(f"Cooldown active for {action} in chat {chat_id}: {remaining}s remaining")
        return False, remaining

    return True, 0


def set_cooldown(chat_id: int, action: str) -> None:
    """
    Set cooldown for an action in a chat

    Args:
        chat_id: Chat ID
        action: Action type ('summary' or 'judge')
    """
    if action not in COOLDOWNS:
        logger.warning(f"Unknown cooldown action: {action}")
        return

    COOLDOWNS[action][chat_id] = time.time()
    logger.debug(f"Set cooldown for {action} in chat {chat_id}")


def clear_cooldown(chat_id: int, action: str) -> None:
    """
    Clear cooldown for an action (for testing or admin purposes)

    Args:
        chat_id: Chat ID
        action: Action type
    """
    if action in COOLDOWNS and chat_id in COOLDOWNS[action]:
        del COOLDOWNS[action][chat_id]
        logger.info(f"Cleared cooldown for {action} in chat {chat_id}")
