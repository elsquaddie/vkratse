# ✅ Шаг 1: База данных и конфигурация - ЗАВЕРШЁН

**Дата:** 2025-11-17
**Прогресс:** 8/9 задач выполнено (89%)

---

## 📝 Что было сделано

### ✅ Созданы SQL-миграции:

1. **`003_create_subscriptions.sql`** - Таблица для подписок (free/pro)
2. **`004_create_usage_limits.sql`** - Таблица для отслеживания дневных лимитов
3. **`005_create_personality_usage.sql`** - Таблица для отслеживания использования личностей
4. **`006_create_group_membership_cache.sql`** - Кеш членства в группе проекта
5. **`007_add_personality_bonus_fields.sql`** - Добавление полей `is_group_bonus` и `is_blocked`

### ✅ Создан мастер-скрипт:

- **`apply_monetization_migrations.sql`** - Единый скрипт для применения всех миграций
- Включает верификацию создания всех таблиц
- Идемпотентный (безопасно запускать несколько раз)

### ✅ Обновлён config.py:

Добавлены новые параметры:
- `PROJECT_TELEGRAM_GROUP_ID` - ID группы проекта для бонуса
- `TIER_LIMITS` - Лимиты для тарифов Free и Pro
- `TRIBUTE_URL` - Ссылка на Tribute.to для донатов
- `ADMIN_USER_ID` - ID администратора для ручных операций
- `YOOKASSA_SHOP_ID` и `YOOKASSA_SECRET_KEY` - Для автоматических платежей

### ✅ Создана документация:

- **`README_MONETIZATION_MIGRATIONS.md`** - Подробные инструкции по применению миграций

---

## 🔍 ЧТО НУЖНО ПРОВЕРИТЬ СЕЙЧАС

### 1. Применить миграции в Supabase

**Шаги:**

1. Открыть **Supabase Dashboard** → **SQL Editor**
2. Создать новый запрос
3. Скопировать содержимое файла `sql/migrations/apply_monetization_migrations.sql`
4. Вставить в редактор
5. Нажать **"Run"** (или Ctrl/Cmd + Enter)
6. Проверить, что появилось сообщение: `"Monetization migrations applied successfully! ✓"`

---

### 2. Проверить созданные таблицы

Выполните в Supabase SQL Editor:

```sql
SELECT table_name
FROM information_schema.tables
WHERE table_schema = 'public'
  AND table_name IN (
    'subscriptions',
    'usage_limits',
    'personality_usage',
    'group_membership_cache'
  )
ORDER BY table_name;
```

**Ожидаемый результат:** Должны вернуться все 4 таблицы.

---

### 3. Проверить новые поля в personalities

Выполните:

```sql
SELECT column_name, data_type, column_default
FROM information_schema.columns
WHERE table_name = 'personalities'
  AND column_name IN ('is_group_bonus', 'is_blocked')
ORDER BY column_name;
```

**Ожидаемый результат:**
- `is_group_bonus` - boolean, default: false
- `is_blocked` - boolean, default: false

---

### 4. Добавить переменные окружения

**В файл `.env` (локально):**

```env
# Monetization settings
PROJECT_TELEGRAM_GROUP_ID=0  # TODO: Заменить на реальный ID группы
TRIBUTE_URL=https://tribute.to/your_bot_page  # TODO: Заменить на реальную ссылку
ADMIN_USER_ID=0  # TODO: Заменить на ваш Telegram ID

# Optional (для YooKassa)
YOOKASSA_SHOP_ID=
YOOKASSA_SECRET_KEY=
```

**В Vercel Dashboard:**

1. Перейти в **Settings** → **Environment Variables**
2. Добавить те же переменные для `Production`, `Preview`, `Development`
3. После добавления сделать **Redeploy**

---

### 5. Тестовая вставка данных (опционально)

Проверьте, что таблицы работают корректно:

```sql
-- Тестовая подписка
INSERT INTO subscriptions (user_id, tier)
VALUES (999999999, 'free')
ON CONFLICT (user_id) DO NOTHING;

SELECT * FROM subscriptions WHERE user_id = 999999999;

-- Тестовое использование
INSERT INTO usage_limits (user_id, messages_count)
VALUES (999999999, 5);

SELECT * FROM usage_limits WHERE user_id = 999999999;

-- Удалить тестовые данные
DELETE FROM subscriptions WHERE user_id = 999999999;
DELETE FROM usage_limits WHERE user_id = 999999999;
```

**Ожидаемый результат:** Все запросы выполняются без ошибок.

---

## 📊 Структура базы данных

После применения миграций у вас будут следующие таблицы:

```
┌─────────────────────┐
│   subscriptions     │ ← Тарифы пользователей
├─────────────────────┤
│ user_id (PK)        │
│ tier (free/pro)     │
│ expires_at          │
│ payment_method      │
│ is_active           │
└─────────────────────┘

┌─────────────────────┐
│   usage_limits      │ ← Дневные лимиты
├─────────────────────┤
│ user_id             │
│ date                │
│ messages_count      │
│ summaries_dm_count  │
│ judge_count         │
└─────────────────────┘

┌─────────────────────┐
│ personality_usage   │ ← Использование личностей
├─────────────────────┤
│ user_id             │
│ personality_name    │
│ date                │
│ summary_count       │
│ chat_count          │
│ judge_count         │
└─────────────────────┘

┌─────────────────────┐
│ group_membership_   │ ← Кеш членства в группе
│      cache          │
├─────────────────────┤
│ user_id (PK)        │
│ is_member           │
│ checked_at          │
└─────────────────────┘

┌─────────────────────┐
│   personalities     │ ← Обновлённая таблица
├─────────────────────┤
│ ... (existing)      │
│ is_group_bonus ✨   │ NEW
│ is_blocked ✨       │ NEW
└─────────────────────┘
```

---

## ⏭️ Следующий шаг

После успешной проверки всех пунктов:

**Переходите к Шагу 2: Сервисы для определения статуса пользователя**

Файл: `TODO_MONETIZATION_v2.1.md` → Шаг 2 (задачи 2.1-2.6)

---

## 📂 Созданные файлы

```
sql/migrations/
├── 003_create_subscriptions.sql
├── 004_create_usage_limits.sql
├── 005_create_personality_usage.sql
├── 006_create_group_membership_cache.sql
├── 007_add_personality_bonus_fields.sql
├── apply_monetization_migrations.sql
└── README_MONETIZATION_MIGRATIONS.md

config.py (обновлён)
TODO_MONETIZATION_v2.1.md (обновлён, 8/75 задач)
MONETIZATION_STEP1_SUMMARY.md (этот файл)
```

---

## ✅ Чек-лист для завершения Шага 1

- [ ] Применены все миграции в Supabase
- [ ] Проверено существование 4 новых таблиц
- [ ] Проверено добавление 2 новых полей в personalities
- [ ] Добавлены переменные окружения в `.env`
- [ ] Добавлены переменные в Vercel Dashboard
- [ ] Выполнена тестовая вставка данных (опционально)

**Как только все пункты выполнены - можно переходить к Шагу 2!** 🚀

---

**Создано:** 2025-11-17
**Статус:** Шаг 1 завершён на 89% (осталась только проверка в Supabase)
