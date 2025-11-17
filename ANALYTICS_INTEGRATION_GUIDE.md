# 📊 Analytics Integration Guide

## Обзор

Система аналитики автоматически отслеживает все взаимодействия пользователей с ботом:
- Клики по кнопкам (callback_query)
- Использование команд (/start, /summary, etc.)
- Сообщения в direct chat
- AI генерации (саммари, судейство, ответы)
- Ошибки

## 🔧 Установка

### 1. Применить SQL миграцию

Выполните в Supabase SQL Editor:

```sql
-- Запустите файл:
sql/migrations/003_button_analytics.sql
```

Это создаст:
- Таблицу `button_analytics` - детальное логирование
- Таблицу `user_sessions` - трекинг сессий
- Views для анализа (popular_buttons_7d, conversion_funnel, activity_by_hour)
- Функции для получения статистики

### 2. Обновить api/index.py

Добавьте импорт middleware в секцию импортов (после строки 85):

```python
# ================================================
# CHECKPOINT 5.5: Import analytics middleware
# ================================================
try:
    from utils.analytics_middleware import analytics_middleware
    analytics_imported = True
    verbose_log("✅ CHECKPOINT 5.5: analytics_middleware import successful")
except Exception as e:
    log(f"❌ CHECKPOINT 5.5 FAILED: analytics_middleware import error: {e}")
    analytics_imported = False
```

Затем в функции `create_bot_application()`, после строки 266 (`build()`), добавьте:

```python
    # Initialize analytics service in bot_data (AFTER build())
    from services.db_service import DBService
    from services.analytics_service import AnalyticsService

    db_service = DBService()
    app.bot_data['analytics_service'] = AnalyticsService(db_service.client)

    verbose_log("✅ Analytics service initialized in bot_data")

    # Add analytics middleware to ALL handlers (before any handler registration)
    if analytics_imported:
        async def wrapped_analytics_middleware(update: Update, context):
            """Wrapper to ensure analytics runs before handlers"""
            await analytics_middleware(update, context)

        # This will run analytics tracking before processing any update
        app.add_handler(
            MessageHandler(filters.ALL, wrapped_analytics_middleware),
            group=-1  # Run before all other handlers
        )
        app.add_handler(
            CallbackQueryHandler(wrapped_analytics_middleware),
            group=-1  # Run before all other handlers
        )
        verbose_log("✅ Analytics middleware registered")
```

**ВАЖНО:** Middleware должен быть добавлен ПЕРЕД регистрацией всех остальных handlers!

Полный diff для `api/index.py`:

```python
# После строки 85 (после импорта modules):
try:
    from utils.analytics_middleware import analytics_middleware
    analytics_imported = True
    verbose_log("✅ CHECKPOINT 5.5: analytics_middleware import successful")
except Exception as e:
    log(f"❌ CHECKPOINT 5.5 FAILED: analytics_middleware import error: {e}")
    analytics_imported = False

# В функции create_bot_application(), после строки 266:
def create_bot_application():
    """Create and configure a new bot Application instance"""
    if not bot_initialized or not modules_imported:
        raise RuntimeError("Cannot create bot application - imports failed")

    # Create persistence for ConversationHandler
    persistence = SupabasePersistence()

    app = Application.builder()\
        .token(config.TELEGRAM_BOT_TOKEN)\
        .persistence(persistence)\
        .build()

    # === ДОБАВИТЬ ЗДЕСЬ ===
    # Initialize analytics service in bot_data
    from services.db_service import DBService
    from services.analytics_service import AnalyticsService

    db_service = DBService()
    app.bot_data['analytics_service'] = AnalyticsService(db_service.client)

    verbose_log("✅ Analytics service initialized in bot_data")

    # Add analytics middleware (runs BEFORE all handlers)
    if analytics_imported:
        async def wrapped_analytics_middleware(update: Update, context):
            await analytics_middleware(update, context)

        app.add_handler(
            MessageHandler(filters.ALL, wrapped_analytics_middleware),
            group=-1
        )
        app.add_handler(
            CallbackQueryHandler(wrapped_analytics_middleware),
            group=-1
        )
        verbose_log("✅ Analytics middleware registered")
    # === КОНЕЦ ДОБАВЛЕНИЯ ===

    # Basic commands
    app.add_handler(CommandHandler("start", start_command))
    # ... rest of handlers
```

### 3. Трекинг AI генераций в модулях

Добавьте трекинг в модулях, где происходит AI генерация:

#### В `modules/summaries.py`:

После успешной генерации саммари (добавить после вызова `ai_service.generate_summary()`):

```python
from utils.analytics_middleware import track_ai_generation

# После генерации саммари
summary_text = ai_service.generate_summary(...)

# Track AI generation
await track_ai_generation(
    context=context,
    user_id=user.id,
    chat_id=chat.id,
    generation_type='summary',
    personality=personality_name,
    metadata={
        'messages_count': len(messages),
        'timeframe': timeframe_hours if timeframe_hours else 'default'
    }
)
```

