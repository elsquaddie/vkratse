# 🛡️ SECURITY FIXES & BUG ROADMAP

> **Пошаговый план исправления всех уязвимостей и багов**
> Каждый шаг: 1 баг → фикс → тестирование → ✅
> Создано: 2025-11-18

---

## 📖 КАК ИСПОЛЬЗОВАТЬ ЭТОТ ДОКУМЕНТ

### Формат работы:
1. Открой новый чат с Claude Code
2. Скажи: **"Делаем ШАГ 1 из SECURITY_FIXES.md"**
3. Claude применит фикс + создаст тест
4. Проверь результат
5. Отметь чекбокс ✅
6. Переходи к следующему шагу

### Порядок выполнения:
- **🔴 КРИТИЧЕСКИЕ (Шаги 1-10)** - делай ПЕРВЫМИ, не откладывая
- **🟠 ВАЖНЫЕ (Шаги 11-18)** - делай в течение недели
- **🟡 УЛУЧШЕНИЯ (Шаги 19+)** - делай когда будет время

### Перед началом:
```bash
# Создай новую ветку
git checkout -b security-fixes

# Установи dev-зависимости (будут созданы в процессе)
pip install -r requirements-dev.txt
```

---

## 🔴 КРИТИЧЕСКИЕ БАГИ (НЕМЕДЛЕННО!)

### ШАГ 1: SQL Injection в db_service.py

**Приоритет:** 🔴 КРИТИЧНО
**Риск:** Data breach, полная компрометация БД
**Файлы:** `services/db_service.py`

#### Описание проблемы:
```python
# services/db_service.py:516
.or_(f'user_id.eq.{user_id}')  # ❌ SQL INJECTION!
```

Использование f-string для построения SQL-запроса позволяет inject произвольный SQL код.

**Пример атаки:**
```python
user_id = "1; DROP TABLE messages; --"
# Результат: .or_(f'user_id.eq.1; DROP TABLE messages; --')
```

#### Как исправить:

**1. Найди строку 516 в `services/db_service.py`:**
```python
# БЫЛО (ОПАСНО!):
.or_(f'user_id.eq.{user_id}')

# СТАЛО (БЕЗОПАСНО):
.or_(f"user_id.eq.{int(user_id)},user_id.is.null")
```

**2. Также проверь другие места с f-string в фильтрах:**
```bash
# Поиск потенциальных проблем:
grep -n "f'" services/db_service.py | grep -E "(eq|neq|gt|lt|in)"
```

#### Тест для проверки:

**Создай файл:** `tests/security/test_sql_injection.py`

```python
import pytest
from services.db_service import DBService

def test_sql_injection_protection():
    """Test that SQL injection is blocked"""
    db = DBService()

    # Попытка SQL injection через user_id
    malicious_user_id = "1; DROP TABLE messages; --"

    with pytest.raises((ValueError, TypeError)):
        # Должен упасть с ошибкой, т.к. int() не может преобразовать
        db.get_user_personalities(malicious_user_id)

    # Проверка что БД не повреждена
    result = db.client.table('messages').select('id').limit(1).execute()
    assert result is not None  # Таблица не удалена

def test_valid_user_id_works():
    """Test that valid user_id still works"""
    db = DBService()

    # Валидный ID должен работать
    result = db.get_user_personalities(123456789)
    assert isinstance(result, list)
```

#### Как проверить:
```bash
# Запусти тест
pytest tests/security/test_sql_injection.py -v

# Ожидаемый результат:
# ✅ test_sql_injection_protection PASSED
# ✅ test_valid_user_id_works PASSED
```

#### Критерии успеха:
- [ ] F-string заменён на безопасную конструкцию
- [ ] Все тесты проходят
- [ ] Нет других f-string в SQL-фильтрах
- [ ] Коммит создан: `git commit -m "fix: SQL injection in db_service.py"`

---

### ШАГ 2: Дефолтный SECRET_KEY в коде

**Приоритет:** 🔴 КРИТИЧНО
**Риск:** Все HMAC подписи скомпрометированы
**Файлы:** `config.py`

#### Описание проблемы:
```python
# config.py:33
SECRET_KEY = os.getenv('SECRET_KEY', 'your-secret-key-change-in-production')
```

Если `SECRET_KEY` не установлен в environment variables, используется дефолтное значение. Это означает:
- Любой может подделать HMAC подписи
- Callback_data можно forge
- Несанкционированный доступ к функциям бота

#### Как исправить:

**1. Замени строку 33 в `config.py`:**
```python
# БЫЛО (ОПАСНО!):
SECRET_KEY = os.getenv('SECRET_KEY', 'your-secret-key-change-in-production')

# СТАЛО (БЕЗОПАСНО):
SECRET_KEY = os.getenv('SECRET_KEY')
if not SECRET_KEY:
    raise ValueError(
        "❌ SECRET_KEY environment variable is required!\n"
        "Generate: python -c 'import secrets; print(secrets.token_hex(32))'\n"
        "Set in Vercel: Settings → Environment Variables → Add SECRET_KEY"
    )
```

**2. Добавь проверку в validation:**
```python
# config.py - в функции validate_config() добавь:
def validate_config():
    """Validate required configuration"""
    errors = []

    # ... existing checks ...

    # NEW: Check SECRET_KEY strength
    if len(SECRET_KEY) < 32:
        errors.append("SECRET_KEY must be at least 32 characters (use secrets.token_hex(32))")

    if errors:
        if os.getenv('ENV') == 'production':
            raise ValueError(f"Configuration errors:\n" + "\n".join(errors))
        else:
            logger.warning(f"Configuration warnings:\n" + "\n".join(errors))
```

**3. Сгенерируй новый SECRET_KEY:**
```bash
# Локально
python -c "import secrets; print(secrets.token_hex(32))"

# Установи в Vercel Dashboard:
# Settings → Environment Variables → Add:
# SECRET_KEY = <generated_value>
```

#### Тест для проверки:

**Создай файл:** `tests/unit/test_config.py`

```python
import pytest
import os

def test_secret_key_required():
    """Test that SECRET_KEY is required"""
    # Сохраняем текущий SECRET_KEY
    original = os.getenv('SECRET_KEY')

    # Убираем SECRET_KEY
    if 'SECRET_KEY' in os.environ:
        del os.environ['SECRET_KEY']

    # Импорт должен упасть
    with pytest.raises(ValueError, match="SECRET_KEY environment variable is required"):
        import importlib
        import config
        importlib.reload(config)

    # Восстанавливаем
    if original:
        os.environ['SECRET_KEY'] = original

def test_secret_key_length():
    """Test that SECRET_KEY has sufficient length"""
    import config
    assert len(config.SECRET_KEY) >= 32, "SECRET_KEY must be at least 32 characters"

def test_secret_key_not_default():
    """Test that SECRET_KEY is not default value"""
    import config
    forbidden_values = [
        'your-secret-key-change-in-production',
        'secret',
        'password',
        '12345',
    ]
    assert config.SECRET_KEY not in forbidden_values, "SECRET_KEY is using default/weak value"
```

#### Как проверить:
```bash
# 1. Запусти тесты
pytest tests/unit/test_config.py -v

# 2. Проверь что без SECRET_KEY бот не запускается
unset SECRET_KEY
python -c "import config"  # Должен упасть с ошибкой

# 3. Установи SECRET_KEY и проверь снова
export SECRET_KEY=$(python -c 'import secrets; print(secrets.token_hex(32))')
python -c "import config; print('OK')"  # Должен вывести OK
```

#### Критерии успеха:
- [ ] Дефолтное значение удалено
- [ ] Бот не запускается без SECRET_KEY
- [ ] SECRET_KEY >= 32 символов
- [ ] Все тесты проходят
- [ ] Новый SECRET_KEY установлен в Vercel
- [ ] Коммит: `git commit -m "fix: require SECRET_KEY, remove default"`

---

### ШАГ 3: Race Condition в asyncio.all_tasks()

**Приоритет:** 🔴 КРИТИЧНО
**Риск:** Завершает tasks других запросов в serverless
**Файлы:** `api/index.py`

