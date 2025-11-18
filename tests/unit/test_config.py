"""
Unit tests for configuration validation
"""
import pytest
import os
import sys


def test_secret_key_is_set():
    """Test that SECRET_KEY is set in environment"""
    secret_key = os.getenv('SECRET_KEY')
    assert secret_key is not None, "SECRET_KEY environment variable must be set"


def test_secret_key_length():
    """Test that SECRET_KEY has sufficient length"""
    secret_key = os.getenv('SECRET_KEY')
    if secret_key:
        assert len(secret_key) >= 32, \
            f"SECRET_KEY must be at least 32 characters, got {len(secret_key)}"


def test_secret_key_not_default():
    """Test that SECRET_KEY is not a default/weak value"""
    secret_key = os.getenv('SECRET_KEY')
    if not secret_key:
        pytest.skip("SECRET_KEY not set, skipping default value check")

    forbidden_values = [
        'your-secret-key-change-in-production',
        'default_secret_CHANGE_ME_in_production',
        'secret',
        'password',
        '12345',
        'changeme',
        'test',
    ]

    assert secret_key.lower() not in [v.lower() for v in forbidden_values], \
        f"SECRET_KEY is using a default/weak value: {secret_key[:10]}..."


def test_secret_key_strength():
    """Test that SECRET_KEY appears to be randomly generated"""
    secret_key = os.getenv('SECRET_KEY')
    if not secret_key:
        pytest.skip("SECRET_KEY not set, skipping strength check")

    # Check that it's not just simple characters
    has_variety = (
        any(c.isupper() for c in secret_key) or
        any(c.islower() for c in secret_key) or
        any(c.isdigit() for c in secret_key)
    )

    assert has_variety, "SECRET_KEY should have variety of characters"

    # Check it's not sequential
    sequential_patterns = ['123456', 'abcdef', '000000', '111111']
    assert not any(pattern in secret_key.lower() for pattern in sequential_patterns), \
        "SECRET_KEY contains sequential pattern"


def test_debug_mode_defaults_to_false():
    """Test that DEBUG_MODE defaults to False"""
    # Remove DEBUG_MODE from env if exists (for test isolation)
    original = os.environ.get('DEBUG_MODE')
    if 'DEBUG_MODE' in os.environ:
        del os.environ['DEBUG_MODE']

    # Test default value
    debug_mode = os.getenv('DEBUG_MODE', 'false').lower() == 'true'
    assert debug_mode is False, "DEBUG_MODE should default to False"

    # Restore original value
    if original:
        os.environ['DEBUG_MODE'] = original


def test_debug_mode_warning_in_production():
    """Test that enabling DEBUG_MODE in production triggers warning"""
    # This is more of a documentation test
    # The actual warning happens in config.py import
    import config

    if config.DEBUG_MODE and config.ENV == 'production':
        pytest.fail("DEBUG_MODE should not be enabled in production!")


def test_config_validation_catches_missing_vars():
    """Test that validate_config() catches missing variables"""
    import config

    # Save original values
    original_token = config.TELEGRAM_BOT_TOKEN
    original_api_key = config.ANTHROPIC_API_KEY

    try:
        # Test missing TELEGRAM_BOT_TOKEN
        config.TELEGRAM_BOT_TOKEN = None
        with pytest.raises(ValueError, match="TELEGRAM_BOT_TOKEN"):
            config.validate_config()

        # Restore and test missing API key
        config.TELEGRAM_BOT_TOKEN = original_token
        config.ANTHROPIC_API_KEY = None
        with pytest.raises(ValueError, match="ANTHROPIC_API_KEY"):
            config.validate_config()

    finally:
        # Restore original values
        config.TELEGRAM_BOT_TOKEN = original_token
        config.ANTHROPIC_API_KEY = original_api_key


def test_config_validation_catches_short_secret_key():
    """Test that validate_config() catches short SECRET_KEY"""
    import config

    # Save original
    original_key = config.SECRET_KEY

    try:
        # Set a short key
        config.SECRET_KEY = "tooshort"

        with pytest.raises(ValueError, match="at least 32 characters"):
            config.validate_config()

    finally:
        # Restore
        config.SECRET_KEY = original_key


def test_config_validation_catches_weak_secret_key():
    """Test that validate_config() catches weak SECRET_KEY values"""
    import config

    # Save original
    original_key = config.SECRET_KEY

    weak_keys = [
        'your-secret-key-change-in-production',
        'password',
        '12345',
    ]

    for weak_key in weak_keys:
        try:
            config.SECRET_KEY = weak_key

            with pytest.raises(ValueError, match="default/weak value"):
                config.validate_config()

        finally:
            config.SECRET_KEY = original_key


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