#### В `modules/judge.py`:

После генерации вердикта:

```python
from utils.analytics_middleware import track_ai_generation

# После генерации вердикта
verdict = ai_service.generate_judge_verdict(...)

# Track AI generation
await track_ai_generation(
    context=context,
    user_id=user.id,
    chat_id=chat.id,
    generation_type='judge',
    personality=personality_name,
    metadata={
        'participants': usernames,
        'messages_analyzed': len(messages)
    }
)
```

#### В `modules/direct_chat.py`:

После генерации ответа в direct chat:

```python
from utils.analytics_middleware import track_ai_generation

# После генерации ответа
response = ai_service.generate_chat_response(...)

# Track AI generation
await track_ai_generation(
    context=context,
    user_id=user.id,
    chat_id=chat.id,
    generation_type='chat_response',
    personality=personality_name,
    metadata={
        'message_length': len(message_text),
        'context_messages': len(history)
    }
)
```

## 📊 Использование аналитики

### Проверка в Supabase

После запуска бота, откройте Supabase → Table Editor → `button_analytics`.

Вы увидите записи о всех взаимодействиях:
- `action_type`: 'button_click', 'command', 'message', 'ai_generation', 'error'
- `action_name`: конкретное действие ('direct_chat', 'select_personality', '/start', etc.)
- `button_text`: текст кнопки (если клик)
- `metadata`: JSON с дополнительными данными

### SQL Queries для анализа

См. файл `sql/analytics_queries.sql` (будет создан далее).

Примеры:

**1. Топ-10 кнопок за последние 7 дней:**
```sql
SELECT * FROM get_top_actions(7, 10);
```

**2. Популярные кнопки с разбивкой по дням:**
```sql
SELECT * FROM popular_buttons_7d
ORDER BY date DESC, total_clicks DESC;
```

**3. Воронка конверсии:**
```sql
SELECT * FROM conversion_funnel
ORDER BY action_number;
```

**4. Активность по часам:**
```sql
SELECT * FROM activity_by_hour
WHERE action_type = 'button_click'
ORDER BY hour;
```

**5. Путь конкретного пользователя:**
```sql
SELECT
  action_type,
  action_name,
  button_text,
  created_at
FROM button_analytics
WHERE user_id = YOUR_USER_ID
  AND created_at >= NOW() - INTERVAL '7 days'
ORDER BY created_at ASC;
```

## 🔍 Debugging

### Проверка работы middleware:

1. Отправьте команду `/start` боту
2. Проверьте логи Vercel - должно быть:
   ```
   ✅ Analytics service initialized in bot_data
   ✅ Analytics middleware registered
   Tracked command: /start by user 123456
   ```
3. Проверьте Supabase → `button_analytics`:
   - Должна появиться запись с `action_type: 'command'` и `action_name: '/start'`

### Если аналитика не работает:

1. **Проверьте миграцию БД:**
   ```sql
   SELECT COUNT(*) FROM button_analytics;
   -- Должно быть >= 0 (таблица существует)
   ```

2. **Проверьте логи Vercel:**
   - Ищите ошибки типа "Error tracking button click"
   - Проверьте, что импорт `analytics_middleware` прошёл успешно

3. **Проверьте права доступа Supabase:**
   - API key должен иметь права на INSERT в `button_analytics`

## 🎯 Best Practices

1. **Не блокируйте основной флоу:**
   - Middleware оборачивает все вызовы в try/except
   - Ошибки аналитики не должны ломать работу бота

2. **Privacy:**
   - Не логируйте личные данные (текст сообщений, номера телефонов)
   - Храните только метаданные (длина, тип, количество)

3. **Retention:**
   - Автоматическая очистка данных старше 90 дней (см. функцию `cleanup_old_analytics()`)
   - Запустите вручную или настройте cron job:
     ```sql
     SELECT cleanup_old_analytics();
     ```

4. **Performance:**
   - Используйте индексы (уже созданы в миграции)
   - Для больших датасетов используйте партиционирование по дате

## 📈 Визуализация

Для создания дашбордов можно использовать:
- **Supabase Dashboard** - встроенные графики
- **Metabase** - подключить к Supabase PostgreSQL
- **Google Data Studio** - через коннектор PostgreSQL
- **Custom dashboard** - React/Vue + Chart.js, данные через Supabase API

## 🚀 Следующие шаги

1. Применить миграцию БД
2. Обновить `api/index.py` с middleware
3. Добавить трекинг AI генераций в модули
4. Протестировать на staging
5. Deploy на production
6. Настроить дашборд для визуализации

---

**Готово!** Теперь у вас полная аналитика всех взаимодействий с ботом 🎉