#### Описание проблемы:
```python
# api/index.py:644-646
pending = asyncio.all_tasks(loop)
results = loop.run_until_complete(asyncio.gather(*pending, return_exceptions=True))
```

`asyncio.all_tasks()` возвращает **ВСЕ** tasks в event loop, включая tasks из других одновременных запросов в том же Vercel worker. Это приводит к:
- Завершению чужих tasks
- Непредсказуемым ошибкам
- Data corruption

#### Как исправить:

**1. Найди строки 644-646 в `api/index.py`:**
```python
# БЫЛО (ОПАСНО!):
pending = asyncio.all_tasks(loop)
results = loop.run_until_complete(asyncio.gather(*pending, return_exceptions=True))

# СТАЛО (БЕЗОПАСНО):
current = asyncio.current_task(loop)
pending = [
    task for task in asyncio.all_tasks(loop)
    if not task.done() and task != current
]

if pending:
    results = loop.run_until_complete(
        asyncio.gather(*pending, return_exceptions=True, timeout=8.0)
    )

    # Log any exceptions
    for i, result in enumerate(results):
        if isinstance(result, Exception):
            logger.error(f"Task {i} failed: {result}")
```

**2. Добавь timeout на process_update():**
```python
# api/index.py - в функции application(), найди:
# loop.run_until_complete(process_update(update_data))

# Замени на:
try:
    loop.run_until_complete(
        asyncio.wait_for(process_update(update_data), timeout=8.0)
    )
except asyncio.TimeoutError:
    logger.error("Update processing timeout (>8s)")
    start_response('504 Gateway Timeout', headers)
    return [b'{"ok": false, "error": "timeout"}']
```

#### Тест для проверки:

**Создай файл:** `tests/integration/test_concurrent_webhooks.py`

```python
import pytest
import asyncio
from unittest.mock import patch, MagicMock

@pytest.mark.asyncio
async def test_concurrent_webhooks_isolation():
    """Test that concurrent webhooks don't interfere"""
    from api.index import process_update

    # Симулируем 2 одновременных webhook
    update1 = {'update_id': 1, 'message': {'text': '/start', 'chat': {'id': 1}}}
    update2 = {'update_id': 2, 'message': {'text': '/help', 'chat': {'id': 2}}}

    # Запускаем параллельно
    results = await asyncio.gather(
        process_update(update1),
        process_update(update2),
        return_exceptions=True
    )

    # Оба должны завершиться без ошибок
    assert not isinstance(results[0], Exception)
    assert not isinstance(results[1], Exception)

@pytest.mark.asyncio
async def test_task_cleanup_only_own_tasks():
    """Test that cleanup doesn't affect other tasks"""
    async def dummy_task():
        await asyncio.sleep(10)

    # Создаём "чужой" task
    other_task = asyncio.create_task(dummy_task())

    # Импортируем cleanup логику
    from api.index import application

    # ... simulate request processing ...

    # Проверяем что чужой task НЕ был отменён
    assert not other_task.done(), "Other task was cancelled!"

    # Cleanup
    other_task.cancel()
```

#### Как проверить:
```bash
# Запусти тесты
pytest tests/integration/test_concurrent_webhooks.py -v

# Stress test (если есть staging):
# Отправь 10 одновременных webhooks и проверь логи
```

#### Критерии успеха:
- [ ] Фильтрация tasks по current_task()
- [ ] Добавлен timeout 8 секунд
- [ ] Тесты проходят
- [ ] Нет ошибок в логах при одновременных запросах
- [ ] Коммит: `git commit -m "fix: race condition in asyncio tasks cleanup"`

---

### ШАГ 4: Отсутствие Telegram Webhook Verification

**Приоритет:** 🔴 КРИТИЧНО
**Риск:** Любой может отправить fake updates
**Файлы:** `api/index.py`, `config.py`

#### Описание проблемы:
Telegram webhook принимает POST запросы от кого угодно. Нет проверки что запрос действительно от Telegram.

**Пример атаки:**
```bash
# Злоумышленник может отправить:
curl -X POST https://vkratse.vercel.app/api/index \
  -H "Content-Type: application/json" \
  -d '{"update_id": 999, "message": {"text": "/admin", "from": {"id": 123}}}'

# Бот обработает как настоящий update!
```

#### Как исправить:

**1. Добавь в `config.py`:**
```python
# config.py - после SECRET_KEY
TELEGRAM_WEBHOOK_SECRET = os.getenv('TELEGRAM_WEBHOOK_SECRET')
if not TELEGRAM_WEBHOOK_SECRET:
    raise ValueError(
        "❌ TELEGRAM_WEBHOOK_SECRET environment variable is required!\n"
        "Generate: python -c 'import secrets; print(secrets.token_urlsafe(32))'\n"
        "Set webhook: curl 'https://api.telegram.org/bot<TOKEN>/setWebhook?"
        "url=https://vkratse.vercel.app&secret_token=<SECRET>'"
    )
```

**2. Добавь проверку в `api/index.py`:**
```python
# api/index.py - в начале функции application(), ПЕРЕД content_length:

def application(environ, start_response):
    """WSGI application entry point"""

    # ===== NEW: WEBHOOK VERIFICATION =====
    webhook_secret = environ.get('HTTP_X_TELEGRAM_BOT_API_SECRET_TOKEN')

    if webhook_secret != config.TELEGRAM_WEBHOOK_SECRET:
        logger.warning(
            f"❌ Webhook verification failed! "
            f"IP: {environ.get('REMOTE_ADDR')}, "
            f"Secret: {webhook_secret[:10]}... (expected {config.TELEGRAM_WEBHOOK_SECRET[:10]}...)"
        )
        start_response('403 Forbidden', [('Content-Type', 'application/json')])
        return [b'{"ok": false, "error": "forbidden"}']
    # ===== END VERIFICATION =====

    # ... rest of existing code ...
```

**3. Установи secret в Telegram:**
```bash
# 1. Сгенерируй secret
SECRET=$(python -c 'import secrets; print(secrets.token_urlsafe(32))')
echo "Generated secret: $SECRET"

# 2. Установи в Vercel
# Vercel Dashboard → Settings → Environment Variables → Add:
# TELEGRAM_WEBHOOK_SECRET = <secret>

# 3. Обнови webhook в Telegram
curl "https://api.telegram.org/bot${TELEGRAM_BOT_TOKEN}/setWebhook?url=https://vkratse.vercel.app&secret_token=${SECRET}"

# 4. Проверь что webhook установлен
curl "https://api.telegram.org/bot${TELEGRAM_BOT_TOKEN}/getWebhookInfo"
```

#### Тест для проверки:

**Создай файл:** `tests/security/test_webhook_verification.py`

```python
import pytest
from unittest.mock import Mock
from api.index import application

def test_webhook_without_secret_rejected():
    """Test that webhook without secret is rejected"""
    environ = {
        'REQUEST_METHOD': 'POST',
        'CONTENT_LENGTH': '100',
        'wsgi.input': Mock(),
        # NO HTTP_X_TELEGRAM_BOT_API_SECRET_TOKEN header
    }

    responses = []
    def start_response(status, headers):
        responses.append(status)

    result = application(environ, start_response)

    assert responses[0] == '403 Forbidden'
    assert b'forbidden' in b''.join(result)

def test_webhook_with_wrong_secret_rejected():
    """Test that webhook with wrong secret is rejected"""
    environ = {
        'REQUEST_METHOD': 'POST',
        'CONTENT_LENGTH': '100',
        'wsgi.input': Mock(),
        'HTTP_X_TELEGRAM_BOT_API_SECRET_TOKEN': 'WRONG_SECRET',
    }

    responses = []
    def start_response(status, headers):
        responses.append(status)

    result = application(environ, start_response)

    assert responses[0] == '403 Forbidden'

def test_webhook_with_correct_secret_accepted():
    """Test that webhook with correct secret is accepted"""
    import config

    environ = {
        'REQUEST_METHOD': 'POST',
        'CONTENT_LENGTH': '50',
        'wsgi.input': Mock(read=lambda: b'{"update_id": 1, "message": {}}'),
        'HTTP_X_TELEGRAM_BOT_API_SECRET_TOKEN': config.TELEGRAM_WEBHOOK_SECRET,
    }

    responses = []
    def start_response(status, headers):
        responses.append(status)

    result = application(environ, start_response)

    # Не должен быть 403
    assert '403' not in responses[0]
```

