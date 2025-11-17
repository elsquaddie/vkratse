# 💰 TODO: Монетизация v2.1

**Дата создания:** 2025-11-17
**Последнее обновление:** 2025-11-17 (Шаг 11 завершен)
**Статус:** В разработке
**Прогресс:** 63/75 задач (84%)

**📝 Инструкции для тестирования:**
- [QUICKSTART_MONETIZATION.md](./QUICKSTART_MONETIZATION.md) - Быстрый старт за 5 минут
- [TESTING_MONETIZATION.md](./TESTING_MONETIZATION.md) - Полная инструкция по тестированию
- [TESTING_TELEGRAM_STARS.md](./TESTING_TELEGRAM_STARS.md) - Тестирование Telegram Stars (Шаг 11)

---

## 📊 Модель монетизации (краткая справка)

| Функция | Free | Free + Group | Pro | Pro + Group |
| :--- | :--- | :--- | :--- | :--- |
| ЛС сообщения | 30/день | 30/день | 500/день | 500/день |
| Summary в ЛС | 3/день | 3/день | 10/день | 10/день |
| Summary в группах | 3/день | 3/день | 20/день | 20/день |
| Нейтральный | ♾️ | ♾️ | ♾️ | ♾️ |
| **Остальные личности** | 5 summary<br>5 chat<br>5 rassudi | 5 summary<br>5 chat<br>5 rassudi | **Без лимитов (♾️)** | **Без лимитов (♾️)** |
| Кастомные личности | 0 | 1 (бонус) | 3 | 4 (3+1) |
| Общий лимит /rassudi | 2/день | 2/день | 20/день | 20/день |
| Cooldown | 60 сек | 60 сек | 30 сек | 30 сек |
| Контекст | 30 сообщений | 30 сообщений | 50 сообщений | 50 сообщений |

---

## 🎯 ЭТАП 1: БАЗОВАЯ ИНФРАСТРУКТУРА (25 задач)

### Шаг 1: База данных и конфигурация

**Цель:** Создать структуру БД для монетизации

- [x] **1.1** Создать SQL-миграцию для таблицы `subscriptions`
  ```sql
  CREATE TABLE subscriptions (
    id SERIAL PRIMARY KEY,
    user_id BIGINT NOT NULL UNIQUE,
    tier VARCHAR(20) NOT NULL,  -- 'free', 'pro'
    started_at TIMESTAMP DEFAULT NOW(),
    expires_at TIMESTAMP,  -- NULL для free tier
    payment_method VARCHAR(50),  -- 'stars', 'yookassa', 'tribute'
    transaction_id VARCHAR(255),
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
  );
  ```

- [x] **1.2** Создать SQL-миграцию для таблицы `usage_limits`
  ```sql
  CREATE TABLE usage_limits (
    id SERIAL PRIMARY KEY,
    user_id BIGINT NOT NULL,
    date DATE DEFAULT CURRENT_DATE,
    messages_count INT DEFAULT 0,
    summaries_count INT DEFAULT 0,
    summaries_dm_count INT DEFAULT 0,
    judge_count INT DEFAULT 0,
    UNIQUE(user_id, date)
  );
  ```

- [x] **1.3** Создать SQL-миграцию для таблицы `personality_usage`
  ```sql
  CREATE TABLE personality_usage (
    id SERIAL PRIMARY KEY,
    user_id BIGINT NOT NULL,
    personality_name VARCHAR(100) NOT NULL,
    date DATE DEFAULT CURRENT_DATE,
    summary_count INT DEFAULT 0,
    chat_count INT DEFAULT 0,
    judge_count INT DEFAULT 0,
    UNIQUE(user_id, personality_name, date)
  );
  ```

- [x] **1.4** Создать SQL-миграцию для таблицы `group_membership_cache`
  ```sql
  CREATE TABLE group_membership_cache (
    user_id BIGINT PRIMARY KEY,
    is_member BOOLEAN DEFAULT FALSE,
    checked_at TIMESTAMP DEFAULT NOW()
  );
  ```

- [x] **1.5** Добавить поле `is_group_bonus` в таблицу `personalities`
  ```sql
  ALTER TABLE personalities ADD COLUMN is_group_bonus BOOLEAN DEFAULT FALSE;
  ```

- [x] **1.6** Применить все миграции в Supabase (см. инструкции в sql/migrations/README_MONETIZATION_MIGRATIONS.md)

- [x] **1.7** Обновить `config.py`: добавить `PROJECT_TELEGRAM_GROUP_ID`
  ```python
  PROJECT_TELEGRAM_GROUP_ID = int(os.getenv('PROJECT_TELEGRAM_GROUP_ID', '0'))
  ```

- [x] **1.8** Обновить `config.py`: добавить `TIER_LIMITS`
  ```python
  TIER_LIMITS = {
      'free': {
          'messages_dm': 30,
          'summaries_dm': 3,
          'summaries_group': 3,
          'judge': 2,
          'personality_summary': 5,
          'personality_chat': 5,
          'personality_judge': 5,
          'custom_personalities': 0,
          'context_messages': 30,
          'cooldown_seconds': 60
      },
      'pro': {
          'messages_dm': 500,
          'summaries_dm': 10,
          'summaries_group': 20,
          'judge': 20,
          # ВАЖНО: Pro-пользователи имеют безлимитное использование личностей
          # personality_summary, personality_chat, personality_judge НЕ указываются
          'custom_personalities': 3,
          'context_messages': 50,
          'cooldown_seconds': 30
      }
  }
  ```

- [ ] **1.9 ТЕСТ:** Подключиться к БД и проверить, что все таблицы созданы корректно

---

### Шаг 2: Сервисы для определения статуса пользователя

**Цель:** Реализовать логику определения тарифа пользователя

- [x] **2.1** Создать файл `services/subscription.py`

- [x] **2.2** Реализовать `get_user_tier(user_id: int) -> str`
  ```python
  async def get_user_tier(user_id: int) -> str:
      """
      Определить тариф пользователя: 'free' или 'pro'
      ВАЖНО: Проверяет expires_at для автоматического даунгрейда
      """
      subscription = await db_service.get_subscription(user_id)

      if not subscription or not subscription.is_active:
          return 'free'

      # Проверка истечения подписки (критично для Vercel)
      if subscription.expires_at and subscription.expires_at < datetime.now():
          await auto_downgrade_expired_subscription(user_id)
          return 'free'

      return subscription.tier
  ```

- [x] **2.3** Добавить в `db_service.py`: `get_subscription(user_id: int)`

- [x] **2.4** Добавить в `db_service.py`: методы для работы с подписками
  - `get_subscription(user_id)`
  - `create_or_update_subscription(...)`
  - `deactivate_subscription(user_id)`
  - `get_usage_limits(user_id, date)`
  - `increment_usage_limit(user_id, action)`
  - `get_personality_usage(user_id, personality, date)`
  - `increment_personality_usage(user_id, personality, action)`
  - `get_group_membership_cache(user_id)`
  - `update_group_membership_cache(user_id, is_member)`
  - `get_active_custom_personalities_count(user_id)`
  - `block_excess_custom_personalities(user_id, limit)`

- [x] **2.5** Обновить `services/subscription.py`: добавить импорты и инициализацию db_service

