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


# ================================================
# TELEGRAM STARS PAYMENT INTEGRATION
# ================================================

# Telegram Stars pricing (approximate conversion: 1 Star ≈ $0.01)
STARS_PRICING = {
    'pro_monthly': {
        'tier': 'pro',
        'duration_days': 30,
        'stars_amount': 300,  # ~$3.00
        'name': 'Pro (1 месяц)',
        'description': 'Безлимитные личности, до 500 сообщений/день, приоритетная обработка'
    },
    'pro_quarterly': {
        'tier': 'pro',
        'duration_days': 90,
        'stars_amount': 800,  # ~$8.00, скидка 11%
        'name': 'Pro (3 месяца)',
        'description': 'Скидка 11%! Все возможности Pro на 3 месяца'
    },
    'pro_yearly': {
        'tier': 'pro',
        'duration_days': 365,
        'stars_amount': 3000,  # ~$30.00, скидка 17%
        'name': 'Pro (1 год)',
        'description': 'Скидка 17%! Все возможности Pro на целый год'
    }
}


def get_stars_pricing_info(plan: str = 'pro_monthly') -> Dict[str, Any]:
    """
    Get Stars pricing information for a specific plan

    Args:
        plan: Plan identifier ('pro_monthly', 'pro_quarterly', 'pro_yearly')

    Returns:
        dict: Stars pricing information
    """
    return STARS_PRICING.get(plan, STARS_PRICING['pro_monthly'])


async def create_stars_invoice(
    bot,  # Telegram Bot instance
    user_id: int,
    plan: str = 'pro_monthly'
) -> Dict[str, Any]:
    """
    Create an invoice for payment through Telegram Stars

    Args:
        bot: Telegram Bot instance
        user_id: Telegram user ID
        plan: Plan identifier ('pro_monthly', 'pro_quarterly', 'pro_yearly')

    Returns:
        dict: {
            'success': bool,
            'invoice_message': Message,  # Sent invoice message
            'plan': str,
            'stars_amount': int,
            'tier': str,
            'duration_days': int
        }

    Security:
        - Payload contains user_id and timestamp for verification
        - No external API keys required (native Telegram feature)
        - Payment automatically verified by Telegram

    Example:
        result = await create_stars_invoice(bot, user_id, 'pro_monthly')
        if result['success']:
            # Invoice sent successfully
            pass
    """
    try:
        # Get pricing info
        pricing = get_stars_pricing_info(plan)

        if not pricing:
            logger.error(f"Invalid plan: {plan}")
            raise PaymentError("Неверный тарифный план")

        # Prepare invoice data
        title = pricing['name']
        description = pricing['description']
        stars_amount = pricing['stars_amount']
        tier = pricing['tier']
        duration_days = pricing['duration_days']

        # Generate unique payload for verification
        # Format: "stars_<user_id>_<tier>_<days>_<timestamp>"
        timestamp = int(datetime.now().timestamp())
        payload = f"stars_{user_id}_{tier}_{duration_days}_{timestamp}"

        # Currency for Telegram Stars
        currency = "XTR"

        # Create price list
        prices = [{"label": title, "amount": stars_amount}]

        logger.info(
            f"Creating Stars invoice: user={user_id}, plan={plan}, "
            f"stars={stars_amount}, duration={duration_days} days"
        )

        # Send invoice to user
        # ВАЖНО: provider_token должен быть пустой строкой для Stars
        invoice_message = await bot.send_invoice(
            chat_id=user_id,
            title=title,
            description=description,
            payload=payload,
            provider_token="",  # Empty for Telegram Stars
            currency=currency,
            prices=prices
        )

        logger.info(
            f"Stars invoice sent successfully: "
            f"user={user_id}, plan={plan}, message_id={invoice_message.message_id}"
        )

        return {
            'success': True,
            'invoice_message': invoice_message,
            'plan': plan,
            'stars_amount': stars_amount,
            'tier': tier,
            'duration_days': duration_days,
            'payload': payload
        }

    except Exception as e:
        logger.error(f"Error creating Stars invoice for user {user_id}: {e}")
        raise PaymentError(
            "Не удалось создать счёт для оплаты. Попробуйте позже или используйте другой способ оплаты."
        )