#### Как проверить:
```bash
# 1. Запусти тесты
pytest tests/security/test_webhook_verification.py -v

# 2. Попробуй fake webhook (должен вернуть 403)
curl -X POST https://vkratse.vercel.app/api/index \
  -H "Content-Type: application/json" \
  -d '{"update_id": 999}'

# 3. Проверь логи Vercel - должна быть запись "Webhook verification failed"
```

#### Критерии успеха:
- [ ] TELEGRAM_WEBHOOK_SECRET добавлен в config
- [ ] Проверка secret добавлена в application()
- [ ] Secret установлен в Vercel
- [ ] Webhook обновлён в Telegram
- [ ] Тесты проходят
- [ ] Fake webhooks отклоняются (403)
- [ ] Коммит: `git commit -m "fix: add Telegram webhook verification"`

---

### ШАГ 5: БАГ в Cache TTL (.seconds)

**Приоритет:** 🔴 КРИТИЧНО
**Риск:** Cache игнорирует дни/часы, работает неправильно
**Файлы:** `services/subscription.py`

#### Описание проблемы:
```python
# services/subscription.py:318
if (datetime.now(timezone.utc) - checked_at).seconds < 3600:
```

`.seconds` возвращает **только секунды внутри минуты** (0-59), игнорируя дни и часы!

**Пример бага:**
```python
from datetime import datetime, timedelta

# Разница: 2 дня 1 час 30 секунд
delta = timedelta(days=2, hours=1, seconds=30)

print(delta.seconds)         # Вывод: 3630 (только 1 час 30 сек, БЕЗ 2 дней!)
print(delta.total_seconds()) # Вывод: 176430 (правильно, всё включено)

# Результат: cache TTL проверка НЕВЕРНА!
```

#### Как исправить:

**1. Найди строку 318 в `services/subscription.py`:**
```python
# БЫЛО (БАГ!):
if (datetime.now(timezone.utc) - checked_at).seconds < 3600:
    return self._cache[user_id]

# СТАЛО (ПРАВИЛЬНО):
if (datetime.now(timezone.utc) - checked_at).total_seconds() < 3600:
    return self._cache[user_id]
```

**2. Проверь другие использования `.seconds`:**
```bash
# Поиск потенциальных проблем
grep -n "\.seconds" services/*.py modules/*.py

# Замени ВСЕ .seconds на .total_seconds() где используется для TTL/timeout
```

#### Тест для проверки:

**Создай файл:** `tests/unit/test_cache_ttl.py`

```python
import pytest
from datetime import datetime, timedelta, timezone
from services.subscription import SubscriptionService
from unittest.mock import Mock

def test_cache_ttl_respects_hours_and_days():
    """Test that cache TTL correctly handles hours and days"""
    db_mock = Mock()
    service = SubscriptionService(db_mock)

    # Добавим тестовые данные в cache
    user_id = 123456789
    test_tier = 'pro'

    # Симулируем старый cache (2 часа назад)
    old_time = datetime.now(timezone.utc) - timedelta(hours=2)
    service._cache[user_id] = test_tier
    service._cache_time[user_id] = old_time

    # Запрашиваем подписку
    result = service._get_cached_subscription(user_id)

    # Cache должен быть НЕВАЛИДЕН (>1 час), поэтому result должен быть None
    assert result is None, "Cache should be invalid after 2 hours!"

def test_cache_ttl_works_within_hour():
    """Test that cache is valid within 1 hour"""
    db_mock = Mock()
    service = SubscriptionService(db_mock)

    user_id = 123456789
    test_tier = 'premium'

    # Симулируем свежий cache (30 минут назад)
    recent_time = datetime.now(timezone.utc) - timedelta(minutes=30)
    service._cache[user_id] = test_tier
    service._cache_time[user_id] = recent_time

    # Запрашиваем подписку
    result = service._get_cached_subscription(user_id)

    # Cache должен быть ВАЛИДЕН (<1 час)
    assert result == test_tier, "Cache should be valid within 1 hour!"

def test_timedelta_seconds_vs_total_seconds():
    """Demonstrate the bug with .seconds vs .total_seconds()"""
    # 2 дня 1 час 30 секунд
    delta = timedelta(days=2, hours=1, seconds=30)

    # .seconds НЕПРАВИЛЬНО (игнорирует дни)
    assert delta.seconds == 3630  # Только 1 час 30 сек

    # .total_seconds() ПРАВИЛЬНО (всё включено)
    assert delta.total_seconds() == 176430  # 2 дня + 1 час + 30 сек

    # Демонстрация бага:
    # Если checked_at был 2 дня назад, но .seconds < 3600 (1 час):
    # Старый код считал бы cache валидным! ❌
```

#### Как проверить:
```bash
# Запусти тесты
pytest tests/unit/test_cache_ttl.py -v

# Ожидаемый результат:
# ✅ test_cache_ttl_respects_hours_and_days PASSED
# ✅ test_cache_ttl_works_within_hour PASSED
# ✅ test_timedelta_seconds_vs_total_seconds PASSED
```

#### Критерии успеха:
- [ ] `.seconds` заменён на `.total_seconds()`
- [ ] Все тесты проходят
- [ ] Нет других использований `.seconds` для TTL
- [ ] Cache работает правильно
- [ ] Коммит: `git commit -m "fix: cache TTL bug - use total_seconds()"`

---

### ШАГ 6: YooKassa Handler не Async

**Приоритет:** 🔴 КРИТИЧНО
**Риск:** Платежи НЕ ОБРАБАТЫВАЮТСЯ
**Файлы:** `api/yookassa_webhook.py`

#### Описание проблемы:
```python
# api/yookassa_webhook.py:67
def handler(request):  # ❌ Sync функция
    # ...
    loop.run_until_complete(process_payment(...))  # ❌ Вызывает async
```

Vercel Python runtime ожидает:
- **Sync** handler для WSGI
- **Async** handler для ASGI

Текущий код - hybrid (sync вызывает async) - **НЕ РАБОТАЕТ КОРРЕКТНО** в serverless.

#### Как исправить:

**1. Замени всю функцию `handler()` в `api/yookassa_webhook.py`:**

```python
# api/yookassa_webhook.py:67-142

# БЫЛО (НЕ РАБОТАЕТ):
def handler(request):
    """
    Vercel serverless function handler for YooKassa webhooks
    """
    # ... sync код ...
    loop.run_until_complete(process_payment(...))

# СТАЛО (РАБОТАЕТ):
async def handler(request):
    """
    Vercel serverless function handler for YooKassa webhooks
    """
    if request.method != 'POST':
        return {
            'statusCode': 405,
            'body': json.dumps({'error': 'Method not allowed'})
        }

    # Get request body
    try:
        body = await request.body() if hasattr(request, 'body') else request.get_json()
    except Exception as e:
        logger.error(f"Failed to parse request body: {e}")
        return {
            'statusCode': 400,
            'body': json.dumps({'error': 'Invalid request body'})
        }

    # Verify IP (если реализована проверка)
    client_ip = request.headers.get('X-Forwarded-For', request.remote_addr)
    if not verify_ip(client_ip):
        logger.warning(f"Webhook from unauthorized IP: {client_ip}")
        return {
            'statusCode': 403,
            'body': json.dumps({'error': 'Forbidden'})
        }

    # Process payment
    try:
        await process_payment(body)
        return {
            'statusCode': 200,
            'body': json.dumps({'status': 'ok'})
        }
    except Exception as e:
        logger.error(f"Payment processing failed: {e}")
        return {
            'statusCode': 500,
            'body': json.dumps({'error': 'Internal server error'})
        }
```

