# 🐛 Отладка Dry Run режима

## Что изменилось

Добавлено детальное логирование для отладки проблем с активацией подписки в dry_run режиме.

### ✅ Теперь логируется:

**В `modules/commands.py`:**
- `[DRY RUN] Processing card payment for user {user_id}` - начало обработки
- `[DRY RUN] Subscription created successfully for user {user_id}` - успех
- `[DRY RUN] Verification: subscription={...}` - верификация записи в БД
- `[DRY RUN] Failed to create subscription for user {user_id}` - ошибка

**В `services/db_service.py`:**
- Параметры перед upsert: `tier`, `duration`, `payment_method`, `expires_at`
- Данные для upsert: полный словарь
- Результат upsert из Supabase
- Полный traceback при ошибках (`exc_info=True`)

## 🔍 Как проверить что работает

### Шаг 1: Включи PAYMENT_DRY_RUN
```bash
# В Vercel Environment Variables:
PAYMENT_DRY_RUN=true
```

### Шаг 2: Попробуй активировать подписку
1. Открой бота
2. `/premium` → Купить Pro → выбери способ
3. Должно показать "Подписка активирована! (DRY RUN)"

### Шаг 3: Проверь логи в Vercel

Открой Vercel Dashboard → Function Logs → найди:

```
INFO: [DRY RUN] Processing Stars payment for user 123456789
INFO: Creating/updating subscription for user 123456789: tier=pro, duration=30 days, payment_method=stars_dryrun, expires_at=2025-...
INFO: Upserting data to subscriptions table: {'user_id': 123456789, 'tier': 'pro', ...}
INFO: Upsert result: [...]
INFO: Subscription created/updated successfully for user 123456789: pro, 30 days
INFO: [DRY RUN] Subscription created successfully for user 123456789
INFO: [DRY RUN] Verification: subscription={'user_id': 123456789, 'tier': 'pro', 'is_active': True, ...}
```

### Шаг 4: Проверь статус
```
/mystatus
```

Должно показывать:
```
📊 Твой статус

Тариф: 💎 Pro
Активен до: 2025-12-18
Осталось: 30 дней
```

## ❌ Что делать если не работает

### Проблема 1: Subscription = None в логах
```
INFO: [DRY RUN] Verification: subscription=None
```

**Причина:** Подписка не создалась в БД.

**Решение:**
1. Проверь логи выше - есть ли `Upsert result`?
2. Проверь таблицу `subscriptions` в Supabase:
   ```sql
   SELECT * FROM subscriptions WHERE user_id = YOUR_TELEGRAM_ID;
   ```
3. Если нет записи - проверь права доступа к таблице в Supabase
4. Проверь что в таблице нет ограничений (constraints) которые блокируют вставку

### Проблема 2: Ошибка в логах
```
ERROR: Error creating/updating subscription for 123456789: ...
```

**Решение:**
1. Смотри полный traceback в логах (теперь с `exc_info=True`)
2. Распространённые проблемы:
   - Таблица `subscriptions` не существует
   - Неправильные права доступа в Supabase
   - Неправильный формат данных
   - Проблемы с подключением к Supabase

### Проблема 3: /mystatus показывает Free, но в логах success
```
INFO: [DRY RUN] Subscription created successfully
```
Но `/mystatus` → Free тариф

**Решение:**
1. Проверь таблицу в Supabase напрямую:
   ```sql
   SELECT user_id, tier, is_active, expires_at
   FROM subscriptions
   WHERE user_id = YOUR_TELEGRAM_ID;
   ```
2. Если запись есть и `is_active = true`:
   - Проблема в функции `get_user_tier()`
   - Проверь логи при вызове `/mystatus`
3. Если запись есть но `is_active = false`:
   - Подписка истекла или была отменена
   - Проверь `expires_at` - не в прошлом ли?

### Проблема 4: Таймаут или "Internal Server Error"

**Решение:**
1. Проверь что `SUPABASE_URL` и `SUPABASE_KEY` правильные
2. Проверь что таблица `subscriptions` существует
3. Проверь лимиты Supabase (free tier имеет ограничения)
4. Попробуй напрямую из SQL Editor в Supabase:
   ```sql
   INSERT INTO subscriptions (user_id, tier, is_active, payment_method, expires_at)
   VALUES (123456789, 'pro', true, 'test', NOW() + INTERVAL '30 days')
   ON CONFLICT (user_id) DO UPDATE SET
     tier = 'pro',
     is_active = true,
     expires_at = NOW() + INTERVAL '30 days';
   ```

## 🔧 Проверка таблицы Supabase

### Структура таблицы `subscriptions`
```sql
CREATE TABLE subscriptions (
    id SERIAL PRIMARY KEY,
    user_id BIGINT NOT NULL UNIQUE,
    tier VARCHAR(20) NOT NULL,
    started_at TIMESTAMP DEFAULT NOW(),
    expires_at TIMESTAMP,
    payment_method VARCHAR(50),
    transaction_id VARCHAR(255),
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_subscriptions_user ON subscriptions(user_id);
CREATE INDEX idx_subscriptions_expiry ON subscriptions(expires_at);
```

### Проверка прав доступа
В Supabase Dashboard → Table Editor → subscriptions → RLS (Row Level Security):

**Должны быть политики:**
- `Enable read access for all users` (SELECT)
- `Enable insert for authenticated users` (INSERT)
- `Enable update for authenticated users` (UPDATE)

Или отключи RLS для тестирования:
```sql
ALTER TABLE subscriptions DISABLE ROW LEVEL SECURITY;
```

## 📊 Полезные SQL запросы для отладки

### Проверить все подписки
```sql
SELECT
  user_id,
  tier,
  is_active,
  payment_method,
  expires_at,
  created_at,
  updated_at
FROM subscriptions
ORDER BY updated_at DESC
LIMIT 10;
```

### Найти конкретного пользователя
```sql
SELECT * FROM subscriptions
WHERE user_id = YOUR_TELEGRAM_ID;
```

### Удалить тестовую подписку
```sql
DELETE FROM subscriptions
WHERE user_id = YOUR_TELEGRAM_ID;
```

### Активировать подписку вручную
```sql
INSERT INTO subscriptions (user_id, tier, is_active, payment_method, expires_at)
VALUES (YOUR_TELEGRAM_ID, 'pro', true, 'manual', NOW() + INTERVAL '30 days')
ON CONFLICT (user_id) DO UPDATE SET
  tier = 'pro',
  is_active = true,
  expires_at = NOW() + INTERVAL '30 days',
  updated_at = NOW();
```

## 📞 Если ничего не помогло

1. Скопируй полные логи из Vercel (последние 50-100 строк)
2. Сделай скриншот вывода `/mystatus`
3. Экспортируй данные из таблицы `subscriptions` (CSV)
4. Проверь переменные окружения в Vercel:
   - `PAYMENT_DRY_RUN=true`
   - `SUPABASE_URL` - правильный?
   - `SUPABASE_KEY` - правильный?

## ✅ После исправления

1. Redeploy бота в Vercel
2. Удали старые тестовые записи:
   ```sql
   DELETE FROM subscriptions WHERE payment_method LIKE '%dryrun%';
   ```
3. Попробуй снова активировать подписку
4. Проверь логи - теперь должны быть детальные

---

**Последнее обновление:** 2025-11-18

Полная документация: [TESTING_SUBSCRIPTION_CANCEL.md](TESTING_SUBSCRIPTION_CANCEL.md)
