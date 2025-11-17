"""
Payment service for handling YooKassa payments

This module provides functions for creating payment links and handling payments
through YooKassa (formerly Yandex.Kassa) payment gateway.

Security features:
- API keys stored in environment variables
- Payment verification through webhooks
- Transaction ID logging for audit trail
"""

import logging
import uuid
from datetime import datetime, timedelta
from typing import Optional, Dict, Any

import config

logger = logging.getLogger(__name__)

# ================================================
# YOOKASSA PAYMENT INTEGRATION
# ================================================

class PaymentError(Exception):
    """Custom exception for payment-related errors"""
    pass


def is_yookassa_configured() -> bool:
    """
    Check if YooKassa is properly configured

    Returns:
        bool: True if SHOP_ID and SECRET_KEY are set
    """
    return bool(config.YOOKASSA_SHOP_ID and config.YOOKASSA_SECRET_KEY)


async def create_payment_link(
    user_id: int,
    tier: str = 'pro',
    duration_days: int = 30,
    amount_usd: float = 2.99
) -> Dict[str, Any]:
    """
    Create a payment link through YooKassa

    Args:
        user_id: Telegram user ID
        tier: Subscription tier ('pro')
        duration_days: Duration of subscription in days
        amount_usd: Payment amount in USD

    Returns:
        dict: {
            'payment_url': str,        # URL for payment
            'payment_id': str,         # YooKassa payment ID
            'amount': float,           # Payment amount
            'currency': str,           # Currency code
            'expires_at': datetime     # Payment link expiration
        }

    Raises:
        PaymentError: If YooKassa is not configured or API error occurs

    Security:
        - Unique payment ID (UUID) for each transaction
        - Metadata includes user_id for verification
        - Payment link expires in 1 hour
        - Return URL redirects to bot
    """
    # Check configuration
    if not is_yookassa_configured():
        logger.error("YooKassa is not configured")
        raise PaymentError(
            "Оплата временно недоступна. Попробуйте другой способ оплаты."
        )

    try:
        # Lazy import to avoid issues if yookassa is not installed
        from yookassa import Payment, Configuration

        # Configure YooKassa
        Configuration.account_id = config.YOOKASSA_SHOP_ID
        Configuration.secret_key = config.YOOKASSA_SECRET_KEY

        # Generate unique payment ID
        payment_id = str(uuid.uuid4())

        # Calculate expiration (1 hour from now)
        expires_at = datetime.now() + timedelta(hours=1)

        # Create payment
        logger.info(f"Creating payment for user {user_id}: tier={tier}, amount=${amount_usd}")

        payment = Payment.create({
            "amount": {
                "value": f"{amount_usd:.2f}",
                "currency": "USD"
            },
            "confirmation": {
                "type": "redirect",
                "return_url": f"https://t.me/{config.BOT_USERNAME}"
            },
            "capture": True,  # Auto-capture payment
            "description": f"Pro подписка на {duration_days} дней",
            "metadata": {
                "user_id": str(user_id),
                "tier": tier,
                "duration_days": str(duration_days),
                "created_at": datetime.now().isoformat()
            },
            # Payment expiration
            "expires_at": expires_at.isoformat()
        }, payment_id)

        # Extract confirmation URL
        payment_url = payment.confirmation.confirmation_url

        logger.info(
            f"Payment created successfully: "
            f"payment_id={payment.id}, user_id={user_id}, amount=${amount_usd}"
        )

        return {
            'payment_url': payment_url,
            'payment_id': payment.id,
            'amount': amount_usd,
            'currency': 'USD',
            'expires_at': expires_at
        }

    except ImportError as e:
        logger.error(f"YooKassa library not installed: {e}")
        raise PaymentError(
            "Ошибка конфигурации платежной системы. Обратитесь в поддержку."
        )
    except Exception as e:
        logger.error(f"Error creating payment: {e}")
        raise PaymentError(
            "Не удалось создать платеж. Попробуйте позже или используйте другой способ оплаты."
        )


async def verify_payment(payment_id: str) -> Optional[Dict[str, Any]]:
    """
    Verify payment status through YooKassa API

    Args:
        payment_id: YooKassa payment ID

    Returns:
        dict or None: Payment data if successful, None otherwise
        {
            'user_id': int,
            'tier': str,
            'duration_days': int,
            'amount': float,
            'status': str
        }

    Security:
        - Validates payment status (must be 'succeeded')
        - Extracts user_id from metadata for verification
        - Logs all verification attempts
    """
    if not is_yookassa_configured():
        logger.error("YooKassa is not configured")
        return None

    try:
        from yookassa import Payment, Configuration

        Configuration.account_id = config.YOOKASSA_SHOP_ID
        Configuration.secret_key = config.YOOKASSA_SECRET_KEY

        # Get payment details
        payment = Payment.find_one(payment_id)

        if not payment:
            logger.warning(f"Payment not found: {payment_id}")
            return None

        # Check payment status
        if payment.status != 'succeeded':
            logger.info(f"Payment {payment_id} status: {payment.status}")
            return None

        # Extract metadata
        metadata = payment.metadata
        user_id = int(metadata.get('user_id', 0))
        tier = metadata.get('tier', 'pro')
        duration_days = int(metadata.get('duration_days', 30))
        amount = float(payment.amount.value)

        logger.info(
            f"Payment verified: payment_id={payment_id}, "
            f"user_id={user_id}, tier={tier}, amount=${amount}"
        )

        return {
            'user_id': user_id,
            'tier': tier,
            'duration_days': duration_days,
            'amount': amount,
            'status': payment.status,
            'payment_id': payment_id
        }

    except Exception as e:
        logger.error(f"Error verifying payment {payment_id}: {e}")
        return None


# ================================================
# PRICING CONFIGURATION
# ================================================

PRICING = {
    'pro_monthly': {
        'tier': 'pro',
        'duration_days': 30,
        'amount_usd': 2.99,
        'name': 'Pro (1 месяц)',
        'description': 'Безлимитные личности, до 500 сообщений/день, приоритетная обработка'
    },
    'pro_quarterly': {
        'tier': 'pro',
        'duration_days': 90,
        'amount_usd': 7.99,  # ~$2.66/month
        'name': 'Pro (3 месяца)',
        'description': 'Скидка 10%! Все возможности Pro на 3 месяца'
    },
    'pro_yearly': {
        'tier': 'pro',
        'duration_days': 365,
        'amount_usd': 29.99,  # ~$2.50/month
        'name': 'Pro (1 год)',
        'description': 'Скидка 16%! Все возможности Pro на целый год'
    }
}


def get_pricing_info(plan: str = 'pro_monthly') -> Dict[str, Any]:
    """
    Get pricing information for a specific plan

    Args:
        plan: Plan identifier ('pro_monthly', 'pro_quarterly', 'pro_yearly')

    Returns:
        dict: Pricing information
    """
    return PRICING.get(plan, PRICING['pro_monthly'])