**2. Обнови export в конце файла:**
```python
# api/yookassa_webhook.py - в конце файла

# БЫЛО:
# def application(environ, start_response):
#     loop = asyncio.new_event_loop()
#     ...

# СТАЛО:
def application(environ, start_response):
    """WSGI wrapper for async handler"""
    # Для Vercel serverless можно использовать прямой async
    # Но если нужен WSGI, используй этот wrapper:

    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    try:
        # Преобразуем WSGI environ в request-like объект
        from werkzeug.wrappers import Request
        request = Request(environ)

        # Вызываем async handler
        result = loop.run_until_complete(handler(request))

        # Форматируем ответ
        status = f"{result['statusCode']} OK"
        headers = [('Content-Type', 'application/json')]
        start_response(status, headers)
        return [result['body'].encode()]

    except Exception as e:
        logger.error(f"Webhook error: {e}", exc_info=True)
        start_response('500 Internal Server Error', [])
        return [b'{"error": "internal error"}']
    finally:
        loop.close()
```

#### Тест для проверки:

**Создай файл:** `tests/integration/test_yookassa_webhook.py`

```python
import pytest
import json
from unittest.mock import Mock, patch, AsyncMock

@pytest.mark.asyncio
async def test_yookassa_webhook_success():
    """Test successful payment webhook processing"""
    from api.yookassa_webhook import handler

    # Mock request
    request = Mock()
    request.method = 'POST'
    request.headers = {'X-Forwarded-For': '185.71.76.0'}  # YooKassa IP

    payment_data = {
        'event': 'payment.succeeded',
        'object': {
            'id': 'test-payment-id',
            'metadata': {'user_id': '123456789', 'tier': 'pro'},
            'status': 'succeeded'
        }
    }
    request.body = AsyncMock(return_value=json.dumps(payment_data))
    request.get_json = Mock(return_value=payment_data)

    # Mock DB
    with patch('services.db_service.DBService') as mock_db:
        mock_db.return_value.create_subscription = AsyncMock()

        # Call handler
        result = await handler(request)

        assert result['statusCode'] == 200
        assert 'ok' in result['body']

@pytest.mark.asyncio
async def test_yookassa_webhook_invalid_method():
    """Test that non-POST requests are rejected"""
    from api.yookassa_webhook import handler

    request = Mock()
    request.method = 'GET'

    result = await handler(request)

    assert result['statusCode'] == 405
    assert 'not allowed' in result['body'].lower()

@pytest.mark.asyncio
async def test_yookassa_webhook_malformed_body():
    """Test that malformed requests return 400"""
    from api.yookassa_webhook import handler

    request = Mock()
    request.method = 'POST'
    request.body = AsyncMock(side_effect=Exception("Parse error"))
    request.get_json = Mock(side_effect=Exception("Parse error"))

    result = await handler(request)

    assert result['statusCode'] == 400
```

#### Как проверить:
```bash
# 1. Запусти тесты
pytest tests/integration/test_yookassa_webhook.py -v

# 2. Отправь тестовый webhook (используй YooKassa test mode)
curl -X POST https://vkratse.vercel.app/api/yookassa_webhook \
  -H "Content-Type: application/json" \
  -d '{
    "event": "payment.succeeded",
    "object": {
      "id": "test-123",
      "metadata": {"user_id": "123", "tier": "pro"},
      "status": "succeeded"
    }
  }'

# 3. Проверь логи Vercel - не должно быть ошибок event loop
```

#### Критерии успеха:
- [ ] `handler()` функция теперь async
- [ ] WSGI wrapper корректно вызывает async handler
- [ ] Тесты проходят
- [ ] Тестовый webhook обрабатывается без ошибок
- [ ] В логах нет "event loop" errors
- [ ] Коммит: `git commit -m "fix: make YooKassa handler async"`

---

### ШАГ 7: Отсутствие Idempotency Check

**Приоритет:** 🔴 КРИТИЧНО
**Риск:** Duplicate webhooks → двойная обработка
**Файлы:** `api/index.py`, `api/yookassa_webhook.py`, SQL migration

#### Описание проблемы:
Telegram и YooKassa могут отправить duplicate webhooks при:
- Network timeouts
- Retry logic
- Infrastructure issues

Без idempotency check:
- Telegram update обрабатывается дважды (дублирующиеся сообщения в БД)
- Платёж активируется дважды (двойная подписка)

#### Как исправить:

**1. Создай SQL миграцию:** `sql/migrations/005_webhook_log.sql`

```sql
-- Таблица для idempotency check
CREATE TABLE IF NOT EXISTS webhook_log (
    id BIGSERIAL PRIMARY KEY,
    webhook_type VARCHAR(50) NOT NULL, -- 'telegram' или 'yookassa'
    webhook_id VARCHAR(255) NOT NULL,  -- update_id или payment_id
    processed_at TIMESTAMP DEFAULT NOW(),
    payload JSONB,                     -- Опционально: для отладки

    UNIQUE(webhook_type, webhook_id)
);

-- Индексы
CREATE INDEX idx_webhook_log_type_id ON webhook_log(webhook_type, webhook_id);
CREATE INDEX idx_webhook_log_processed ON webhook_log(processed_at);

-- Auto-cleanup старых записей (>7 дней)
-- Запускать через cron или manual cleanup script
```

**2. Добавь метод в `services/db_service.py`:**

```python
# services/db_service.py - добавь в класс DBService

def check_and_mark_webhook_processed(
    self,
    webhook_type: str,
    webhook_id: str,
    payload: dict = None
) -> bool:
    """
    Check if webhook was already processed, and mark as processed if not.

    Returns:
        True if webhook is NEW (should be processed)
        False if webhook was already processed (skip)
    """
    try:
        # Check if exists
        result = self.client.table('webhook_log')\
            .select('webhook_id')\
            .eq('webhook_type', webhook_type)\
            .eq('webhook_id', str(webhook_id))\
            .execute()

        if result.data:
            logger.warning(
                f"Duplicate {webhook_type} webhook: {webhook_id}, skipping"
            )
            return False  # Already processed

        # Mark as processed
        self.client.table('webhook_log').insert({
            'webhook_type': webhook_type,
            'webhook_id': str(webhook_id),
            'payload': payload  # Optional
        }).execute()

        return True  # New webhook, should process

    except Exception as e:
        logger.error(f"Idempotency check failed: {e}")
        # В случае ошибки БД - лучше обработать (риск дубликата)
        return True
```

**3. Используй в `api/index.py`:**

```python
# api/index.py - в функции process_update(), в самом начале:

async def process_update(update_data: dict):
    """Process a single Telegram update"""
    update_id = update_data.get('update_id')

    # ===== NEW: IDEMPOTENCY CHECK =====
    db = DBService()
    if not db.check_and_mark_webhook_processed('telegram', update_id, update_data):
        logger.info(f"Skipping duplicate update {update_id}")
        return  # Already processed
    # ===== END IDEMPOTENCY CHECK =====

    # ... rest of existing code ...
```

**4. Используй в `api/yookassa_webhook.py`:**

```python
# api/yookassa_webhook.py - в функции process_payment():

async def process_payment(payment_data: dict):
    """Process YooKassa payment notification"""
    payment_id = payment_data['object']['id']

    # ===== NEW: IDEMPOTENCY CHECK =====
    db = DBService()
    if not db.check_and_mark_webhook_processed('yookassa', payment_id, payment_data):
        logger.info(f"Skipping duplicate payment {payment_id}")
        return  # Already processed
    # ===== END IDEMPOTENCY CHECK =====

    # ... rest of existing code ...
```

#### Тест для проверки:

**Создай файл:** `tests/integration/test_idempotency.py`

