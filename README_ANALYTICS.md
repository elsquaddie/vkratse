# 📊 Analytics System - Quick Start

## Что это?

Полная система аналитики для Telegram бота, которая автоматически отслеживает:
- ✅ Все клики по кнопкам (inline keyboard)
- ✅ Использование команд (/start, /summary, /chat, etc.)
- ✅ Сообщения пользователей (в direct chat)
- ✅ AI генерации (саммари, судейство, ответы)
- ✅ Ошибки и edge cases

## 🚀 Быстрый старт

### 1. Установка (5 минут)

```bash
# 1. Применить SQL миграцию в Supabase
# Откройте Supabase → SQL Editor → New query
# Скопируйте содержимое файла:
sql/migrations/003_button_analytics.sql

# 2. Обновить api/index.py
# См. детали в ANALYTICS_INTEGRATION_GUIDE.md
# Краткая версия: добавить импорт и middleware
```

### 2. Проверка работы

```bash
# 1. Deploy на Vercel
vercel deploy --prod

# 2. Отправить /start боту в Telegram

# 3. Проверить в Supabase → Table Editor → button_analytics
# Должна появиться запись с action_name = '/start'
```

### 3. Анализ данных

```sql
-- В Supabase SQL Editor запустите:

-- Топ-10 кнопок за неделю
SELECT * FROM get_top_actions(7, 10);

-- Популярные кнопки по дням
SELECT * FROM popular_buttons_7d
ORDER BY date DESC, total_clicks DESC;

-- Воронка конверсии
SELECT * FROM conversion_funnel;
```

## 📂 Файлы системы

```
vkratse/
├── sql/
│   ├── migrations/
│   │   └── 003_button_analytics.sql      # 🆕 БД миграция
│   └── analytics_queries.sql             # 🆕 27 готовых SQL запросов
│
├── services/
│   └── analytics_service.py              # 🆕 Сервис для трекинга
│
├── utils/
│   └── analytics_middleware.py           # 🆕 Автоматический трекинг
│
├── ANALYTICS_INTEGRATION_GUIDE.md        # 🆕 Полная документация
└── README_ANALYTICS.md                   # 🆕 Этот файл
```

## 📊 Что отслеживается?

### 1. Клики по кнопкам (Button Clicks)

**Автоматически логируется:**
- Название действия (`action_name`): `direct_chat`, `select_personality`, etc.
- Текст кнопки (`button_text`): "💬 Общаться напрямую"
- Callback data (`callback_data`): оригинальные данные с HMAC
- Пользователь, чат, время

**Примеры кнопок:**
- "💬 Общаться напрямую" → `direct_chat`
- "🎭 Быдлан" → `select_personality:bydlan`
- "📝 Сделать саммари" → `group_summary`

### 2. Команды (Commands)

**Автоматически логируется:**
- Команда (`action_name`): `/start`, `/summary`, `/chat`, etc.
- Пользователь, чат, время

### 3. AI Генерации (AI Generations)

**Нужно добавить вручную в модулях:**
```python
from utils.analytics_middleware import track_ai_generation

await track_ai_generation(
    context=context,
    user_id=user.id,
    chat_id=chat.id,
    generation_type='summary',  # 'summary', 'judge', 'chat_response'
    personality='bydlan',
    metadata={'messages_count': 50}
)
```

См. примеры в `ANALYTICS_INTEGRATION_GUIDE.md` → "Трекинг AI генераций в модулях"

### 4. Ошибки (Errors)

**Автоматически (если добавить в error handler):**
```python
from utils.analytics_middleware import track_error

await track_error(
    context=context,
    update=update,
    error_type='rate_limit_exceeded',
    error_message=str(error)
)
```

## 📈 Полезные запросы

### Топ-10 кнопок за неделю
```sql
SELECT
  action_name,
  button_text,
  COUNT(*) as clicks,
  COUNT(DISTINCT user_id) as users
FROM button_analytics
WHERE action_type = 'button_click'
  AND created_at >= NOW() - INTERVAL '7 days'
GROUP BY action_name, button_text
ORDER BY clicks DESC
LIMIT 10;
```

### Активность по часам (найти пиковые часы)
```sql
SELECT
  EXTRACT(HOUR FROM created_at) as hour,
  COUNT(*) as actions,
  COUNT(DISTINCT user_id) as users
FROM button_analytics
WHERE created_at >= NOW() - INTERVAL '7 days'
GROUP BY hour
ORDER BY hour;
```

### Путь пользователя (User Journey)
```sql
SELECT
  created_at,
  action_type,
  action_name,
  button_text
FROM button_analytics
WHERE user_id = 123456  -- Замените на реальный user_id
  AND created_at >= NOW() - INTERVAL '7 days'
ORDER BY created_at ASC;
```

### Воронка: /start → личность → первое сообщение
```sql
WITH users AS (
  SELECT DISTINCT user_id FROM button_analytics
  WHERE created_at >= NOW() - INTERVAL '30 days'
)
SELECT
  'Started bot' as step,
  COUNT(DISTINCT CASE WHEN action_name = '/start' THEN user_id END) as users
FROM button_analytics
WHERE user_id IN (SELECT user_id FROM users)
UNION ALL
SELECT
  'Selected personality',
  COUNT(DISTINCT CASE WHEN action_name LIKE '%personality%' THEN user_id END)
FROM button_analytics
WHERE user_id IN (SELECT user_id FROM users)
UNION ALL
SELECT
  'Sent message',
  COUNT(DISTINCT CASE WHEN action_type = 'message' THEN user_id END)
FROM button_analytics
WHERE user_id IN (SELECT user_id FROM users);
```

**Больше запросов:** См. `sql/analytics_queries.sql` (27 готовых запросов!)

## 🎯 Use Cases

