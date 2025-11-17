# 🚀 Шаг 8: Деплой и тестирование

**Дата:** 2025-11-17
**Что сделано:** Реализована система лимитов на кастомные личности

---

## ✅ Что реализовано

### 1. Логика лимитов (subscription.py)
- `get_custom_personality_limit()` - определяет сколько личностей доступно
  - Free: 0
  - Free + Group: 1
  - Pro: 3
  - Pro + Group: 4

- `can_create_custom_personality()` - проверяет можно ли создать личность
  - Возвращает детальную информацию о причине отказа
  - Показывает что нужно (группа или Pro)

### 2. Подсчет активных личностей (db_service.py)
- `get_active_custom_personalities_count()` - считает созданные личности
- Учитывает только активные (`is_active = true`)

### 3. Проверка при создании (personalities.py)
- Встроена проверка в обработчик "create_start"
- Показывает понятные сообщения пользователю
- Удалена старая проверка (через `MAX_CUSTOM_PERSONALITIES_PER_USER`)

### 4. Маркировка бонусных личностей (db_service.py)
- Добавлен параметр `is_group_bonus` в `create_personality()`
- Автоматически определяется на основе тарифа:
  - Free → `is_group_bonus = true` (это бонус за группу)
  - Pro → `is_group_bonus = false` (обычная личность)

---

## 📦 Перед деплоем

### 1. Убедись что миграции применены

**В Supabase SQL Editor выполни:**

```sql
-- Проверить что поле is_group_bonus существует
SELECT column_name, data_type, column_default
FROM information_schema.columns
WHERE table_name = 'personalities'
  AND column_name = 'is_group_bonus';

-- Должно вернуть:
-- column_name: is_group_bonus
-- data_type: boolean
-- column_default: false
```

Если поле НЕ существует, выполни миграцию:
```sql
ALTER TABLE personalities ADD COLUMN is_group_bonus BOOLEAN DEFAULT FALSE;
```

### 2. Проверь environment variables в Vercel

Должны быть установлены:
- `PROJECT_TELEGRAM_GROUP_ID` - ID твоей Telegram группы
- Все остальные переменные из предыдущих шагов

### 3. Commit и push изменений

```bash
# Проверь статус
git status

# Добавь изменённые файлы
git add services/subscription.py
git add services/db_service.py
git add modules/personalities.py
git add TESTING_STEP8_CUSTOM_PERSONALITIES.md
git add STEP8_DEPLOYMENT_GUIDE.md
git add TODO_MONETIZATION_v2.1.md

# Commit
git commit -m "feat(monetization): Implement Step 8 - Custom personalities limit system

- Add get_custom_personality_limit() to determine user's personality slots
- Add can_create_custom_personality() with detailed reason codes
- Integrate limit checking into personality creation flow
- Add is_group_bonus field to track group bonus personalities
- Automatically mark personalities based on user tier (Free=bonus, Pro=normal)
- Remove old MAX_CUSTOM_PERSONALITIES_PER_USER check
- Create comprehensive testing guide with 7 test scenarios"

# Push
git push -u origin claude/monetization-step-8-01WvhrdNWDZmzWt9fy72kQY8
```

---

## 🧪 После деплоя - тестирование

### Quick test (5 минут)

**Цель:** Быстро проверить что основное работает

1. **Отправь боту `/lichnost`**

2. **Нажми "➕ Создать личность"**

3. **Если ты Free без группы:**
   - Должно показать: "Вступи в группу или купи Pro"
   - ✅ Работает!

4. **Если ты Pro:**
   - Должно начаться создание личности
   - ✅ Работает!

5. **Проверь что личность создалась с правильным `is_group_bonus`:**
   ```sql
   SELECT name, is_group_bonus, created_by_user_id
   FROM personalities
   WHERE created_by_user_id = ТВОЙ_USER_ID
   ORDER BY created_at DESC
   LIMIT 1;
   ```

### Полное тестирование (30-60 минут)

**Следуй инструкции:**
[TESTING_STEP8_CUSTOM_PERSONALITIES.md](./TESTING_STEP8_CUSTOM_PERSONALITIES.md)