```python
import pytest
from services.db_service import DBService

def test_first_webhook_is_processed():
    """Test that first webhook is marked for processing"""
    db = DBService()

    should_process = db.check_and_mark_webhook_processed(
        'telegram',
        'test_update_123'
    )

    assert should_process is True, "First webhook should be processed"

def test_duplicate_webhook_is_skipped():
    """Test that duplicate webhook is skipped"""
    db = DBService()
    webhook_id = 'test_update_456'

    # Первый раз
    first = db.check_and_mark_webhook_processed('telegram', webhook_id)
    assert first is True

    # Второй раз (duplicate)
    second = db.check_and_mark_webhook_processed('telegram', webhook_id)
    assert second is False, "Duplicate webhook should be skipped"

def test_different_webhook_types_independent():
    """Test that same ID for different types are independent"""
    db = DBService()
    webhook_id = 'same_id_789'

    # Telegram webhook
    telegram = db.check_and_mark_webhook_processed('telegram', webhook_id)
    assert telegram is True

    # YooKassa webhook (same ID, but different type)
    yookassa = db.check_and_mark_webhook_processed('yookassa', webhook_id)
    assert yookassa is True, "Different types should be independent"

@pytest.mark.asyncio
async def test_telegram_duplicate_update_skipped():
    """Integration test: duplicate Telegram update is skipped"""
    from api.index import process_update

    update = {
        'update_id': 999888,
        'message': {
            'text': '/start',
            'chat': {'id': 123},
            'from': {'id': 456}
        }
    }

    # First processing
    await process_update(update)

    # Get messages count
    db = DBService()
    messages1 = db.client.table('messages').select('*').eq('chat_id', 123).execute()
    count1 = len(messages1.data)

    # Second processing (duplicate)
    await process_update(update)

    # Get messages count again
    messages2 = db.client.table('messages').select('*').eq('chat_id', 123).execute()
    count2 = len(messages2.data)

    # Должно быть ОДИНАКОВОЕ количество (duplicate не обработан)
    assert count1 == count2, "Duplicate update should not create duplicate messages"
```

#### Как проверить:
```bash
# 1. Примени миграцию
psql $SUPABASE_URL -f sql/migrations/005_webhook_log.sql

# Или через Supabase Dashboard:
# SQL Editor → New Query → вставь SQL → Run

# 2. Запусти тесты
pytest tests/integration/test_idempotency.py -v

# 3. Проверь что таблица создана
# Supabase Dashboard → Table Editor → webhook_log

# 4. Отправь duplicate webhook вручную (дважды подряд):
curl -X POST https://vkratse.vercel.app/api/index \
  -H "X-Telegram-Bot-Api-Secret-Token: $TELEGRAM_WEBHOOK_SECRET" \
  -H "Content-Type: application/json" \
  -d '{"update_id": 777, "message": {"text": "test"}}'

# Второй раз с тем же update_id
curl -X POST https://vkratse.vercel.app/api/index \
  -H "X-Telegram-Bot-Api-Secret-Token: $TELEGRAM_WEBHOOK_SECRET" \
  -H "Content-Type: application/json" \
  -d '{"update_id": 777, "message": {"text": "test"}}'

# 5. Проверь логи - второй запрос должен вывести "Skipping duplicate"
```

#### Критерии успеха:
- [ ] Таблица `webhook_log` создана
- [ ] Метод `check_and_mark_webhook_processed()` добавлен
- [ ] Idempotency check в `api/index.py`
- [ ] Idempotency check в `api/yookassa_webhook.py`
- [ ] Тесты проходят
- [ ] Duplicate webhooks не обрабатываются
- [ ] Коммит: `git commit -m "fix: add idempotency check for webhooks"`

---

### ШАГ 8: Логирование HMAC Signatures

**Приоритет:** 🔴 КРИТИЧНО
**Риск:** Утечка signatures → подделка подписей
**Файлы:** `utils/security.py`

#### Описание проблемы:
```python
# utils/security.py:73, 100
logger.info(f"[SIGNATURE CREATE] ... signature='{signature}'")
logger.debug(f"Expected signature: {expected_sig}")
```

Signatures логируются в production logs. Если злоумышленник получит доступ к логам:
- Может подделать любые callback_data
- Обойти HMAC защиту
- Получить несанкционированный доступ

#### Как исправить:

**1. Найди и удали/замени все логи signatures в `utils/security.py`:**

**Строка 73:**
```python
# БЫЛО (ОПАСНО!):
logger.info(
    f"[SIGNATURE CREATE] user_id={user_id}, "
    f"data='{data}', signature='{signature}'"
)

# СТАЛО (БЕЗОПАСНО):
if config.DEBUG_MODE:  # Только в debug mode
    logger.debug(
        f"[SIGNATURE CREATE] user_id={user_id}, "
        f"data='{data}', signature='***REDACTED***'"
    )
else:
    logger.info(f"[SIGNATURE CREATE] user_id={user_id}, data_length={len(data)}")
```

**Строка 100:**
```python
# БЫЛО (ОПАСНО!):
logger.debug(f"Expected signature: {expected_sig}")
logger.debug(f"Provided signature: {provided_signature}")

# СТАЛО (БЕЗОПАСНО):
if config.DEBUG_MODE:
    logger.debug(f"Expected signature: {expected_sig[:8]}...")
    logger.debug(f"Provided signature: {provided_signature[:8]}...")
else:
    logger.info("Signature verification in progress")
```

**Строка 173 (если есть похожие логи):**
```python
# Везде где логируется signature/secret_key:
# БЫЛО: logger.info(f"... signature={sig}")
# СТАЛО: logger.info(f"... signature={'***' if not config.DEBUG_MODE else sig[:8]+'...'}")
```

**2. Добавь в `config.py` флаг DEBUG_MODE:**
```python
# config.py - в конце файла
DEBUG_MODE = os.getenv('DEBUG_MODE', 'false').lower() == 'true'

# WARNING: Never enable DEBUG_MODE in production!
if DEBUG_MODE and os.getenv('ENV') == 'production':
    logger.warning("⚠️ DEBUG_MODE is enabled in production! Secrets may be logged!")
```

**3. Проверь другие файлы на утечки:**
```bash
# Поиск потенциальных утечек
grep -rn "logger\." . --include="*.py" | grep -E "(signature|secret|token|password)" | grep -v "test"

# Замени все найденные на redacted версии
```

#### Тест для проверки:

**Создай файл:** `tests/security/test_no_secret_leaks.py`

```python
import pytest
import logging
from io import StringIO
from utils.security import create_string_signature, verify_string_signature
import config

def test_signatures_not_logged_in_production(caplog):
    """Test that signatures are not logged in production mode"""
    # Симулируем production mode
    original_debug = config.DEBUG_MODE
    config.DEBUG_MODE = False

    with caplog.at_level(logging.INFO):
        signature = create_string_signature("test_data", 12345)

    # Проверяем что signature НЕ в логах
    for record in caplog.records:
        assert signature not in record.message, \
            f"Signature leaked in log: {record.message}"
        assert "***" in record.message or "REDACTED" in record.message or \
               "data_length" in record.message, \
            "Log should contain redacted placeholder"

    # Восстанавливаем
    config.DEBUG_MODE = original_debug

def test_signatures_logged_in_debug_mode(caplog):
    """Test that signatures CAN be logged in debug mode (for development)"""
    # Симулируем debug mode
    original_debug = config.DEBUG_MODE
    config.DEBUG_MODE = True

    with caplog.at_level(logging.DEBUG):
        signature = create_string_signature("test_data", 12345)

    # В debug mode можно логировать (но частично)
    logged = any(sig[:8] in record.message for record in caplog.records for sig in [signature])
    # НО полный signature всё равно не должен быть
    full_logged = any(signature in record.message for record in caplog.records)

    assert not full_logged, "Full signature should never be logged!"

    # Восстанавливаем
    config.DEBUG_MODE = original_debug

def test_secret_key_never_logged():
    """Test that SECRET_KEY is never logged"""
    import config
    import sys
    from io import StringIO

    # Capture all logs
    log_capture = StringIO()
    handler = logging.StreamHandler(log_capture)
    logging.root.addHandler(handler)

    # Do some operations that might log
    create_string_signature("test", 123)
    verify_string_signature("test", 123, "fake_sig")

    # Check logs
    logs = log_capture.getvalue()

    # SECRET_KEY не должен быть в логах ни в каком виде
    assert config.SECRET_KEY not in logs, "SECRET_KEY leaked in logs!"

    # Cleanup
    logging.root.removeHandler(handler)
```

#### Как проверить:
```bash
# 1. Запусти тесты
pytest tests/security/test_no_secret_leaks.py -v

# 2. Проверь что в production логах нет secrets
# Vercel Dashboard → Logs → Search для "signature"

# 3. Grep по коду на утечки
grep -rn "logger\." --include="*.py" | grep -E "(signature|secret)" | less

# 4. Убедись что DEBUG_MODE = false в production
# Vercel Dashboard → Environment Variables → DEBUG_MODE должна быть unset или false
```

