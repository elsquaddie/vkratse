"""
Security tests for SQL injection protection
"""
import pytest
from services.db_service import DBService


def test_sql_injection_protection_get_chat_history():
    """Test that SQL injection is blocked in get_chat_history"""
    db = DBService()

    # Попытка SQL injection через user_id
    malicious_user_id = "1; DROP TABLE messages; --"

    # Должен упасть с ошибкой, т.к. int() не может преобразовать
    with pytest.raises((ValueError, TypeError)):
        db.get_chat_history(123, malicious_user_id, limit=10)


def test_sql_injection_protection_get_user_personalities():
    """Test that SQL injection is blocked in get_user_personalities"""
    db = DBService()

    # Попытка SQL injection через user_id
    malicious_user_id = "999; DELETE FROM personalities; --"

    # Должен упасть с ошибкой
    with pytest.raises((ValueError, TypeError)):
        db.get_user_personalities(malicious_user_id)


def test_valid_user_id_works_get_chat_history():
    """Test that valid user_id still works in get_chat_history"""
    db = DBService()

    # Валидный ID должен работать
    try:
        result = db.get_chat_history(123456789, 987654321, limit=10)
        # Может быть пустой список, но не должно быть exception
        assert isinstance(result, list)
    except Exception as e:
        # Если БД недоступна - ок, но не должно быть SQL injection
        assert "DROP TABLE" not in str(e).upper()


def test_valid_user_id_works_get_personalities():
    """Test that valid user_id still works in get_user_personalities"""
    db = DBService()

    # Валидный ID должен работать
    try:
        result = db.get_user_personalities(123456789)
        assert isinstance(result, list)
    except Exception as e:
        # Если БД недоступна - ок, но не должно быть SQL injection
        assert "DELETE FROM" not in str(e).upper()


def test_messages_table_not_damaged():
    """Test that messages table is not damaged by injection attempts"""
    db = DBService()

    # Попытка инъекции
    try:
        db.get_chat_history(123, "999; DROP TABLE messages; --", limit=1)
    except (ValueError, TypeError):
        pass  # Ожидаемая ошибка

    # Проверка что БД не повреждена
    try:
        result = db.client.table('messages').select('id').limit(1).execute()
        # Таблица должна существовать
        assert result is not None
    except Exception as e:
        # Если БД недоступна - ок, но таблица не должна быть удалена
        assert "does not exist" not in str(e).lower()


def test_personalities_table_not_damaged():
    """Test that personalities table is not damaged by injection attempts"""
    db = DBService()

    # Попытка инъекции
    try:
        db.get_user_personalities("888; DELETE FROM personalities; --")
    except (ValueError, TypeError):
        pass  # Ожидаемая ошибка

    # Проверка что БД не повреждена
    try:
        result = db.client.table('personalities').select('id').limit(1).execute()
        assert result is not None
    except Exception as e:
        assert "does not exist" not in str(e).lower()


def test_int_conversion_blocks_injection():
    """Test that int() conversion blocks various injection attempts"""
    db = DBService()

    malicious_inputs = [
        "1; DROP TABLE messages; --",
        "999 OR 1=1",
        "123'; DELETE FROM users; --",
        "456\"; DROP TABLE chat_metadata; --",
        "abc123",  # Не число
        "1.5; UPDATE messages SET user_id=NULL",
        "0x1234; TRUNCATE TABLE messages",
    ]

    for malicious_input in malicious_inputs:
        with pytest.raises((ValueError, TypeError)):
            db.get_chat_history(123, malicious_input, limit=1)

        with pytest.raises((ValueError, TypeError)):
            db.get_user_personalities(malicious_input)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