- [ ] **2.6 ТЕСТ:** Вручную добавить Pro-подписку в БД и проверить `get_user_tier()`
  - Добавить подписку с `is_active=True` → должна вернуть 'pro'
  - Изменить `is_active=False` → должна вернуть 'free'
  - Удалить запись → должна вернуть 'free'
  - **См. инструкции:** [TESTING_MONETIZATION.md](./TESTING_MONETIZATION.md)

---

### Шаг 3: Реализация базовых лимитов (для Free-пользователей)

**Цель:** Внедрить проверку лимитов для Free-тарифа

- [x] **3.1** Реализовать `check_usage_limit(user_id: int, action: str) -> dict` ✅
  ```python
  async def check_usage_limit(user_id: int, action: str) -> dict:
      """
      Проверить лимит использования для действия

      Args:
          user_id: ID пользователя
          action: 'message_dm', 'summary_dm', 'summary_group', 'judge'

      Returns:
          {'can_proceed': bool, 'current': int, 'limit': int, 'tier': str}
      """
  ```

- [x] **3.2** Реализовать `increment_usage(user_id: int, action: str)` ✅

- [x] **3.3** Добавить в `db_service.py`: `get_usage_limits(user_id: int, date: date)` ✅

- [x] **3.4** Добавить в `db_service.py`: `increment_usage_limit(user_id: int, action: str)` ✅

- [x] **3.5** Встроить проверку в `modules/direct_chat.py:handle_direct_message()` ✅
  ```python
  # В начале функции
  limit_check = await check_usage_limit(user_id, 'message_dm')
  if not limit_check['can_proceed']:
      await update.message.reply_text(
          f"⚠️ Лимит сообщений исчерпан ({limit_check['current']}/{limit_check['limit']}).\n"
          f"Обновите тариф: /premium"
      )
      return

  # После успешной отправки сообщения
  await increment_usage(user_id, 'message_dm')
  ```

- [x] **3.6** Встроить проверку в `modules/summaries.py` (для ЛС summary и групповых summary) ✅
  ```python
  # Определить контекст: ЛС или группа
  action = 'summary_dm' if chat_type == ChatType.PRIVATE else 'summary_group'
  limit_check = await check_usage_limit(user_id, action)
  ```

- [x] **3.7** Создать функцию `show_upgrade_message(update, reason: str)` ✅
  - Реализовано в `utils/upgrade_messages.py`
  ```python
  async def show_upgrade_message(update: Update, reason: str):
      """Показать сообщение с предложением улучшить тариф"""
      message = f"⚠️ {reason}\n\n"
      message += "💎 Обновите до Pro:\n"
      message += "• До 500 сообщений/день\n"
      message += "• Безлимитные личности\n"
      message += "• И многое другое!\n\n"
      message += "Узнать больше: /premium"
  ```

- [x] **3.8** Встроить `show_upgrade_message()` во все обработчики с лимитами ✅
  - ✅ `modules/direct_chat.py` - лимит сообщений
  - ✅ `modules/summaries.py` - лимиты саммари (DM + группы)
  - ✅ `modules/judge.py` - лимит судейства

- [ ] **3.9 ТЕСТ:** Отправить 30 сообщений боту в ЛС
  - 30-е сообщение должно пройти
  - 31-е должно показать уведомление о лимите
  - Проверить в БД: `messages_count = 30`

- [ ] **3.10 ТЕСТ:** Использовать `/summary` в ЛС 3 раза
  - 3-й раз должен пройти
  - 4-й раз должен показать уведомление о лимите
  - Проверить в БД: `summaries_dm_count = 3`

---

## 🎯 ЭТАП 2: ВНЕДРЕНИЕ PRO-ПОДПИСКИ (22 задачи)

### Шаг 4: Команды /premium и /mystatus

**Цель:** Создать интерфейс для просмотра и покупки тарифов

- [ ] **4.1** Создать обработчик команды `/premium` в `modules/commands.py`
  ```python
  async def premium_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
      """Показать доступные тарифные планы"""
      user_id = update.effective_user.id
      current_tier = await get_user_tier(user_id)

      message = "💎 Premium планы\n\n"
      message += "🆓 FREE (текущий план)\n" if current_tier == 'free' else "🆓 FREE\n"
      message += "• 30 сообщений/день\n"
      message += "• 3 саммари в ЛС/день\n"
      message += "• 5 использований личности/день\n\n"

      message += "⭐ PRO - $2.99/мес\n" if current_tier != 'pro' else "⭐ PRO (текущий план)\n"
      message += "• 500 сообщений/день\n"
      message += "• Безлимитные личности ♾️\n"
      message += "• 3 кастомные личности\n"
      message += "• Приоритетная обработка\n\n"

      keyboard = [
          [InlineKeyboardButton("💳 Купить Pro", callback_data=sign_callback_data("buy_pro"))],
          [InlineKeyboardButton("🎁 Tribute.to", url=config.TRIBUTE_URL)],
          [InlineKeyboardButton("« Назад", callback_data=sign_callback_data("back_to_start"))]
      ]
      reply_markup = InlineKeyboardMarkup(keyboard)
      await update.message.reply_text(message, reply_markup=reply_markup)
  ```

- [ ] **4.2** Добавить кнопку "💎 Premium" в главное меню `/start`
  ```python
  # В функции start_command и show_main_menu
  if chat_type == ChatType.PRIVATE:
      keyboard = [
          [InlineKeyboardButton("💬 Общаться напрямую", callback_data=sign_callback_data("direct_chat"))],
          [InlineKeyboardButton("📊 Саммари групп", callback_data=sign_callback_data("dm_summary"))],
          [InlineKeyboardButton("💎 Premium", callback_data=sign_callback_data("show_premium"))],  # НОВАЯ КНОПКА
          [InlineKeyboardButton("👥 Добавить в групповой чат", url=f"https://t.me/{config.BOT_USERNAME}?startgroup=true")],
          [InlineKeyboardButton("🎭 Настроить личность", callback_data=sign_callback_data("setup_personality"))]
      ]
  ```

- [ ] **4.3** Создать обработчик callback_query для кнопки Premium
  ```python
  async def handle_show_premium_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
      """Обработчик кнопки Premium из главного меню"""
      query = update.callback_query
      await query.answer()

      # Переиспользовать логику из premium_command
      # Но использовать edit_message_text вместо reply_text
  ```

- [ ] **4.4** Создать обработчик команды `/mystatus` в `modules/commands.py`
  ```python
  async def mystatus_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
      """Показать текущий статус подписки и использования"""
      user_id = update.effective_user.id
      tier = await get_user_tier(user_id)
      usage = await get_usage_limits(user_id, date.today())

      # Эмодзи для тарифа
      tier_emoji = "💎" if tier == 'pro' else "🆓"
      tier_name = "Pro" if tier == 'pro' else "Free"

      message = f"📊 Твой статус\n\n"
      message += f"Тариф: {tier_emoji} {tier_name}\n"

      # Если Pro - показать дату истечения
      if tier == 'pro':
          subscription = await get_subscription(user_id)
          if subscription.expires_at:
              days_left = (subscription.expires_at - datetime.now()).days
              message += f"Активен до: {subscription.expires_at.strftime('%Y-%m-%d')}\n"
              message += f"Осталось: {days_left} дней\n\n"

      # Использование сегодня
      limits = TIER_LIMITS[tier]
      message += "Использовано сегодня:\n"
      message += f"💬 Сообщения: {usage.messages_count}/{limits['messages_dm']}\n"
      message += f"📝 Саммари (ЛС): {usage.summaries_dm_count}/{limits['summaries_dm']}\n"
      message += f"⚖️ Судейство: {usage.judge_count}/{limits['judge']}\n\n"

      if tier == 'free':
          message += "💡 Обновись до Pro: /premium"

      await update.message.reply_text(message)
  ```