#### Критерии успеха:
- [ ] Все логи signatures удалены или redacted
- [ ] DEBUG_MODE флаг добавлен в config
- [ ] В production mode signatures не логируются
- [ ] Тесты проходят
- [ ] Grep не находит утечек
- [ ] Коммит: `git commit -m "fix: remove signature logging, prevent secret leaks"`

---

### ШАГ 9: Отсутствие Retry на DB Failures

**Приоритет:** 🔴 КРИТИЧНО
**Риск:** Data loss при transient failures
**Файлы:** `services/db_service.py`, `services/ai_service.py`

#### Описание проблемы:
Нет retry логики для:
- Supabase API calls (network timeouts, rate limits)
- Claude API calls (429 errors, timeouts)

Один network glitch = failed request = потеря данных.

#### Как исправить:

**1. Добавь зависимость в `requirements.txt`:**
```
tenacity==8.2.3
```

**2. Создай retry декораторы в `utils/retry.py`:**

```python
# utils/retry.py - НОВЫЙ ФАЙЛ
"""Retry decorators for external API calls"""

import logging
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type,
    before_sleep_log
)
from anthropic import APIError, RateLimitError
from postgrest.exceptions import APIError as PostgrestAPIError

logger = logging.getLogger(__name__)

# Retry для Supabase
db_retry = retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=1, max=10),
    retry=retry_if_exception_type((
        PostgrestAPIError,
        ConnectionError,
        TimeoutError,
    )),
    before_sleep=before_sleep_log(logger, logging.WARNING),
    reraise=True
)

# Retry для Claude API
ai_retry = retry(
    stop=stop_after_attempt(2),  # API calls дороже, меньше попыток
    wait=wait_exponential(multiplier=2, min=2, max=20),
    retry=retry_if_exception_type((
        RateLimitError,
        APIError,
        TimeoutError,
    )),
    before_sleep=before_sleep_log(logger, logging.WARNING),
    reraise=True
)
```

**3. Примени к критическим методам в `services/db_service.py`:**

```python
# services/db_service.py - в начале файла
from utils.retry import db_retry

class DBService:
    # ... existing __init__ ...

    @db_retry
    def save_message(self, chat_id: int, user_id: int, username: str, message_text: str):
        """Save message with retry logic"""
        # ... existing code ...

    @db_retry
    def get_subscription(self, user_id: int):
        """Get subscription with retry logic"""
        # ... existing code ...

    @db_retry
    def create_subscription(self, user_id: int, tier: str, ...):
        """Create subscription with retry logic"""
        # ... existing code ...

    # Добавь @db_retry ко ВСЕМ методам которые делают DB calls
```

**4. Примени к AI calls в `services/ai_service.py`:**

```python
# services/ai_service.py - в начале файла
from utils.retry import ai_retry

class AIService:
    # ... existing __init__ ...

    @ai_retry
    def generate_summary(self, messages: list, personality: dict, ...):
        """Generate summary with retry logic"""
        # ... existing code ...

    @ai_retry
    def generate_chat_response(self, personality: dict, history: list, ...):
        """Generate chat response with retry logic"""
        # ... existing code ...

    @ai_retry
    def generate_judge_verdict(self, ...):
        """Generate verdict with retry logic"""
        # ... existing code ...
```

**5. Добавь timeout к HTTP clients:**

```python
# services/db_service.py - в __init__
from supabase import create_client, Client
from supabase.lib.client_options import ClientOptions
import httpx

def __init__(self):
    # Добавь timeout
    self.client: Client = create_client(
        config.SUPABASE_URL,
        config.SUPABASE_KEY,
        options=ClientOptions(
            headers={"Connection": "keep-alive"},
            timeout=10.0  # 10 секунд timeout
        )
    )

# services/ai_service.py - в __init__
import anthropic

def __init__(self):
    self.client = anthropic.Anthropic(
        api_key=config.ANTHROPIC_API_KEY,
        timeout=30.0,  # 30 секунд для AI (может быть долго)
        max_retries=0,  # Используем свой retry механизм
    )
```

#### Тест для проверки:

**Создай файл:** `tests/integration/test_retry_logic.py`

```python
import pytest
from unittest.mock import patch, Mock
from services.db_service import DBService
from services.ai_service import AIService
from postgrest.exceptions import APIError
from anthropic import RateLimitError

def test_db_retry_on_network_error():
    """Test that DB operations retry on network errors"""
    db = DBService()

    # Mock client to fail 2 times, then succeed
    call_count = [0]

    def failing_insert(*args, **kwargs):
        call_count[0] += 1
        if call_count[0] < 3:
            raise ConnectionError("Network timeout")
        return Mock(data=[{'id': 1}])

    with patch.object(db.client.table('messages'), 'insert', side_effect=failing_insert):
        # Should succeed after retries
        db.save_message(123, 456, 'user', 'test message')

    # Должно быть 3 попытки
    assert call_count[0] == 3, f"Expected 3 attempts, got {call_count[0]}"

def test_db_fails_after_max_retries():
    """Test that DB operations fail after max retries"""
    db = DBService()

    # Mock client to always fail
    with patch.object(
        db.client.table('messages'),
        'insert',
        side_effect=ConnectionError("Network timeout")
    ):
        # Should raise after 3 attempts
        with pytest.raises(ConnectionError):
            db.save_message(123, 456, 'user', 'test message')

def test_ai_retry_on_rate_limit():
    """Test that AI operations retry on rate limit"""
    ai = AIService()

    call_count = [0]

    def rate_limited_call(*args, **kwargs):
        call_count[0] += 1
        if call_count[0] < 2:
            raise RateLimitError("Rate limit exceeded", response=Mock(), body={})
        return Mock(content=[Mock(text="Summary")])

    with patch.object(ai.client.messages, 'create', side_effect=rate_limited_call):
        result = ai.generate_summary([], {'system_prompt': 'test'}, {})

    # Должно быть 2 попытки
    assert call_count[0] == 2

def test_retry_exponential_backoff():
    """Test that retry uses exponential backoff"""
    import time
    db = DBService()

    call_times = []

    def failing_insert(*args, **kwargs):
        call_times.append(time.time())
        if len(call_times) < 3:
            raise ConnectionError("Timeout")
        return Mock(data=[{'id': 1}])

    with patch.object(db.client.table('messages'), 'insert', side_effect=failing_insert):
        db.save_message(123, 456, 'user', 'test')

    # Проверяем что интервалы растут экспоненциально
    if len(call_times) >= 3:
        interval1 = call_times[1] - call_times[0]
        interval2 = call_times[2] - call_times[1]

        # Второй интервал должен быть больше первого
        assert interval2 > interval1, "Backoff should be exponential"
```

#### Как проверить:
```bash
# 1. Установи зависимости
pip install tenacity==8.2.3

# 2. Запусти тесты
pytest tests/integration/test_retry_logic.py -v

# 3. Проверь что retry работает в production
# Временно сделай DB unavailable (отключи Supabase в dashboard на 10 сек)
# Отправь команду боту - должна быть retry попытка в логах

# 4. Проверь логи - должны быть записи "Retrying..."
# Vercel Dashboard → Logs → Search "Retrying"
```

#### Критерии успеха:
- [ ] `tenacity` добавлен в requirements
- [ ] `utils/retry.py` создан
- [ ] `@db_retry` добавлен ко всем DB методам
- [ ] `@ai_retry` добавлен ко всем AI методам
- [ ] Timeouts установлены на HTTP clients
- [ ] Тесты проходят
- [ ] Retry работает при network errors
- [ ] Коммит: `git commit -m "fix: add retry logic for DB and AI calls"`

---

### ШАГ 10: Connection Pooling отсутствует

**Приоритет:** 🔴 КРИТИЧНО
**Риск:** Resource leak, медленные запросы
**Файлы:** `services/db_service.py`

#### Описание проблемы:
```python
# services/db_service.py:17-22
class DBService:
    def __init__(self):
        self.client = create_client(...)  # Новый client при каждом DBService()
```