### 1. Оптимизация UX
**Вопрос:** Какие кнопки игнорируют?
```sql
SELECT action_name, COUNT(*) FROM button_analytics
WHERE action_type = 'button_click'
GROUP BY action_name
ORDER BY COUNT(*) ASC
LIMIT 5;
```
→ Удалите или переместите непопулярные кнопки

### 2. A/B тестирование
**Вопрос:** Какая личность популярнее?
```sql
SELECT
  metadata->>'personality' as personality,
  COUNT(*) as usage
FROM button_analytics
WHERE action_type = 'ai_generation'
GROUP BY personality
ORDER BY usage DESC;
```

### 3. Retention анализ
**Вопрос:** Сколько пользователей возвращаются?
```sql
WITH user_cohorts AS (
  SELECT user_id, DATE(MIN(created_at)) as cohort_date
  FROM button_analytics
  GROUP BY user_id
)
SELECT
  cohort_date,
  COUNT(DISTINCT user_id) as new_users,
  COUNT(DISTINCT CASE
    WHEN DATE(created_at) > cohort_date + 7 THEN user_id
  END) as returned_after_7d
FROM button_analytics ba
JOIN user_cohorts uc ON ba.user_id = uc.user_id
WHERE cohort_date >= NOW() - INTERVAL '30 days'
GROUP BY cohort_date
ORDER BY cohort_date DESC;
```

### 4. Поиск багов
**Вопрос:** Какие ошибки происходят?
```sql
SELECT
  action_name,
  metadata->>'error_message' as error,
  COUNT(*) as count
FROM button_analytics
WHERE action_type = 'error'
  AND created_at >= NOW() - INTERVAL '7 days'
GROUP BY action_name, error
ORDER BY count DESC;
```

## 🔧 Интеграция в модули

### Пример: добавить трекинг в summaries.py

```python
# В начале файла
from utils.analytics_middleware import track_ai_generation

# В функции summary_personality_callback, после генерации саммари:
async def summary_personality_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # ... existing code ...

    # Generate summary
    summary = ai_service.generate_summary(...)

    # 🆕 Track AI generation
    await track_ai_generation(
        context=context,
        user_id=user.id,
        chat_id=chat.id,
        generation_type='summary',
        personality=personality_name,
        metadata={
            'messages_count': len(messages),
            'timeframe': timeframe
        }
    )

    # Send summary
    await query.message.reply_text(summary)
```

## 📊 Дашборды (опционально)

### Вариант 1: Supabase Dashboard
1. Откройте Supabase → Database → Tables → `button_analytics`
2. Используйте встроенные фильтры и графики

### Вариант 2: Metabase (рекомендуется)
1. Установите [Metabase](https://www.metabase.com/)
2. Подключите к Supabase PostgreSQL
3. Создайте дашборды из `analytics_queries.sql`

### Вариант 3: Google Data Studio
1. Установите [PostgreSQL коннектор](https://datastudio.google.com/datasources/create)
2. Подключите к Supabase
3. Создайте визуализации

### Вариант 4: Custom Dashboard
```python
# FastAPI endpoint для аналитики
@app.get("/analytics/summary")
async def get_analytics_summary():
    analytics = AnalyticsService(supabase_client)
    top_buttons = analytics.get_popular_buttons(days_back=7)
    return {"top_buttons": top_buttons}
```

## 🧹 Maintenance

### Очистка старых данных (> 90 дней)
```sql
-- Запускать раз в месяц
SELECT cleanup_old_analytics();
```

### Оптимизация производительности
```sql
-- Если запросы медленные, обновите статистику
ANALYZE button_analytics;
ANALYZE user_sessions;
```

### Размер таблицы
```sql
SELECT
  pg_size_pretty(pg_total_relation_size('button_analytics')) as size,
  COUNT(*) as rows
FROM button_analytics;
```

## 📚 Документация

- **Полная интеграция:** `ANALYTICS_INTEGRATION_GUIDE.md`
- **SQL запросы:** `sql/analytics_queries.sql`
- **Миграция БД:** `sql/migrations/003_button_analytics.sql`
- **Сервис:** `services/analytics_service.py`
- **Middleware:** `utils/analytics_middleware.py`

## ❓ FAQ

**Q: Аналитика не работает, что делать?**
A: Проверьте:
1. Миграция применена в Supabase?
2. Middleware добавлен в `api/index.py`?
3. Логи Vercel показывают "Analytics middleware registered"?
4. Таблица `button_analytics` существует?

**Q: Как посмотреть путь конкретного пользователя?**
A: См. запрос #23 в `sql/analytics_queries.sql`

**Q: Можно ли отключить аналитику?**
A: Да, просто закомментируйте middleware в `api/index.py`

**Q: Влияет ли аналитика на производительность?**
A: Минимально. Middleware работает в фоне и не блокирует основной флоу.

**Q: Хранятся ли личные данные?**
A: Нет. Мы логируем только метаданные (длина, тип, количество), но НЕ содержимое сообщений.

## 🚀 Следующие шаги

1. ✅ Примените миграцию БД
2. ✅ Обновите `api/index.py` (см. `ANALYTICS_INTEGRATION_GUIDE.md`)
3. ✅ Deploy на Vercel
4. ✅ Протестируйте: отправьте `/start` боту
5. ✅ Проверьте Supabase → `button_analytics`
6. ✅ Добавьте трекинг AI генераций в модули
7. 🎯 Создайте дашборд (Metabase или Data Studio)
8. 📊 Анализируйте данные и оптимизируйте UX!

---

**Готово!** 🎉 Теперь у вас полная аналитика всех взаимодействий с ботом.

Вопросы? См. `ANALYTICS_INTEGRATION_GUIDE.md` или `sql/analytics_queries.sql`