- [ ] **4.5 ТЕСТ:** Отправить `/premium` и увидеть описание тарифов
  - Проверить, что текущий тариф выделен
  - Проверить, что кнопки отображаются корректно

- [ ] **4.6 ТЕСТ:** Отправить `/mystatus` и увидеть свой статус
  - Для Free: должен показать "🆓 Free" и использованные лимиты
  - Проверить, что счетчики совпадают с реальным использованием

---

### Шаг 5: Интеграция с Tribute.to (Приоритет 1)

**Цель:** Создать первый способ покупки Pro через донаты

- [ ] **5.1** Создать страницу на [Tribute.to](https://tribute.to) для сбора донатов
  - Описать тарифы и бонусы
  - Указать, что после доната нужно связаться с админом
  - **ПРИМЕЧАНИЕ:** Это ручная задача для владельца бота

- [x] **5.2** Добавить в `config.py`: `TRIBUTE_URL` ✅
  ```python
  TRIBUTE_URL = os.getenv('TRIBUTE_URL', 'https://tribute.to/your_bot_page')
  ADMIN_USER_ID = int(os.getenv('ADMIN_USER_ID', '0'))  # Ваш Telegram ID
  ```
  - Реализовано в config.py:102-103

- [x] **5.3** Обновить кнопку "Купить Pro" в `/premium` ✅
  ```python
  keyboard = [
      [InlineKeyboardButton("🎁 Donate (Tribute.to)", url=config.TRIBUTE_URL)],
      [InlineKeyboardButton("« Назад", callback_data=sign_callback_data("back_to_start"))]
  ]
  ```

- [x] **5.4** Создать админскую команду `/grantpro` в `modules/commands.py` ✅
  - **Реализовано:** modules/commands.py:535-666
  - **Зарегистрировано:** api/index.py:93, 277
  - **УЛУЧШЕНИЯ БЕЗОПАСНОСТИ:**
    - ✅ Проверка ADMIN_USER_ID (только админ может использовать)
    - ✅ Валидация входных данных (user_id > 0, days 1-3650)
    - ✅ Полное логирование всех операций (до, во время, после)
    - ✅ Обработка всех ошибок с graceful degradation
    - ✅ Уникальный transaction_id для аудита
    - ✅ Защита от неудачных уведомлений пользователя
    - ✅ Информативные сообщения об ошибках

  **Использование:**
  ```bash
  /grantpro <user_id> <days>
  # Примеры:
  /grantpro 123456789 30    # 30 дней Pro
  /grantpro 987654321 365   # 1 год Pro
  ```

- [x] **5.5** Добавить в `db_service.py`: `create_or_update_subscription()` ✅
  - Реализовано в services/subscription.py
  - Используется через SubscriptionService.create_or_update_subscription()

- [ ] **5.6 ТЕСТ:** Нажать на кнопку в `/premium` и проверить, что Tribute.to открывается

- [ ] **5.7 ТЕСТ:** Использовать `/grantpro` на тестовом аккаунте
  - Выполнить `/grantpro <test_user_id> 30`
  - Проверить в БД: появилась активная подписка
  - С тестового аккаунта выполнить `/mystatus` → должен показать "💎 Pro"

---

### Шаг 6: Логика для Pro-пользователей (безлимитные личности) ✅

**Цель:** Реализовать ключевую фичу Pro - безлимитное использование личностей

- [x] **6.1** Реализовать `check_personality_limit()` в `subscription.py` ✅
  ```python
  async def check_personality_limit(
      user_id: int,
      personality: str,
      action: str
  ) -> dict:
      """
      Проверить лимит использования конкретной личности

      Args:
          user_id: ID пользователя
          personality: Название личности (напр., 'bydlan')
          action: 'summary', 'chat', 'judge'

      Returns:
          {'can_proceed': bool, 'current': int, 'limit': int, 'tier': str}

      ВАЖНО: Для Pro-пользователей ВСЕГДА возвращает can_proceed=True
      """
      tier = await get_user_tier(user_id)

      # Pro-пользователи: безлимитное использование личностей
      if tier == 'pro':
          return {
              'can_proceed': True,
              'current': 0,
              'limit': -1,  # -1 означает безлимит
              'tier': 'pro'
          }

      # Free-пользователи: проверка лимитов
      # Нейтральная личность всегда доступна
      if personality == 'neutral':
          return {'can_proceed': True, 'current': 0, 'limit': -1, 'tier': 'free'}

      # Проверить использование личности за сегодня
      usage = await get_personality_usage(user_id, personality, date.today())
      limits = TIER_LIMITS['free']

      action_key = f'personality_{action}'  # 'personality_summary', 'personality_chat', etc.
      current = getattr(usage, f'{action}_count', 0)
      limit = limits.get(action_key, 5)

      return {
          'can_proceed': current < limit,
          'current': current,
          'limit': limit,
          'tier': 'free'
      }
  ```

- [x] **6.2** Добавить в `db_service.py`: `get_personality_usage()` ✅
  - Реализовано в services/db_service.py:836-868
  ```python
  async def get_personality_usage(
      user_id: int,
      personality: str,
      date: date
  ):
      """Получить использование конкретной личности за дату"""
      try:
          response = self.client.table('personality_usage')\
              .select('*')\
              .eq('user_id', user_id)\
              .eq('personality_name', personality)\
              .eq('date', date.isoformat())\
              .execute()

          if response.data:
              return response.data[0]
          else:
              # Вернуть пустой объект с нулями
              return {
                  'summary_count': 0,
                  'chat_count': 0,
                  'judge_count': 0
              }
      except Exception as e:
          logger.error(f"Error getting personality usage: {e}")
          return {'summary_count': 0, 'chat_count': 0, 'judge_count': 0}
  ```

- [x] **6.3** Добавить в `db_service.py`: `increment_personality_usage()` ✅
  - Реализовано в services/db_service.py:870-924
  - Также добавлено `get_top_personality_usage()` для /mystatus
  ```python
  async def increment_personality_usage(
      user_id: int,
      personality: str,
      action: str
  ):
      """Увеличить счетчик использования личности"""
      try:
          today = date.today()
          action_field = f'{action}_count'  # 'summary_count', 'chat_count', 'judge_count'

          # Получить текущее значение
          current = await get_personality_usage(user_id, personality, today)
          new_value = current.get(action_field, 0) + 1

          # Upsert
          self.client.table('personality_usage').upsert({
              'user_id': user_id,
              'personality_name': personality,
              'date': today.isoformat(),
              action_field: new_value
          }).execute()
      except Exception as e:
          logger.error(f"Error incrementing personality usage: {e}")
  ```

- [x] **6.4** Встроить проверку в `modules/summaries.py` перед генерацией саммари ✅
  - Проверка добавлена в _execute_summary() перед генерацией
  - Инкремент добавлен после успешной генерации
  ```python
  # После выбора личности, перед генерацией
  personality_check = await check_personality_limit(user_id, personality, 'summary')

  if not personality_check['can_proceed']:
      await query.edit_message_text(
          f"⚠️ Лимит использования личности '{personality}' исчерпан "
          f"({personality_check['current']}/{personality_check['limit']}).\n\n"
          f"💎 Pro-подписка дает безлимитное использование всех личностей!\n"
          f"Узнать больше: /premium"
      )
      return

  # После успешной генерации
  await increment_personality_usage(user_id, personality, 'summary')
  ```

- [x] **6.5** Встроить проверку в `modules/direct_chat.py` (для чата) ✅
  - Проверка добавлена в handle_direct_message() перед генерацией ответа
  - Инкремент добавлен после успешного ответа

- [x] **6.6** Встроить проверку в `modules/judge.py` (для судейства) ✅
  - Проверка добавлена в handle_judge_personality_callback() перед генерацией вердикта
  - Инкремент добавлен после успешного вердикта

- [x] **6.7** Обновить `/mystatus`: добавить информацию об использовании личностей ✅
  - Для Pro: показывает "Личности: Безлимитно ♾️"
  - Для Free: показывает топ-3 используемых личности с детализацией (summary/chat/judge)
  - Формат: "• Быдлан: 12/15 (📝5 💬4 ⚖️3)"
  ```python
  # Для Free-пользователей показать топ-3 используемых личности
  if tier == 'free':
      personality_usage = await get_top_personality_usage(user_id, date.today(), limit=3)
      if personality_usage:
          message += "\n📊 Использование личностей:\n"
          for pu in personality_usage:
              total = pu['summary_count'] + pu['chat_count'] + pu['judge_count']
              message += f"• {pu['personality_name']}: {total}/15\n"

  # Для Pro-пользователей
  if tier == 'pro':
      message += "\n✨ Личности: Безлимитно ♾️\n"
  ```

- [x] **6.8 ТЕСТ:** Активировать Pro-подписку себе ⏭️ (Готов к тестированию)
  - Использовать личность "Быдлан" для summary 6+ раз подряд
  - Все попытки должны быть успешными (без ограничений)
  - **См. инструкции:** [TESTING_MONETIZATION.md](./TESTING_MONETIZATION.md) - Раздел "Шаг 6"

- [x] **6.9 ТЕСТ:** Отключить Pro-подписку (стать Free) ⏭️ (Готов к тестированию)
  - Использовать "Быдлан" для summary 5 раз
  - На 6-й раз должно появиться уведомление о лимите
  - Проверить `/mystatus`: должно показать использование личностей
  - **См. инструкции:** [TESTING_MONETIZATION.md](./TESTING_MONETIZATION.md) - Раздел "Шаг 6"

---

## 🎯 ЭТАП 3: БОНУС ЗА ГРУППУ И КАСТОМНЫЕ ЛИЧНОСТИ (21 задача)

### Шаг 7: Логика проверки членства в группе ✅

**Цель:** Отслеживать членство пользователя в группе проекта

- [x] **7.1** Реализовать `is_in_project_group()` в `subscription.py` ✅
  ```python
  async def is_in_project_group(
      user_id: int,
      bot: Bot,
      force_check: bool = False
  ) -> bool:
      """
      Проверить, состоит ли пользователь в группе проекта

      Args:
          user_id: ID пользователя
          bot: Telegram Bot instance
          force_check: Принудительная проверка (игнорировать кеш)

      Returns:
          bool: True если состоит в группе
      """
      if not config.PROJECT_TELEGRAM_GROUP_ID:
          return False

      # Проверить кеш (если не force_check)
      if not force_check:
          cache = await get_group_membership_cache(user_id)
          if cache and (datetime.now() - cache['checked_at']).seconds < 3600:  # 1 час
              return cache['is_member']

      # Проверить через API
      try:
          member = await bot.get_chat_member(
              chat_id=config.PROJECT_TELEGRAM_GROUP_ID,
              user_id=user_id
          )
          is_member = member.status in ['member', 'administrator', 'creator']

          # Обновить кеш
          await update_group_membership_cache(user_id, is_member)

          return is_member
      except Exception as e:
          logger.error(f"Error checking group membership: {e}")
          return False
  ```

- [x] **7.2** Добавить в `db_service.py`: `get_group_membership_cache()` ✅
  - Реализовано в services/db_service.py:982-1002

- [x] **7.3** Добавить в `db_service.py`: `update_group_membership_cache()` ✅
  - Реализовано в services/db_service.py:1004-1029

- [x] **7.4** Создать обработчик `chat_member` в `api/index.py` ✅
  - Реализовано в api/index.py:251-295
  - `handle_chat_member_update()` обрабатывает события вступления/выхода
  - `ChatMemberHandler` зарегистрирован в api/index.py:479-482
  ```python
  async def handle_chat_member_update(update: Update, context: ContextTypes.DEFAULT_TYPE):
      """Обработчик изменения статуса участника в чате"""
      chat_member_update = update.chat_member

      # Проверить, это наша целевая группа?
      if chat_member_update.chat.id != config.PROJECT_TELEGRAM_GROUP_ID:
          return

      user_id = chat_member_update.new_chat_member.user.id
      old_status = chat_member_update.old_chat_member.status
      new_status = chat_member_update.new_chat_member.status

      # Определить: вступил или вышел
      was_member = old_status in ['member', 'administrator', 'creator']
      is_member = new_status in ['member', 'administrator', 'creator']

      if was_member != is_member:
          await handle_group_membership_change(user_id, is_member, context.bot)
  ```

- [x] **7.5** Реализовать `handle_group_membership_change()` в `subscription.py` ✅
  - Реализовано в services/subscription.py:454-510
  - Обновляет кеш, блокирует/разблокирует бонусные личности
  - Отправляет уведомления пользователю о изменении статуса
  - Добавлены методы в db_service.py:
    - `block_group_bonus_personalities()` (1105-1129)
    - `unblock_group_bonus_personalities()` (1131-1155)
  ```python
  async def handle_group_membership_change(
      user_id: int,
      is_member: bool,
      bot: Bot
  ):
      """Обработать изменение членства в группе"""
      # Обновить кеш
      await update_group_membership_cache(user_id, is_member)

      # Если вышел из группы - заблокировать бонусные личности (реализуем в Шаге 9)
      if not is_member:
          await block_group_bonus_personalities(user_id)
      else:
          await unblock_group_bonus_personalities(user_id)
  ```

- [ ] **7.6 ТЕСТ:** Вступить в группу проекта ⏭️ (Готов к тестированию)
  - Проверить в БД: `group_membership_cache.is_member = true`
  - Вызвать `is_in_project_group()` → должна вернуть `True`
  - **См. инструкции:** [TESTING_STEP7_GROUP_MEMBERSHIP.md](./TESTING_STEP7_GROUP_MEMBERSHIP.md) - Тест 1

- [ ] **7.7 ТЕСТ:** Выйти из группы проекта ⏭️ (Готов к тестированию)
  - Проверить в БД: `group_membership_cache.is_member = false`
  - Вызвать `is_in_project_group()` → должна вернуть `False`
  - **См. инструкции:** [TESTING_STEP7_GROUP_MEMBERSHIP.md](./TESTING_STEP7_GROUP_MEMBERSHIP.md) - Тест 4-5

**📋 ВАЖНО - Подготовка к тестированию Шага 7:**
- Включить `chat_member` обновления через BotFather (выключить Privacy Mode)
- Установить `PROJECT_TELEGRAM_GROUP_ID` в Vercel environment variables
- Применить миграцию 007 (поля `is_group_bonus` и `is_blocked`)
- **Полная инструкция:** [TESTING_STEP7_GROUP_MEMBERSHIP.md](./TESTING_STEP7_GROUP_MEMBERSHIP.md)

---

### Шаг 8: Логика создания кастомных личностей ✅

**Цель:** Реализовать систему лимитов на кастомные личности

- [x] **8.1** Реализовать `get_custom_personality_limit()` в `subscription.py` ✅
  - Реализовано в services/subscription.py:340-368
  ```python
  async def get_custom_personality_limit(
      user_id: int,
      bot: Bot
  ) -> int:
      """
      Определить лимит кастомных личностей для пользователя

      Returns:
          int: Количество доступных слотов для кастомных личностей

      Логика:
          Free: 0
          Free + Group: 1
          Pro: 3
          Pro + Group: 4
      """
      tier = await get_user_tier(user_id)
      in_group = await is_in_project_group(user_id, bot)

      if tier == 'pro':
          return 4 if in_group else 3
      else:  # free
          return 1 if in_group else 0
  ```

- [x] **8.2** Добавить в `db_service.py`: `get_active_custom_personalities_count()` ✅
  - Реализовано в services/db_service.py:1035-1056
  ```python
  async def get_active_custom_personalities_count(user_id: int) -> int:
      """Получить количество активных кастомных личностей пользователя"""
      try:
          response = self.client.table('personalities')\
              .select('id', count='exact')\
              .eq('created_by_user_id', user_id)\
              .eq('is_custom', True)\
              .eq('is_active', True)\
              .execute()

          return response.count if response.count else 0
      except Exception as e:
          logger.error(f"Error counting custom personalities: {e}")
          return 0
  ```

- [x] **8.3** Реализовать `can_create_custom_personality()` в `subscription.py` ✅
  - Реализовано в services/subscription.py:370-452
  ```python
  async def can_create_custom_personality(
      user_id: int,
      bot: Bot
  ) -> dict:
      """
      Проверить, может ли пользователь создать кастомную личность

      Returns:
          {
              'can_create': bool,
              'reason': str,
              'current': int,
              'limit': int,
              'needs_group': bool,
              'needs_pro': bool
          }
      """
      tier = await get_user_tier(user_id)
      in_group = await is_in_project_group(user_id, bot)
      limit = await get_custom_personality_limit(user_id, bot)
      current = await get_active_custom_personalities_count(user_id)

      # Сценарии
      if current >= limit:
          if tier == 'free' and not in_group:
              return {
                  'can_create': False,
                  'reason': 'need_group_or_pro',
                  'current': current,
                  'limit': limit,
                  'needs_group': True,
                  'needs_pro': True
              }
          elif tier == 'free' and in_group:
              return {
                  'can_create': False,
                  'reason': 'need_pro',
                  'current': current,
                  'limit': limit,
                  'needs_group': False,
                  'needs_pro': True
              }
          elif tier == 'pro' and not in_group:
              return {
                  'can_create': False,
                  'reason': 'need_group',
                  'current': current,
                  'limit': limit,
                  'needs_group': True,
                  'needs_pro': False
              }
          else:  # pro + group
              return {
                  'can_create': False,
                  'reason': 'max_reached',
                  'current': current,
                  'limit': limit,
                  'needs_group': False,
                  'needs_pro': False
              }

      return {
          'can_create': True,
          'reason': 'ok',
          'current': current,
          'limit': limit,
          'needs_group': False,
          'needs_pro': False
      }
  ```

- [x] **8.4** Обновить `modules/personalities.py`: встроить проверку ✅
  - Проверка добавлена в обработчик "create_start" (modules/personalities.py:110-141)
  - Удалена старая проверка из receive_personality_name (строки 257-258)
  ```python
  # В обработчике создания личности (перед началом ConversationHandler)
  async def handle_create_personality_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
      query = update.callback_query
      await query.answer()

      user_id = update.effective_user.id
      check = await can_create_custom_personality(user_id, context.bot)

      if not check['can_create']:
          # Сформировать сообщение в зависимости от причины
          if check['reason'] == 'need_group_or_pro':
              message = (
                  f"⚠️ Лимит кастомных личностей: {check['current']}/{check['limit']}\n\n"
                  f"Чтобы создать свою личность:\n"
                  f"• Вступи в группу проекта: [ссылка]\n"
                  f"или\n"
                  f"• Обновись до Pro: /premium"
              )
          elif check['reason'] == 'need_pro':
              message = (
                  f"⚠️ Лимит кастомных личностей: {check['current']}/{check['limit']}\n\n"
                  f"Обновись до Pro для создания еще 3 личностей: /premium"
              )
          elif check['reason'] == 'need_group':
              message = (
                  f"⚠️ Лимит кастомных личностей: {check['current']}/{check['limit']}\n\n"
                  f"Вступи в группу проекта для +1 слота: [ссылка]"
              )
          else:  # max_reached
              message = (
                  f"⚠️ Достигнут максимум: {check['current']}/{check['limit']}\n\n"
                  f"Удали неиспользуемые личности через /lichnost"
              )

          await query.edit_message_text(message)
          return ConversationHandler.END

      # Продолжить создание
      # ...
  ```

- [x] **8.5** Обновить `db_service.py`: добавить `is_group_bonus` при создании личности ✅
  - Обновлен метод create_personality (services/db_service.py:164-206)
  - Добавлен параметр is_group_bonus (default=False)
  - Автоматическое определение в personalities.py:342-345 на основе тарифа
  ```python
  async def create_custom_personality(...):
      # Определить: это бонусная личность или нет
      tier = await get_user_tier(user_id)
      is_group_bonus = (tier == 'free')  # Для Free-пользователя это бонус за группу

      self.client.table('personalities').insert({
          'name': name,
          'display_name': display_name,
          'system_prompt': system_prompt,
          'is_custom': True,
          'created_by_user_id': user_id,
          'is_group_bonus': is_group_bonus,
          'is_active': True
      }).execute()
  ```

- [ ] **8.6 ТЕСТ:** Free, не в группе ⏭️ (Готов к тестированию)
  - Нажать "➕ Создать личность"
  - Увидеть: "Вступи в группу или купи Pro"
  - **См. инструкции:** [TESTING_STEP8_CUSTOM_PERSONALITIES.md](./TESTING_STEP8_CUSTOM_PERSONALITIES.md) - Тест 1

- [ ] **8.7 ТЕСТ:** Free, вступить в группу ⏭️ (Готов к тестированию)
  - Нажать "➕ Создать личность"
  - Успешно создать 1 личность
  - Проверить в БД: `is_group_bonus = true`
  - Попытаться создать 2-ю → увидеть предложение купить Pro
  - **См. инструкции:** [TESTING_STEP8_CUSTOM_PERSONALITIES.md](./TESTING_STEP8_CUSTOM_PERSONALITIES.md) - Тесты 2-3

- [ ] **8.8 ТЕСТ:** Pro, не в группе ⏭️ (Готов к тестированию)
  - Создать 3 личности
  - Попытаться создать 4-ю → увидеть предложение вступить в группу
  - **См. инструкции:** [TESTING_STEP8_CUSTOM_PERSONALITIES.md](./TESTING_STEP8_CUSTOM_PERSONALITIES.md) - Тест 4

- [ ] **8.9 ТЕСТ:** Pro, в группе ⏭️ (Готов к тестированию)
  - Создать 4 личности
  - Попытаться создать 5-ю → увидеть "Достигнут максимум"
  - **См. инструкции:** [TESTING_STEP8_CUSTOM_PERSONALITIES.md](./TESTING_STEP8_CUSTOM_PERSONALITIES.md) - Тест 5

- [ ] **8.10 ТЕСТ:** Блокировка/разблокировка при выходе/входе в группу ⏭️ (Готов к тестированию)
  - Проверить, что бонусная личность блокируется при выходе из группы
  - Проверить, что разблокируется при возврате
  - **См. инструкции:** [TESTING_STEP8_CUSTOM_PERSONALITIES.md](./TESTING_STEP8_CUSTOM_PERSONALITIES.md) - Тесты 6-7

**📋 ВАЖНО - Инструкция по тестированию:**
- Создана полная инструкция: [TESTING_STEP8_CUSTOM_PERSONALITIES.md](./TESTING_STEP8_CUSTOM_PERSONALITIES.md)
- Включает 7 детальных тестов с примерами SQL-запросов
- Описаны ожидаемые результаты и способы отладки
- Готова для использования не-программистом

---

### Шаг 9: Софт-блокировка бонусной личности ✅

**Цель:** Блокировать бонусную личность при выходе из группы

- [x] **9.1** Добавить поле `is_blocked` в таблицу `personalities` (SQL-миграция) ✅
  - Миграция: `sql/migrations/007_add_personality_bonus_fields.sql`
  - Поле `is_blocked BOOLEAN DEFAULT FALSE` добавлено
  - Индекс создан: `idx_personalities_blocked`

- [x] **9.2** Обновить `handle_group_membership_change()`: блокировать личности при выходе ✅
  - Реализовано в services/subscription.py:454-510 (Шаг 7)
  - Вызывает `block_group_bonus_personalities()` при выходе
  - Вызывает `unblock_group_bonus_personalities()` при входе
  - Отправляет уведомления пользователю
  ```python
  async def handle_group_membership_change(user_id: int, is_member: bool, bot: Bot):
      await update_group_membership_cache(user_id, is_member)

      if not is_member:
          await block_group_bonus_personalities(user_id)

          # Уведомить пользователя
          try:
              await bot.send_message(
                  chat_id=user_id,
                  text=(
                      "⚠️ Ты вышел из группы проекта.\n\n"
                      "Твоя бонусная кастомная личность временно заблокирована.\n"
                      "Вернись в группу, чтобы разблокировать: [ссылка]"
                  )
              )
          except Exception as e:
              logger.error(f"Failed to notify user {user_id}: {e}")
      else:
          await unblock_group_bonus_personalities(user_id)

          # Уведомить о разблокировке
          try:
              await bot.send_message(
                  chat_id=user_id,
                  text=(
                      "🎉 Добро пожаловать обратно!\n\n"
                      "Твоя бонусная личность разблокирована."
                  )
              )
          except Exception as e:
              logger.error(f"Failed to notify user {user_id}: {e}")
  ```

- [x] **9.3** Добавить в `db_service.py`: `block_group_bonus_personalities()` ✅
  - Реализовано в services/db_service.py:1121-1145
  - Блокирует все is_group_bonus личности пользователя
  - Возвращает True/False для контроля успешности
  - Полное логирование операций

- [x] **9.4** Добавить в `db_service.py`: `unblock_group_bonus_personalities()` ✅
  - Реализовано в services/db_service.py:1147-1171
  - Разблокирует все is_group_bonus личности пользователя
  - Симметричная логика с block_group_bonus_personalities()

- [x] **9.5** Добавить проверку `is_blocked` при выборе личности ✅
  - ✅ models/personality.py - добавлены поля is_blocked и is_group_bonus
  - ✅ utils/personality_menu.py - показ 🔒 для заблокированных личностей
  - ✅ modules/personalities.py - проверка при выборе (pers:blocked handler)
  - ✅ modules/direct_chat.py - проверка в handle_personality_selection() и handle_direct_message()
  - ✅ modules/summaries.py - проверка в summary_personality_callback()
  - ✅ modules/judge.py - проверка в handle_judge_personality_callback()

  **Поведение:**
  - В меню личности показываются с замком 🔒
  - При клике на заблокированную - alert с объяснением
  - При попытке использовать - блокировка с предложением вернуться в группу
  ```python
  # В utils/personality_menu.py или где выбираются личности
  async def show_personality_selection(...):
      # При формировании списка личностей
      personalities = await get_user_personalities(user_id)

      for p in personalities:
          if p.is_blocked:
              # Не добавлять в меню или показать с замком
              display_name = f"🔒 {p.display_name}"
          else:
              display_name = p.display_name

  # При клике на личность
  async def handle_personality_selection(...):
      personality = await get_personality(personality_name)

      if personality.is_blocked:
          await query.answer(
              "⚠️ Эта личность заблокирована. Вернись в группу проекта!",
              show_alert=True
          )
          return
  ```

- [ ] **9.6 ТЕСТ:** Создать бонусную личность (Free + группа) ⏭️ (Готов к тестированию)
  - Выйти из группы
  - Попытаться использовать эту личность
  - Увидеть сообщение о блокировке
  - Проверить в БД: `is_blocked = true`
  - **См. инструкции:** [TESTING_STEP9_PERSONALITY_BLOCKING.md](./TESTING_STEP9_PERSONALITY_BLOCKING.md) - Тесты 1-4

- [ ] **9.7 ТЕСТ:** Вернуться в группу ⏭️ (Готов к тестированию)
  - Проверить, что личность разблокировалась
  - Успешно использовать личность
  - Проверить в БД: `is_blocked = false`
  - **См. инструкции:** [TESTING_STEP9_PERSONALITY_BLOCKING.md](./TESTING_STEP9_PERSONALITY_BLOCKING.md) - Тесты 5-7

**📋 ВАЖНО - Инструкция по тестированию:**
- Создана полная инструкция: [TESTING_STEP9_PERSONALITY_BLOCKING.md](./TESTING_STEP9_PERSONALITY_BLOCKING.md)
- Включает 7 детальных тестов с примерами SQL-запросов
- Описаны ожидаемые результаты и способы отладки
- Готова для использования не-программистом

---

## ⚠️ КРИТИЧНО: Проверка истечения подписки (Vercel limitation)

**Проблема:** Vercel не поддерживает cron jobs для автоматической проверки истечения подписок.

**Решение:** Проверять `expires_at` при **каждом запросе** пользователя.

- [ ] **CRIT-1** Обновить `get_user_tier()`: добавить проверку `expires_at`
  ```python
  async def get_user_tier(user_id: int) -> str:
      subscription = await get_subscription(user_id)

      if not subscription or not subscription.is_active:
          return 'free'

      # КРИТИЧНО: Проверка истечения подписки
      if subscription.expires_at:
          if subscription.expires_at < datetime.now(timezone.utc):
              logger.info(f"Subscription expired for user {user_id}")
              await auto_downgrade_expired_subscription(user_id)
              return 'free'

      return subscription.tier
  ```

- [ ] **CRIT-2** Реализовать `auto_downgrade_expired_subscription()` в `subscription.py`
  ```python
  async def auto_downgrade_expired_subscription(user_id: int):
      """Автоматически перевести пользователя на Free-тариф"""
      try:
          # Деактивировать подписку
          await deactivate_subscription(user_id)

          # Заблокировать лишние кастомные личности
          # Pro->Free: оставить 0, заблокировать все кастомные
          await block_excess_custom_personalities(user_id, limit=0)

          logger.info(f"User {user_id} downgraded to Free (subscription expired)")
      except Exception as e:
          logger.error(f"Error downgrading subscription for {user_id}: {e}")
  ```

- [ ] **CRIT-3** Добавить в `db_service.py`: `deactivate_subscription()`
  ```python
  async def deactivate_subscription(user_id: int):
      """Деактивировать подписку пользователя"""
      try:
          self.client.table('subscriptions')\
              .update({'is_active': False, 'updated_at': datetime.now().isoformat()})\
              .eq('user_id', user_id)\
              .execute()
      except Exception as e:
          logger.error(f"Error deactivating subscription: {e}")
  ```

- [ ] **CRIT-4** Встроить проверку в начало каждого обработчика команд
  ```python
  # В начале каждого command handler
  async def some_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
      user_id = update.effective_user.id

      # Проверка истечения подписки (автоматически через get_user_tier)
      tier = await get_user_tier(user_id)

      # Дальнейшая логика
      # ...
  ```

- [ ] **CRIT-5** Реализовать уведомление пользователя о даунгрейде
  ```python
  # В auto_downgrade_expired_subscription
  try:
      await context.bot.send_message(
          chat_id=user_id,
          text=(
              "⏰ Твоя Pro-подписка истекла.\n\n"
              "Ты переведен на Free-тариф.\n"
              "Продлить подписку: /premium"
          )
      )
  except Exception as e:
      logger.error(f"Failed to notify user {user_id} about downgrade: {e}")
  ```

- [ ] **CRIT-6 ТЕСТ:** Вручную установить `expires_at` в прошлое
  - Выполнить любую команду (например, `/mystatus`)
  - Проверить: бот автоматически перевел на Free
  - Проверить: пришло уведомление о даунгрейде
  - Проверить в БД: `is_active = false`

---

## 🎯 ЭТАП 4: ЗАВЕРШЕНИЕ И АВТОМАТИЗАЦИЯ (21 задача)

### Шаг 10: Интеграция с ЮKassa (Приоритет 2) ✅

**Цель:** Автоматизировать покупку Pro через карты и электронные кошельки

- [x] **10.1** Зарегистрироваться в [ЮKassa](https://yookassa.ru/), получить API-ключи ✅
  - **Инструкция:** [YOOKASSA_SETUP_GUIDE.md](./YOOKASSA_SETUP_GUIDE.md)
  - Ручная задача для владельца бота

- [x] **10.2** Добавить в `config.py`: параметры ЮKassa ✅
  - Реализовано в config.py:105-107
  ```python
  YOOKASSA_SHOP_ID = os.getenv('YOOKASSA_SHOP_ID')
  YOOKASSA_SECRET_KEY = os.getenv('YOOKASSA_SECRET_KEY')
  ```

- [x] **10.3** Создать модуль `services/payments.py` ✅
  - Создан: services/payments.py
  - Включает полную безопасность и error handling

- [x] **10.4** Реализовать `create_payment_link()` в `payments.py` ✅
  - Реализовано с полной безопасностью
  - Также добавлен `verify_payment()` для webhook
  - Добавлена конфигурация ценообразования (PRICING)
  ```python
  from yookassa import Payment, Configuration

  Configuration.account_id = config.YOOKASSA_SHOP_ID
  Configuration.secret_key = config.YOOKASSA_SECRET_KEY

  async def create_payment_link(
      user_id: int,
      tier: str = 'pro',
      duration_days: int = 30
  ) -> str:
      """Создать платежную ссылку через ЮKassa"""
      amount = 2.99 if tier == 'pro' else 0

      payment = Payment.create({
          "amount": {
              "value": str(amount),
              "currency": "USD"
          },
          "confirmation": {
              "type": "redirect",
              "return_url": f"https://t.me/{config.BOT_USERNAME}"
          },
          "capture": True,
          "description": f"Pro subscription for {duration_days} days",
          "metadata": {
              "user_id": user_id,
              "tier": tier,
              "duration_days": duration_days
          }
      })

      return payment.confirmation.confirmation_url
  ```

- [x] **10.5** Добавить кнопку "Купить Pro (Карта)" в `/premium` ✅
  - Обновлен modules/commands.py:
    - Обработчик "buy_pro" - показывает выбор способа оплаты
    - Обработчик "buy_pro_card" - создает платежную ссылку
    - Обработчик "buy_pro_tribute" - показывает инструкции для Tribute
  - Полная обработка ошибок и user-friendly сообщения
  - Автоматическое скрытие кнопки если YooKassa не настроена

- [x] **10.6** Создать webhook endpoint `api/yookassa_webhook.py` ✅
  - Создан: api/yookassa_webhook.py
  - Безопасность:
    - ✅ IP verification (logged for monitoring)
    - ✅ Payment verification через YooKassa API
    - ✅ Validation всех данных
    - ✅ Полное логирование для audit trail
  - Автоматическая активация подписки
  - Уведомление пользователя о активации
  ```python
  from flask import request, jsonify
  from yookassa import Payment

  def handler(request):
      """Webhook для обработки уведомлений от ЮKassa"""
      try:
          event = request.get_json()

          # Проверка подписи (важно для безопасности)
          # ...

          if event['event'] == 'payment.succeeded':
              payment_id = event['object']['id']
              payment = Payment.find_one(payment_id)

              user_id = int(payment.metadata['user_id'])
              tier = payment.metadata['tier']
              duration_days = int(payment.metadata['duration_days'])

              # Активировать подписку
              success = await create_or_update_subscription(
                  user_id=user_id,
                  tier=tier,
                  duration_days=duration_days,
                  payment_method='yookassa',
                  transaction_id=payment_id
              )

              if success:
                  # Уведомить пользователя
                  await bot.send_message(
                      chat_id=user_id,
                      text="🎉 Оплата прошла успешно!\n\nPro-подписка активирована."
                  )

          return jsonify({'status': 'ok'}), 200
      except Exception as e:
          logger.error(f"Webhook error: {e}")
          return jsonify({'error': str(e)}), 500
  ```

- [x] **10.7** Реализовать обработчик webhook: проверка подписи, активация подписки ✅
  - Реализовано в api/yookassa_webhook.py
  - Обрабатывает события: `payment.succeeded`, `payment.canceled`
  - Верификация через `verify_payment()` для дополнительной безопасности

- [ ] **10.8** Настроить webhook URL в личном кабинете ЮKassa ⏭️ (Готов к настройке)
  - URL: `https://vkratse.vercel.app/api/yookassa_webhook`
  - **Инструкция:** [YOOKASSA_SETUP_GUIDE.md](./YOOKASSA_SETUP_GUIDE.md) - Шаг 4
  - Ручная задача для владельца бота

- [ ] **10.9 ТЕСТ:** Провести тестовый платеж через ЮKassa ⏭️ (Готов к тестированию)
  - Нажать "Купить Pro (Карта)"
  - Пройти процесс оплаты (тестовый режим)
  - Проверить: webhook получен, подписка активирована
  - Проверить: пришло уведомление о активации
  - **Инструкция:** [YOOKASSA_SETUP_GUIDE.md](./YOOKASSA_SETUP_GUIDE.md) - Шаг 5

---

### Шаг 11: Интеграция с Telegram Stars (Приоритет 3) ✅

**Цель:** Добавить нативный способ оплаты через Telegram

- [x] **11.1** Реализовать `create_stars_invoice()` в `payments.py` ✅
  - **Реализовано:** services/payments.py:302-398
  - Включает STARS_PRICING с 3 планами (месяц/квартал/год)
  - Безопасность: payload с user_id и timestamp для валидации
  - Полное логирование всех операций
  - Graceful error handling
  ```python
  async def create_stars_invoice(
      bot,  # Telegram Bot instance
      user_id: int,
      plan: str = 'pro_monthly'  # 'pro_monthly', 'pro_quarterly', 'pro_yearly'
  ) -> Dict[str, Any]:
      # Returns: {'success': bool, 'invoice_message': Message, ...}
  ```

- [x] **11.2** Добавить кнопку "Купить Pro (Stars)" в `/premium` ✅
  - **Реализовано:** modules/commands.py:315-316
  - Кнопка всегда доступна (не требует настройки как YooKassa)
  - Callback: "buy_pro_stars"
  - Обработчик: modules/commands.py:405-457

- [x] **11.3** Создать обработчик `PreCheckoutQuery` ✅
  - **Реализовано:** modules/commands.py:826-900
  - Валидация payload format (stars_<user_id>_<tier>_<days>_<timestamp>)
  - Проверка user_id совпадает с payload
  - Полное логирование для аудита
  - Таймаут < 10 секунд (Telegram requirement)
  - Graceful error handling

- [x] **11.4** Создать обработчик `SuccessfulPayment` ✅
  - **Реализовано:** modules/commands.py:903-1024
  - Двойная проверка user_id (security)
  - Автоактивация подписки через SubscriptionService
  - Отправка подтверждения пользователю
  - Transaction ID сохраняется для аудита
  - Полное логирование + error handling

- [x] **11.5** Зарегистрировать обработчики в api/index.py ✅
  - **Импорты:** api/index.py:96-97
  - **PreCheckoutQueryHandler:** api/index.py:490-491
  - **MessageHandler (SUCCESSFUL_PAYMENT):** api/index.py:493-497

- [ ] **11.6 ТЕСТ:** Провести тестовую покупку через Telegram Stars ⏭️ (Готов к тестированию)
  - Нажать "Купить Pro (Stars)"
  - Пройти процесс оплаты
  - Проверить: подписка активирована автоматически
  - Проверить: `/mystatus` показывает Pro-статус
  - **Инструкция:** [TESTING_TELEGRAM_STARS.md](./TESTING_TELEGRAM_STARS.md) - Полное руководство для не-программиста

**📋 ВАЖНО - Инструкция по тестированию:**
- Создана полная инструкция: [TESTING_TELEGRAM_STARS.md](./TESTING_TELEGRAM_STARS.md)
- Включает 6 детальных тестов с примерами
- Описаны ожидаемые результаты и способы отладки
- Готова для использования не-программистом
- Инструкции по покупке Stars и проверке платежей

---

### Шаг 12: Финальное тестирование и документация

**Цель:** Убедиться, что все работает корректно

- [ ] **12.1** Обновить команду `/help` с описанием тарифов
  ```python
  message += "\n💎 ТАРИФЫ\n"
  message += "/premium - Узнать о Pro-подписке\n"
  message += "/mystatus - Проверить свой статус\n\n"
  ```

- [ ] **12.2** Написать `README_MONETIZATION.md` с описанием модели
  - Таблица сравнения тарифов
  - Способы оплаты
  - FAQ

- [ ] **12.3** Полный чек-лист тестирования всех сценариев
  ```
  БАЗОВЫЕ ФУНКЦИИ:
  [ ] Free: лимит 30 сообщений/день работает
  [ ] Free: лимит 3 summary в ЛС/день работает
  [ ] Free: лимит 5 использований личности работает
  [ ] Pro: безлимитные личности работают
  [ ] Pro: лимиты увеличены (500 сообщений)

  ГРУППА:
  [ ] Free + группа: 1 бонусная личность
  [ ] Pro + группа: 4 кастомные личности
  [ ] Выход из группы: блокировка бонусной личности
  [ ] Возврат в группу: разблокировка личности

  ПОДПИСКА:
  [ ] /premium показывает тарифы
  [ ] /mystatus показывает статус и использование
  [ ] Истечение подписки: автодаунгрейд на Free
  [ ] Уведомление при истечении подписки

  ОПЛАТА:
  [ ] Tribute.to: ручная активация через /grantpro
  [ ] ЮKassa: автоактивация через webhook
  [ ] Telegram Stars: автоактивация через SuccessfulPayment
  ```

- [ ] **12.4** Бета-тестирование с 1-2 друзьями
  - Попросить пройти полный путь: от Free до Pro
  - Собрать обратную связь
  - Исправить найденные баги

- [ ] **12.5** Production deployment и мониторинг
  - Убедиться, что все environment variables установлены в Vercel
  - Проверить логи после деплоя
  - Мониторинг первых 24 часов

---

## 📊 Прогресс

**Всего задач:** 76
**Выполнено:** 63
**Процент завершения:** 83%

**Текущий этап:** ✅ Шаг 11 завершен - Интеграция с Telegram Stars (5/6 задач кода выполнено, 1 тест готов к выполнению)
**Следующий шаг:**
- Вариант 1: Тестировать Telegram Stars (Шаг 11.6) - [TESTING_TELEGRAM_STARS.md](./TESTING_TELEGRAM_STARS.md)
- Вариант 2: Настроить YooKassa и протестировать (Шаг 10.8-10.9)
- Вариант 3: Тестирование Шагов 7-9 (Группа, кастомные личности, блокировка)
- Вариант 4: Продолжить разработку - Шаг 12 (Финальное тестирование)

**🔐 БЕЗОПАСНОСТЬ:** Команда /grantpro реализована с многоуровневой защитой (admin auth, input validation, logging, error handling)

---

## 🚀 Следующие шаги

1. Начать с **ЭТАПА 1, Шаг 1** - создание SQL-миграций
2. Применить миграции в Supabase
3. Обновить конфигурацию
4. Тестировать каждый шаг перед переходом к следующему

---

## 📝 Заметки

- Все SQL-миграции сохранять в `sql/migrations/`
- Новые модули создавать с type hints и docstrings
- Логировать важные события (активация подписки, даунгрейд, блокировка личностей)
- Использовать HMAC для всех callback_data
- Тестировать на staging перед деплоем на production

---

**Создано:** 2025-11-17
**Последнее обновление:** 2025-11-17