При каждом `DBService()` создаётся новый Supabase client:
- Новое TCP connection
- Новая аутентификация
- Memory leak (старые connections не закрываются)

**В serverless это особенно критично** - каждый webhook создаёт новый client.

#### Как исправить:

**1. Создай singleton для Supabase client в `services/db_service.py`:**

```python
# services/db_service.py - В НАЧАЛЕ ФАЙЛА, ДО класса DBService

import logging
from supabase import create_client, Client
from supabase.lib.client_options import ClientOptions
import config

logger = logging.getLogger(__name__)

# ===== SINGLETON SUPABASE CLIENT =====
_supabase_client: Client = None

def get_supabase_client() -> Client:
    """
    Get or create Supabase client (Singleton pattern)

    In serverless, this keeps connection alive between requests
    in the same worker instance.
    """
    global _supabase_client

    if _supabase_client is None:
        logger.info("Creating new Supabase client (singleton)")
        _supabase_client = create_client(
            config.SUPABASE_URL,
            config.SUPABASE_KEY,
            options=ClientOptions(
                headers={
                    "Connection": "keep-alive",
                    "Keep-Alive": "timeout=30, max=100"
                },
                timeout=10.0
            )
        )

    return _supabase_client

# ===== END SINGLETON =====


class DBService:
    """Database service with connection pooling"""

    def __init__(self):
        # Используем singleton вместо создания нового client
        self.client = get_supabase_client()

    # ... rest of existing methods ...
```

**2. Добавь connection health check (опционально):**

```python
# services/db_service.py - после get_supabase_client()

def health_check_supabase() -> bool:
    """Check if Supabase connection is healthy"""
    try:
        client = get_supabase_client()
        # Простой query для проверки соединения
        result = client.table('personalities').select('id').limit(1).execute()
        return result is not None
    except Exception as e:
        logger.error(f"Supabase health check failed: {e}")
        return False
```

**3. Добавь cleanup при graceful shutdown (для non-serverless):**

```python
# services/db_service.py - в конце файла

import atexit

def cleanup_supabase_client():
    """Cleanup Supabase client on shutdown"""
    global _supabase_client
    if _supabase_client is not None:
        logger.info("Cleaning up Supabase client")
        # Supabase client doesn't have explicit close(), но можем обнулить
        _supabase_client = None

# Регистрируем cleanup
atexit.register(cleanup_supabase_client)
```

**4. Аналогично для AI service (опционально):**

```python
# services/ai_service.py - сделай то же самое

_anthropic_client = None

def get_anthropic_client():
    """Get or create Anthropic client (Singleton)"""
    global _anthropic_client

    if _anthropic_client is None:
        logger.info("Creating new Anthropic client (singleton)")
        _anthropic_client = anthropic.Anthropic(
            api_key=config.ANTHROPIC_API_KEY,
            timeout=30.0,
            max_retries=0
        )

    return _anthropic_client


class AIService:
    def __init__(self):
        self.client = get_anthropic_client()
        self.model = config.ANTHROPIC_MODEL
```

#### Тест для проверки:

**Создай файл:** `tests/unit/test_connection_pooling.py`

```python
import pytest
from services.db_service import DBService, get_supabase_client, _supabase_client

def test_supabase_client_is_singleton():
    """Test that Supabase client is reused (singleton)"""
    # Первый вызов
    client1 = get_supabase_client()

    # Второй вызов
    client2 = get_supabase_client()

    # Должен быть ОДИН И ТОТ ЖЕ объект
    assert client1 is client2, "Supabase client should be singleton!"

def test_db_service_reuses_client():
    """Test that multiple DBService instances share client"""
    db1 = DBService()
    db2 = DBService()

    # Оба должны использовать один и тот же client
    assert db1.client is db2.client, "DBService instances should share client!"

def test_connection_pooling_performance():
    """Test that connection pooling improves performance"""
    import time

    # Первое создание (cold start)
    start1 = time.time()
    db1 = DBService()
    time1 = time.time() - start1

    # Второе создание (должно быть быстрее)
    start2 = time.time()
    db2 = DBService()
    time2 = time.time() - start2

    # Второе создание должно быть ЗНАЧИТЕЛЬНО быстрее
    assert time2 < time1 / 2, \
        f"Connection pooling should be faster! time1={time1:.4f}, time2={time2:.4f}"

def test_health_check():
    """Test Supabase health check"""
    from services.db_service import health_check_supabase

    is_healthy = health_check_supabase()

    assert is_healthy is True, "Supabase should be healthy"

@pytest.mark.benchmark
def test_connection_pooling_under_load(benchmark):
    """Benchmark: connection pooling vs new connections"""

    def create_db_service():
        db = DBService()
        # Simulate query
        return db

    # Benchmark должен показать что последующие вызовы быстрее
    result = benchmark(create_db_service)
```

#### Как проверить:
```bash
# 1. Запусти тесты
pytest tests/unit/test_connection_pooling.py -v

# 2. Проверь логи - должно быть ОДНО сообщение "Creating new Supabase client"
# При запуске нескольких команд

# 3. Benchmark (опционально)
pip install pytest-benchmark
pytest tests/unit/test_connection_pooling.py::test_connection_pooling_under_load --benchmark-only

# 4. Мониторинг connections в Supabase
# Supabase Dashboard → Settings → Database → Connection pooling
# Должно быть меньше активных connections после фикса
```

#### Критерии успеха:
- [ ] Singleton pattern реализован
- [ ] `get_supabase_client()` функция создана
- [ ] `DBService` использует singleton
- [ ] Health check добавлен
- [ ] Тесты проходят
- [ ] В логах только ОДНО "Creating new Supabase client"
- [ ] Performance улучшен (benchmark)
- [ ] Коммит: `git commit -m "fix: implement connection pooling for Supabase"`

---

## 🟠 ВАЖНЫЕ ПРОБЛЕМЫ (В ТЕЧЕНИЕ НЕДЕЛИ)

### ШАГ 11: Auto-cleanup при каждом save_message

**Приоритет:** 🟠 ВАЖНО
**Риск:** Performance degradation
**Файлы:** `services/db_service.py`

#### Описание проблемы:
```python
# services/db_service.py:46-54
def save_message(self, ...):
    # Save message
    ...
    # Auto-cleanup OLD messages - КАЖДЫЙ РАЗ!
    self._cleanup_old_messages(chat_id)
```

Cleanup запускается при **КАЖДОМ** сохранении сообщения:
- DELETE query при каждом сообщении
- Лишняя нагрузка на БД
- Медленнее обработка webhook

#### Как исправить:

**1. Замени auto-cleanup на probabilistic cleanup:**

```python
# services/db_service.py - в save_message()

import random

def save_message(self, chat_id: int, user_id: int, username: str, message_text: str):
    """Save message to database with probabilistic cleanup"""

    # ... existing save code ...

    # ===== БЫЛО (МЕДЛЕННО): =====
    # self._cleanup_old_messages(chat_id)

    # ===== СТАЛО (БЫСТРО): =====
    # Cleanup только с вероятностью 1% (1 из 100 сообщений)
    if random.random() < 0.01:
        logger.debug(f"Running probabilistic cleanup for chat {chat_id}")
        self._cleanup_old_messages(chat_id)
    # ===== END =====
```

**2. Или используй background task (для non-serverless):**

```python
# services/db_service.py - добавь метод

import threading
from datetime import datetime, timedelta

_last_cleanup = {}  # {chat_id: datetime}
_cleanup_lock = threading.Lock()

def save_message(self, chat_id: int, user_id: int, username: str, message_text: str):
    """Save message with background cleanup"""

    # ... existing save code ...

    # Cleanup не чаще 1 раза в час для каждого чата
    with _cleanup_lock:
        last = _last_cleanup.get(chat_id)
        should_cleanup = (
            last is None or
            (datetime.now() - last) > timedelta(hours=1)
        )

        if should_cleanup:
            _last_cleanup[chat_id] = datetime.now()

            # Запускаем cleanup в фоне (не блокирует webhook)
            thread = threading.Thread(
                target=self._cleanup_old_messages,
                args=(chat_id,),
                daemon=True
            )
            thread.start()
```

