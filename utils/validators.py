"""
Validation utilities
Chat access validation and data validation
"""

import re
from typing import Tuple, List
from telegram import Bot
from config import logger


async def validate_chat_access(
    bot: Bot,
    chat_id: int,
    user_id: int
) -> Tuple[bool, str]:
    """
    Validate that both bot and user have access to a chat

    Args:
        bot: Telegram bot instance
        chat_id: Chat ID to validate
        user_id: User ID to validate

    Returns:
        Tuple of (is_valid, error_message)
    """
    # 1. Check if bot is in the chat
    try:
        bot_member = await bot.get_chat_member(chat_id, bot.id)
        if bot_member.status not in ['member', 'administrator']:
            return False, "⚠️ Бот больше не в этом чате"
    except Exception as e:
        logger.error(f"Error checking bot membership: {e}")
        return False, "⚠️ Чат не найден"

    # 2. Check if user is in the chat
    try:
        user_member = await bot.get_chat_member(chat_id, user_id)
        if user_member.status not in ['member', 'administrator', 'creator']:
            return False, "⚠️ Ты больше не в этом чате"
    except Exception as e:
        logger.error(f"Error checking user membership: {e}")
        return False, "⚠️ Доступ запрещён"

    return True, ""


def extract_mentions(text: str) -> List[str]:
    """
    Extract @username mentions from text

    Args:
        text: Text to extract mentions from

    Returns:
        List of usernames (without @)
    """
    # Pattern: @username (letters, digits, underscores)
    pattern = r'@([a-zA-Z0-9_]+)'
    matches = re.findall(pattern, text)

    logger.debug(f"Extracted {len(matches)} mentions from text")
    return matches


def is_valid_personality_name(name: str) -> Tuple[bool, str]:
    """
    Validate custom personality name

    Args:
        name: Personality name

    Returns:
        Tuple of (is_valid, error_message)
    """
    # Must be alphanumeric (or cyrillic) and underscores
    if not re.match(r'^[a-zA-Zа-яА-Я0-9_]+$', name):
        return False, "Имя может содержать только буквы, цифры и подчёркивания"

    # Length limits
    if len(name) < 3:
        return False, "Имя должно быть минимум 3 символа"

    if len(name) > 50:
        return False, "Имя должно быть максимум 50 символов"

    # Reserved names
    reserved = ['admin', 'bot', 'system', 'помощь', 'help']
    if name.lower() in reserved:
        return False, f"Имя '{name}' зарезервировано"

    return True, ""
