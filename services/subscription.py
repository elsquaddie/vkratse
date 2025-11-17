"""
Subscription Service
Handles user tier management, limits checking, and group bonuses
"""

from datetime import datetime, date, timezone, timedelta
from typing import Dict, Optional
from telegram import Bot
from telegram.error import TelegramError

import config
from config import logger


class SubscriptionService:
    """Service for managing user subscriptions and limits"""

    def __init__(self, db_service):
        """
        Initialize subscription service

        Args:
            db_service: Database service instance
        """
        self.db = db_service

    # ================================================
    # TIER MANAGEMENT
    # ================================================

    async def get_user_tier(self, user_id: int) -> str:
        """
        Get user's subscription tier

        Args:
            user_id: Telegram user ID

        Returns:
            'free' or 'pro'

        IMPORTANT: Automatically checks and downgrades expired subscriptions
        """
        try:
            subscription = await self.db.get_subscription(user_id)

            if not subscription or not subscription.get('is_active'):
                return 'free'

            # CRITICAL: Check subscription expiration
            expires_at = subscription.get('expires_at')
            if expires_at:
                # Parse ISO string to datetime
                if isinstance(expires_at, str):
                    expires_at = datetime.fromisoformat(expires_at.replace('Z', '+00:00'))

                # Check if expired
                if expires_at < datetime.now(timezone.utc):
                    logger.info(f"Subscription expired for user {user_id}")
                    await self.auto_downgrade_expired_subscription(user_id)
                    return 'free'

            return subscription.get('tier', 'free')

        except Exception as e:
            logger.error(f"Error getting user tier for {user_id}: {e}")
            return 'free'  # Default to free on error

    async def auto_downgrade_expired_subscription(self, user_id: int) -> None:
        """
        Automatically downgrade user to Free tier when subscription expires

        Args:
            user_id: Telegram user ID
        """
        try:
            # Deactivate subscription
            await self.db.deactivate_subscription(user_id)

            # Block excess custom personalities (Pro->Free: keep 0, block all)
            await self.db.block_excess_custom_personalities(user_id, limit=0)

            logger.info(f"User {user_id} downgraded to Free (subscription expired)")

            # TODO: Send notification to user (requires bot instance)
            # Will be implemented when integrating with handlers

        except Exception as e:
            logger.error(f"Error downgrading subscription for {user_id}: {e}")

    # ================================================
    # USAGE LIMITS
    # ================================================

    async def check_usage_limit(
        self,
        user_id: int,
        action: str
    ) -> Dict[str, any]:
        """
        Check if user has exceeded their usage limit for an action

        Args:
            user_id: Telegram user ID
            action: Action type - 'message_dm', 'summary_dm', 'summary_group', 'judge'

        Returns:
            {
                'can_proceed': bool,
                'current': int,
                'limit': int,
                'tier': str
            }
        """
        try:
            tier = await self.get_user_tier(user_id)
            limits = config.TIER_LIMITS[tier]

            # Get action limit
            limit = limits.get(action, 0)
            if limit == 0:
                # No limit defined for this action
                return {
                    'can_proceed': True,
                    'current': 0,
                    'limit': -1,  # -1 means unlimited
                    'tier': tier
                }

            # Get current usage for today
            usage = await self.db.get_usage_limits(user_id, date.today())

            # Map action to usage field
            action_field_map = {
                'message_dm': 'messages_count',
                'summary_dm': 'summaries_dm_count',
                'summary_group': 'summaries_count',
                'judge': 'judge_count'
            }

            field_name = action_field_map.get(action, 'messages_count')
            current = usage.get(field_name, 0) if usage else 0

            return {
                'can_proceed': current < limit,
                'current': current,
                'limit': limit,
                'tier': tier
            }

        except Exception as e:
            logger.error(f"Error checking usage limit for {user_id}, action {action}: {e}")
            # On error, allow proceeding to avoid blocking users
            return {
                'can_proceed': True,
                'current': 0,
                'limit': -1,
                'tier': 'free'
            }

    async def increment_usage(self, user_id: int, action: str) -> None:
        """
        Increment usage counter for an action

        Args:
            user_id: Telegram user ID
            action: Action type - 'message_dm', 'summary_dm', 'summary_group', 'judge'
        """
        try:
            await self.db.increment_usage_limit(user_id, action)
        except Exception as e:
            logger.error(f"Error incrementing usage for {user_id}, action {action}: {e}")

    # ================================================
    # PERSONALITY LIMITS
    # ================================================

    async def check_personality_limit(
        self,
        user_id: int,
        personality: str,
        action: str
    ) -> Dict[str, any]:
        """
        Check if user can use a specific personality

        Args:
            user_id: Telegram user ID
            personality: Personality name (e.g., 'bydlan')
            action: Action type - 'summary', 'chat', 'judge'

        Returns:
            {
                'can_proceed': bool,
                'current': int,
                'limit': int,
                'tier': str
            }

        IMPORTANT: Pro users have unlimited personality usage
        """
        try:
            tier = await self.get_user_tier(user_id)

            # Pro users: unlimited personality usage
            if tier == 'pro':
                return {
                    'can_proceed': True,
                    'current': 0,
                    'limit': -1,  # -1 means unlimited
                    'tier': 'pro'
                }

            # Neutral personality: always available for free users
            if personality == 'neutral':
                return {
                    'can_proceed': True,
                    'current': 0,
                    'limit': -1,
                    'tier': 'free'
                }

            # Free users: check personality usage limit
            usage = await self.db.get_personality_usage(user_id, personality, date.today())
            limits = config.TIER_LIMITS['free']

            action_key = f'personality_{action}'  # 'personality_summary', 'personality_chat', etc.
            limit = limits.get(action_key, 5)

            action_field_map = {
                'summary': 'summary_count',
                'chat': 'chat_count',
                'judge': 'judge_count'
            }

            field_name = action_field_map.get(action, 'summary_count')
            current = usage.get(field_name, 0) if usage else 0

            return {
                'can_proceed': current < limit,
                'current': current,
                'limit': limit,
                'tier': 'free'
            }

        except Exception as e:
            logger.error(f"Error checking personality limit for {user_id}, {personality}, {action}: {e}")
            # On error, allow neutral personality only
            return {
                'can_proceed': personality == 'neutral',
                'current': 0,
                'limit': 5,
                'tier': 'free'
            }

    async def increment_personality_usage(
        self,
        user_id: int,
        personality: str,
        action: str
    ) -> None:
        """
        Increment personality usage counter

        Args:
            user_id: Telegram user ID
            personality: Personality name
            action: Action type - 'summary', 'chat', 'judge'
        """
        try:
            # Only increment for non-neutral personalities and free users
            if personality == 'neutral':
                return

            tier = await self.get_user_tier(user_id)
            if tier == 'pro':
                # Pro users don't have limits, no need to track
                return

            await self.db.increment_personality_usage(user_id, personality, action)

        except Exception as e:
            logger.error(f"Error incrementing personality usage for {user_id}, {personality}, {action}: {e}")

    # ================================================
    # GROUP MEMBERSHIP BONUS
    # ================================================

    async def is_in_project_group(
        self,
        user_id: int,
        bot: Bot,
        force_check: bool = False
    ) -> bool:
        """
        Check if user is a member of the project group

        Args:
            user_id: Telegram user ID
            bot: Telegram Bot instance
            force_check: Force API check (ignore cache)

        Returns:
            True if user is in the group
        """
        if not config.PROJECT_TELEGRAM_GROUP_ID:
            return False

        try:
            # Check cache first (unless force_check)
            if not force_check:
                cache = await self.db.get_group_membership_cache(user_id)
                if cache:
                    checked_at = cache.get('checked_at')
                    if isinstance(checked_at, str):
                        checked_at = datetime.fromisoformat(checked_at.replace('Z', '+00:00'))

                    # Cache valid for 1 hour
                    if (datetime.now(timezone.utc) - checked_at).seconds < 3600:
                        return cache.get('is_member', False)

            # Check via Telegram API
            member = await bot.get_chat_member(
                chat_id=config.PROJECT_TELEGRAM_GROUP_ID,
                user_id=user_id
            )
            is_member = member.status in ['member', 'administrator', 'creator']

            # Update cache
            await self.db.update_group_membership_cache(user_id, is_member)

            return is_member

        except TelegramError as e:
            logger.warning(f"Could not check group membership for {user_id}: {e}")
            return False
        except Exception as e:
            logger.error(f"Error checking group membership for {user_id}: {e}")
            return False

    async def get_custom_personality_limit(
        self,
        user_id: int,
        bot: Bot
    ) -> int:
        """
        Get the limit of custom personalities for a user

        Returns:
            Number of allowed custom personalities

        Logic:
            Free: 0
            Free + Group: 1
            Pro: 3
            Pro + Group: 4
        """
        try:
            tier = await self.get_user_tier(user_id)
            in_group = await self.is_in_project_group(user_id, bot)

            if tier == 'pro':
                return 4 if in_group else 3
            else:  # free
                return 1 if in_group else 0

        except Exception as e:
            logger.error(f"Error getting custom personality limit for {user_id}: {e}")
            return 0

    async def can_create_custom_personality(
        self,
        user_id: int,
        bot: Bot
    ) -> Dict[str, any]:
        """
        Check if user can create a custom personality

        Returns:
            {
                'can_create': bool,
                'reason': str,
                'current': int,
                'limit': int,
                'needs_group': bool,
                'needs_pro': bool
            }
        """
        try:
            tier = await self.get_user_tier(user_id)
            in_group = await self.is_in_project_group(user_id, bot)
            limit = await self.get_custom_personality_limit(user_id, bot)
            current = await self.db.get_active_custom_personalities_count(user_id)

            # Can create if current < limit
            if current < limit:
                return {
                    'can_create': True,
                    'reason': 'ok',
                    'current': current,
                    'limit': limit,
                    'needs_group': False,
                    'needs_pro': False
                }

            # Determine what user needs
            if tier == 'free' and not in_group:
                return {
                    'can_create': False,
                    'reason': 'need_group_or_pro',
                    'current': current,
                    'limit': limit,
                    'needs_group': True,
                    'needs_pro': True
                }
            elif tier == 'free' and in_group:
                return {
                    'can_create': False,
                    'reason': 'need_pro',
                    'current': current,
                    'limit': limit,
                    'needs_group': False,
                    'needs_pro': True
                }
            elif tier == 'pro' and not in_group:
                return {
                    'can_create': False,
                    'reason': 'need_group',
                    'current': current,
                    'limit': limit,
                    'needs_group': True,
                    'needs_pro': False
                }
            else:  # pro + group
                return {
                    'can_create': False,
                    'reason': 'max_reached',
                    'current': current,
                    'limit': limit,
                    'needs_group': False,
                    'needs_pro': False
                }

        except Exception as e:
            logger.error(f"Error checking custom personality creation for {user_id}: {e}")
            return {
                'can_create': False,
                'reason': 'error',
                'current': 0,
                'limit': 0,
                'needs_group': False,
                'needs_pro': False
            }

    async def handle_group_membership_change(
        self,
        user_id: int,
        is_member: bool,
        bot: Bot
    ) -> None:
        """
        Handle user joining or leaving the project group

        Args:
            user_id: Telegram user ID
            is_member: True if user joined, False if left
            bot: Telegram Bot instance
        """
        try:
            # Update cache
            await self.db.update_group_membership_cache(user_id, is_member)
            logger.info(f"Group membership changed for user {user_id}: is_member={is_member}")

            if not is_member:
                # User left the group - block bonus personalities
                await self.db.block_group_bonus_personalities(user_id)
                logger.info(f"Blocked bonus personalities for user {user_id}")

                # Notify user
                try:
                    await bot.send_message(
                        chat_id=user_id,
                        text=(
                            "⚠️ Ты вышел из группы проекта.\n\n"
                            "Твоя бонусная кастомная личность временно заблокирована.\n"
                            "Вернись в группу, чтобы разблокировать её!"
                        )
                    )
                except TelegramError as e:
                    logger.warning(f"Could not notify user {user_id} about blocking: {e}")

            else:
                # User joined the group - unblock bonus personalities
                await self.db.unblock_group_bonus_personalities(user_id)
                logger.info(f"Unblocked bonus personalities for user {user_id}")

                # Notify user
                try:
                    await bot.send_message(
                        chat_id=user_id,
                        text=(
                            "🎉 Добро пожаловать в группу проекта!\n\n"
                            "Теперь ты можешь создать 1 бонусную кастомную личность.\n"
                            "Используй команду /lichnost для создания."
                        )
                    )
                except TelegramError as e:
                    logger.warning(f"Could not notify user {user_id} about unblocking: {e}")

        except Exception as e:
            logger.error(f"Error handling group membership change for {user_id}: {e}")

    # ================================================
    # ADMIN OPERATIONS
    # ================================================

    async def create_or_update_subscription(
        self,
        user_id: int,
        tier: str,
        duration_days: int,
        payment_method: str = 'manual',
        transaction_id: Optional[str] = None
    ) -> bool:
        """
        Create or update user subscription (admin operation)

        Args:
            user_id: Telegram user ID
            tier: 'free' or 'pro'
            duration_days: Number of days for subscription
            payment_method: 'manual', 'tribute', 'yookassa', 'telegram_stars'
            transaction_id: Optional transaction ID

        Returns:
            True if successful
        """
        try:
            return await self.db.create_or_update_subscription(
                user_id=user_id,
                tier=tier,
                duration_days=duration_days,
                payment_method=payment_method,
                transaction_id=transaction_id
            )
        except Exception as e:
            logger.error(f"Error creating/updating subscription for {user_id}: {e}")
            return False


# ================================================
# SINGLETON INSTANCE
# ================================================

# This will be initialized in handlers after db_service is created
_subscription_service: Optional[SubscriptionService] = None


def init_subscription_service(db_service):
    """Initialize subscription service with db_service"""
    global _subscription_service
    _subscription_service = SubscriptionService(db_service)
    return _subscription_service


def get_subscription_service() -> SubscriptionService:
    """Get subscription service instance"""
    if _subscription_service is None:
        raise RuntimeError("Subscription service not initialized. Call init_subscription_service() first.")
    return _subscription_service