**3. Добавь manual cleanup command (для админов):**

```python
# modules/admin.py - добавь команду

async def cleanup_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Manual cleanup old messages (admin only)"""
    user_id = update.effective_user.id

    if user_id not in config.ADMIN_USER_IDS:
        await update.message.reply_text("❌ Admin only")
        return

    db = DBService()

    # Cleanup all chats
    await update.message.reply_text("🔄 Starting cleanup...")

    # Get all chats
    chats = db.client.table('chat_metadata').select('chat_id').execute()

    cleaned = 0
    for chat in chats.data:
        deleted = db._cleanup_old_messages(chat['chat_id'])
        cleaned += deleted

    await update.message.reply_text(
        f"✅ Cleanup complete!\n"
        f"Deleted {cleaned} old messages from {len(chats.data)} chats"
    )

# Регистрация:
# application.add_handler(CommandHandler('cleanup', cleanup_command))
```

#### Тест для проверки:

**Создай файл:** `tests/unit/test_cleanup_performance.py`

```python
import pytest
import time
from services.db_service import DBService
from unittest.mock import patch

def test_cleanup_not_called_every_time():
    """Test that cleanup is not called for every message"""
    db = DBService()

    cleanup_calls = [0]

    def mock_cleanup(chat_id):
        cleanup_calls[0] += 1

    with patch.object(db, '_cleanup_old_messages', side_effect=mock_cleanup):
        # Сохраняем 100 сообщений
        for i in range(100):
            db.save_message(123, 456, 'user', f'message {i}')

    # Cleanup должен вызваться ~1 раз (probabilistic 1%)
    assert cleanup_calls[0] <= 5, \
        f"Cleanup called {cleanup_calls[0]} times, expected ~1-2"

def test_save_message_performance_without_cleanup():
    """Test that save_message is fast without cleanup"""
    db = DBService()

    # Mock cleanup to do nothing
    with patch.object(db, '_cleanup_old_messages', return_value=0):
        start = time.time()

        # Сохраняем 10 сообщений
        for i in range(10):
            db.save_message(123, 456, 'user', f'test {i}')

        elapsed = time.time() - start

    # Должно быть быстро (<1 секунда для 10 сообщений)
    assert elapsed < 1.0, f"save_message too slow: {elapsed:.2f}s"

@pytest.mark.benchmark
def test_cleanup_frequency(benchmark):
    """Benchmark cleanup frequency"""
    db = DBService()

    def save_messages():
        for i in range(100):
            db.save_message(999, 111, 'user', f'msg {i}')

    # Benchmark должен показать что cleanup вызывается редко
    benchmark(save_messages)
```

#### Как проверить:
```bash
# 1. Запусти тесты
pytest tests/unit/test_cleanup_performance.py -v

# 2. Проверь логи - "Running probabilistic cleanup" должно быть редко
# Отправь 100 сообщений боту, проверь сколько раз cleanup запустился

# 3. Benchmark
pytest tests/unit/test_cleanup_performance.py::test_cleanup_frequency --benchmark-only

# 4. Проверь DB performance
# Supabase Dashboard → Performance → Query Stats
# DELETE queries должно быть меньше после фикса
```

#### Критерии успеха:
- [ ] Probabilistic cleanup реализован (1% вероятность)
- [ ] Или background cleanup (1 раз в час)
- [ ] Manual cleanup command добавлен
- [ ] Тесты проходят
- [ ] Performance улучшен (меньше DELETE queries)
- [ ] Коммит: `git commit -m "perf: optimize message cleanup frequency"`

---

*Продолжение в следующем разделе...*

---

## 📝 ДОПОЛНИТЕЛЬНЫЕ РЕСУРСЫ

### Создание requirements-dev.txt

**Создай файл:** `requirements-dev.txt`

```
# Testing
pytest==7.4.3
pytest-asyncio==0.21.1
pytest-cov==4.1.0
pytest-benchmark==4.0.0
pytest-mock==3.12.0

# Code quality
flake8==6.1.0
black==23.12.1
mypy==1.7.1
isort==5.13.2

# Security scanning
bandit==1.7.5
safety==2.3.5

# Utilities
ipython==8.18.1
httpx==0.27.2
```

### Pre-commit hooks

**Создай файл:** `.pre-commit-config.yaml`

```yaml
repos:
  - repo: https://github.com/pre-commit/pre-commit-hooks
    rev: v4.5.0
    hooks:
      - id: trailing-whitespace
      - id: end-of-file-fixer
      - id: check-yaml
      - id: check-added-large-files
      - id: check-merge-conflict

  - repo: https://github.com/psf/black
    rev: 23.12.1
    hooks:
      - id: black
        language_version: python3.11

  - repo: https://github.com/PyCQA/flake8
    rev: 6.1.0
    hooks:
      - id: flake8
        args: ['--max-line-length=100', '--ignore=E203,W503']

  - repo: https://github.com/PyCQA/bandit
    rev: 1.7.5
    hooks:
      - id: bandit
        args: ['-ll']
        files: .py$

  - repo: https://github.com/Yelp/detect-secrets
    rev: v1.4.0
    hooks:
      - id: detect-secrets
        args: ['--baseline', '.secrets.baseline']
```

### GitHub Actions CI/CD

**Создай файл:** `.github/workflows/test.yml`

```yaml
name: Tests

on:
  push:
    branches: [main, develop]
  pull_request:
    branches: [main]

jobs:
  test:
    runs-on: ubuntu-latest

    steps:
      - uses: actions/checkout@v3

      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.11'

      - name: Install dependencies
        run: |
          pip install -r requirements.txt
          pip install -r requirements-dev.txt

      - name: Run linters
        run: |
          flake8 . --count --select=E9,F63,F7,F82 --show-source --statistics
          black --check .

      - name: Run security checks
        run: |
          bandit -r . -ll

      - name: Run tests
        env:
          SECRET_KEY: test_secret_key_32_chars_long_!
          TELEGRAM_BOT_TOKEN: test_token
          TELEGRAM_WEBHOOK_SECRET: test_webhook_secret
          ANTHROPIC_API_KEY: test_api_key
          SUPABASE_URL: https://test.supabase.co
          SUPABASE_KEY: test_key
        run: |
          pytest tests/ --cov=. --cov-report=xml --cov-report=html

      - name: Check coverage
        run: |
          coverage=$(pytest --cov=. --cov-report=term | grep TOTAL | awk '{print $4}' | sed 's/%//')
          if [ "${coverage}" -lt 60 ]; then
            echo "Coverage ${coverage}% is below 60%"
            exit 1
          fi

      - name: Upload coverage
        uses: codecov/codecov-action@v3
        with:
          file: ./coverage.xml
```

---

## 🎯 ПРОГРЕСС TRACKER

### Критические баги:
- [ ] ШАГ 1: SQL Injection
- [ ] ШАГ 2: Дефолтный SECRET_KEY
- [ ] ШАГ 3: Race Condition
- [ ] ШАГ 4: Webhook Verification
- [ ] ШАГ 5: Cache TTL Bug
- [ ] ШАГ 6: YooKassa Async
- [ ] ШАГ 7: Idempotency Check
- [ ] ШАГ 8: Signature Logging
- [ ] ШАГ 9: Retry Logic
- [ ] ШАГ 10: Connection Pooling

### Важные проблемы:
- [ ] ШАГ 11: Cleanup Performance
- [ ] ШАГ 12-18: (будут добавлены)

---

**Версия документа:** 1.0
**Последнее обновление:** 2025-11-18
**Статус:** 10 критических шагов готовы

---

## 💬 КАК РАБОТАТЬ С ЭТИМ ДОКУМЕНТОМ

### В новом чате с Claude:

```
Привет! Я работаю над исправлением багов.
Открой файл SECURITY_FIXES.md и сделай ШАГ 1.

Создай все необходимые файлы:
1. Примени фикс
2. Создай тесты
3. Запусти тесты
4. Создай коммит

Когда закончишь - отметь чекбокс ✅ в документе.
```

Claude выполнит весь шаг автоматически!
