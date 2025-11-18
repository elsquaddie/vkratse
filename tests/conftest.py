"""Pytest configuration and fixtures"""

import pytest
import os
from unittest.mock import Mock

# Set test environment variables
os.environ['SECRET_KEY'] = 'test_secret_key_for_tests_32_characters_long_abc123'
os.environ['TELEGRAM_BOT_TOKEN'] = 'test_token'
os.environ['TELEGRAM_WEBHOOK_SECRET'] = 'test_webhook_secret'
os.environ['ANTHROPIC_API_KEY'] = 'test_api_key'
os.environ['SUPABASE_URL'] = 'https://test.supabase.co'
os.environ['SUPABASE_KEY'] = 'test_key'
os.environ['ENV'] = 'test'
os.environ['DEBUG_MODE'] = 'false'


@pytest.fixture
def mock_db_service():
    """Mock DBService for testing"""
    from unittest.mock import Mock
    mock = Mock()
    mock.client = Mock()
    return mock


@pytest.fixture
def mock_ai_service():
    """Mock AIService for testing"""
    from unittest.mock import Mock
    mock = Mock()
    mock.client = Mock()
    return mock


@pytest.fixture
def sample_telegram_update():
    """Sample Telegram update for testing"""
    return {
        'update_id': 12345,
        'message': {
            'message_id': 1,
            'from': {
                'id': 123456789,
                'is_bot': False,
                'first_name': 'Test',
                'username': 'testuser'
            },
            'chat': {
                'id': 123456789,
                'first_name': 'Test',
                'username': 'testuser',
                'type': 'private'
            },
            'date': 1234567890,
            'text': '/start'
        }
    }


@pytest.fixture
def sample_payment_data():
    """Sample YooKassa payment data for testing"""
    return {
        'event': 'payment.succeeded',
        'object': {
            'id': 'test-payment-123',
            'status': 'succeeded',
            'paid': True,
            'amount': {
                'value': '299.00',
                'currency': 'RUB'
            },
            'metadata': {
                'user_id': '123456789',
                'tier': 'pro'
            }
        }
    }
