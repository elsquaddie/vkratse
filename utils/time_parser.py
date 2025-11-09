"""
Time argument parser
Parse time arguments like "30m", "2h", "today", etc.
"""

from datetime import datetime, timedelta, timezone
from typing import Optional, Tuple
from config import logger


def parse_time_argument(arg: str) -> Tuple[Optional[datetime], str]:
    """
    Parse time argument into datetime and description

    Formats:
    - 30m → 30 minutes ago
    - 2h → 2 hours ago
    - today → start of today
    - Number → interpreted as hours (backward compatibility)

    Args:
        arg: Time argument string

    Returns:
        Tuple of (datetime_since, description)
        Returns (None, description) if invalid
    """
    arg = arg.lower().strip()

    # Minutes (e.g., "30m")
    if arg.endswith('м') or arg.endswith('m'):
        try:
            minutes = int(arg[:-1])
            if minutes <= 0 or minutes > 1440:  # Max 24 hours
                return None, "неверный формат"

            since = datetime.now(timezone.utc) - timedelta(minutes=minutes)
            description = f"за последние {minutes} минут" if arg.endswith('м') else f"за последние {minutes}м"
            logger.debug(f"Parsed time: {minutes} minutes ago")
            return since, description
        except ValueError:
            return None, "неверный формат минут"

    # Hours (e.g., "2h" or "2ч")
    if arg.endswith('ч') or arg.endswith('h'):
        try:
            hours = int(arg[:-1])
            if hours <= 0 or hours > 168:  # Max 7 days
                return None, "неверный формат"

            since = datetime.now(timezone.utc) - timedelta(hours=hours)
            description = f"за последние {hours} часов" if arg.endswith('ч') else f"за последние {hours}ч"
            logger.debug(f"Parsed time: {hours} hours ago")
            return since, description
        except ValueError:
            return None, "неверный формат часов"

    # Days (e.g., "2d" or "2д")
    if arg.endswith('д') or arg.endswith('d'):
        try:
            days = int(arg[:-1])
            if days <= 0 or days > 7:  # Max 7 days
                return None, "максимум 7 дней"

            since = datetime.now(timezone.utc) - timedelta(days=days)
            description = f"за последние {days} дней" if arg.endswith('д') else f"за последние {days}д"
            logger.debug(f"Parsed time: {days} days ago")
            return since, description
        except ValueError:
            return None, "неверный формат дней"

    # Today
    if arg in ['today', 'сегодня']:
        since = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
        description = "с начала дня"
        logger.debug("Parsed time: today")
        return since, description

    # Yesterday
    if arg in ['yesterday', 'вчера']:
        yesterday = datetime.now(timezone.utc) - timedelta(days=1)
        since = yesterday.replace(hour=0, minute=0, second=0, microsecond=0)
        description = "за вчера"
        logger.debug("Parsed time: yesterday")
        return since, description

    # Pure number - interpret as hours for backward compatibility
    if arg.isdigit():
        hours = int(arg)
        if hours <= 0 or hours > 168:
            return None, "неверный формат"

        since = datetime.now(timezone.utc) - timedelta(hours=hours)
        description = f"за последние {hours} часов"
        logger.debug(f"Parsed time: {hours} hours ago (from number)")
        return since, description

    # Unknown format
    return None, "неверный формат времени"


def get_default_period() -> Tuple[datetime, str]:
    """
    Get default time period (24 hours)

    Returns:
        Tuple of (datetime_since, description)
    """
    since = datetime.now(timezone.utc) - timedelta(hours=24)
    description = "за последние 24 часа"
    return since, description