Эта инструкция включает:
- ✅ 7 детальных сценариев тестирования
- ✅ SQL-запросы для проверки
- ✅ Примеры ожидаемых результатов
- ✅ Инструкции по отладке если что-то не работает

---

## 🔍 Как проверить что всё применилось

### 1. Проверь логи Vercel после деплоя

```bash
vercel logs --follow
```

Ищи ошибки импорта или запуска.

### 2. Проверь что subscription service инициализируется

В логах должна быть строка при запуске бота (если есть логирование инициализации).

### 3. Отправь тестовую команду

```
/lichnost
```

Если показывается меню личностей - всё работает!

---

## 🐛 Troubleshooting

### Проблема: "NameError: name 'get_subscription_service' is not defined"

**Причина:** Не импортирован модуль в personalities.py

**Решение:**
Проверь что в `modules/personalities.py` есть импорт:
```python
from services.subscription import get_subscription_service
```

---

### Проблема: "RuntimeError: Subscription service not initialized"

**Причина:** Subscription service не инициализирован при старте

**Решение:**
Проверь что в `api/index.py` есть инициализация:
```python
from services.subscription import init_subscription_service

# После создания db_service:
subscription_service = init_subscription_service(db_service)
```

---

### Проблема: Проверка лимитов не срабатывает

**Диагностика:**
1. Открой Vercel logs
2. Найди момент когда нажимаешь "➕ Создать личность"
3. Ищи ошибки или exceptions

**Возможные причины:**
- Не вызывается `can_create_custom_personality()`
- Ошибка в определении тарифа (`get_user_tier()`)
- Кеш группы устарел

---

### Проблема: `is_group_bonus` всегда `false`

**Диагностика:**
```sql
SELECT name, is_group_bonus, created_by_user_id
FROM personalities
WHERE created_by_user_id = ТВОЙ_USER_ID
  AND is_custom = true
ORDER BY created_at DESC;
```

**Возможные причины:**
- Не передается параметр в `create_personality()`
- Тариф определяется как Pro вместо Free
- Миграция БД не применена

**Решение:**
Проверь что в `personalities.py:342-345` определяется тариф:
```python
tier = await subscription_service.get_user_tier(user.id)
is_group_bonus = (tier == 'free')
```

---

## 📋 Следующие шаги

После успешного тестирования Шага 8:

### Опция 1: Протестировать сейчас
- Следуй [TESTING_STEP8_CUSTOM_PERSONALITIES.md](./TESTING_STEP8_CUSTOM_PERSONALITIES.md)
- Пройди все 7 сценариев
- Отметь тесты в TODO_MONETIZATION_v2.1.md

### Опция 2: Перейти к Шагу 9
**Шаг 9: Софт-блокировка бонусной личности**

**Примечание:** Шаг 9 уже частично реализован в Шаге 7!
- `block_group_bonus_personalities()` - уже есть
- `unblock_group_bonus_personalities()` - уже есть
- Обработчик в `handle_group_membership_change()` - уже вызывает блокировку

**Что осталось:**
- Добавить проверку `is_blocked` при отображении личностей в меню
- Добавить проверку `is_blocked` при выборе личности
- Тестирование блокировки/разблокировки

### Опция 3: Перейти к Шагу 4 (команды /premium и /mystatus)
Если хочешь сначала сделать user-facing функции для покупки Pro.

---

## 💡 Полезные команды для тестирования

### Сбросить свой тариф на Free
```sql
DELETE FROM subscriptions WHERE user_id = ТВОЙ_USER_ID;
```

### Активировать Pro на 30 дней
```bash
/grantpro ТВОЙ_USER_ID 30
```

### Удалить все свои кастомные личности (начать заново)
```sql
DELETE FROM personalities
WHERE created_by_user_id = ТВОЙ_USER_ID
  AND is_custom = true;
```

### Проверить текущий статус
```sql
-- Тариф
SELECT tier, is_active, expires_at FROM subscriptions WHERE user_id = ТВОЙ_USER_ID;

-- Группа
SELECT is_member FROM group_membership_cache WHERE user_id = ТВОЙ_USER_ID;

-- Личности
SELECT name, is_group_bonus, is_blocked FROM personalities WHERE created_by_user_id = ТВОЙ_USER_ID;
```

---

**Готово! Шаг 8 реализован. Время тестировать! 🎉**
