-- ================================================
-- Migration: Button Analytics Enhancement
-- Description: Расширенная аналитика для трекинга взаимодействий с кнопками
-- Created: 2025-11-17
-- ================================================

-- ================================================
-- 1. Таблица: button_analytics
-- Детальное логирование всех кликов по кнопкам
-- ================================================
CREATE TABLE IF NOT EXISTS button_analytics (
  id BIGSERIAL PRIMARY KEY,

  -- Пользователь и контекст
  user_id BIGINT NOT NULL,
  username TEXT,
  chat_id BIGINT NOT NULL,
  chat_type TEXT,                               -- 'private', 'group', 'supergroup'

  -- Действие
  action_type VARCHAR(100) NOT NULL,            -- 'button_click', 'command', 'message'
  action_name VARCHAR(100) NOT NULL,            -- 'direct_chat', 'select_personality', '/start'
  button_text TEXT,                             -- Текст кнопки (если это кнопка)
  callback_data TEXT,                           -- Оригинальный callback_data

  -- Контекст и путь пользователя
  previous_action VARCHAR(100),                 -- Предыдущее действие (для user journey)
  session_id UUID,                              -- ID сессии (для группировки действий)

  -- Метаданные (JSONB для гибкости)
  metadata JSONB DEFAULT '{}'::jsonb,           -- Любые дополнительные данные

  -- Временные метки
  created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Индексы для быстрых запросов
CREATE INDEX IF NOT EXISTS idx_button_analytics_action ON button_analytics(action_name, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_button_analytics_user ON button_analytics(user_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_button_analytics_chat ON button_analytics(chat_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_button_analytics_type ON button_analytics(action_type, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_button_analytics_session ON button_analytics(session_id) WHERE session_id IS NOT NULL;

-- Индекс для анализа по дате
CREATE INDEX IF NOT EXISTS idx_button_analytics_date ON button_analytics(DATE(created_at), action_name);

-- ================================================
-- 2. Расширение существующей таблицы analytics
-- Добавляем новые поля для совместимости
-- ================================================
ALTER TABLE analytics
  ADD COLUMN IF NOT EXISTS action_name VARCHAR(100),
  ADD COLUMN IF NOT EXISTS button_text TEXT,
  ADD COLUMN IF NOT EXISTS chat_type TEXT,
  ADD COLUMN IF NOT EXISTS session_id UUID;

-- Индекс для новых полей
CREATE INDEX IF NOT EXISTS idx_analytics_action_name ON analytics(action_name) WHERE action_name IS NOT NULL;

-- ================================================
-- 3. Таблица: user_sessions
-- Трекинг пользовательских сессий для анализа путей
-- ================================================
CREATE TABLE IF NOT EXISTS user_sessions (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id BIGINT NOT NULL,
  chat_id BIGINT NOT NULL,
  started_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
  last_activity TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
  ended_at TIMESTAMP WITH TIME ZONE,
  total_actions INT DEFAULT 0,
  metadata JSONB DEFAULT '{}'::jsonb
);

CREATE INDEX IF NOT EXISTS idx_user_sessions_user ON user_sessions(user_id, started_at DESC);
CREATE INDEX IF NOT EXISTS idx_user_sessions_activity ON user_sessions(last_activity DESC);

-- ================================================
-- 4. View: популярные кнопки за последние 7 дней
-- ================================================
CREATE OR REPLACE VIEW popular_buttons_7d AS
SELECT
  action_name,
  button_text,
  COUNT(*) as total_clicks,
  COUNT(DISTINCT user_id) as unique_users,
  COUNT(DISTINCT chat_id) as unique_chats,
  DATE_TRUNC('day', created_at) as date
FROM button_analytics
WHERE created_at >= NOW() - INTERVAL '7 days'
  AND action_type = 'button_click'
GROUP BY action_name, button_text, DATE_TRUNC('day', created_at)
ORDER BY total_clicks DESC;

-- ================================================
-- 5. View: воронка конверсии (funnel)
-- ================================================
CREATE OR REPLACE VIEW conversion_funnel AS
WITH user_actions AS (
  SELECT
    user_id,
    action_name,
    created_at,
    ROW_NUMBER() OVER (PARTITION BY user_id ORDER BY created_at) as action_number
  FROM button_analytics
  WHERE created_at >= NOW() - INTERVAL '30 days'
)
SELECT
  action_number,
  action_name,
  COUNT(DISTINCT user_id) as users_count,
  LAG(COUNT(DISTINCT user_id)) OVER (ORDER BY action_number) as previous_step_users,
  ROUND(
    100.0 * COUNT(DISTINCT user_id) /
    LAG(COUNT(DISTINCT user_id)) OVER (ORDER BY action_number),
    2
  ) as conversion_rate_percent
FROM user_actions
GROUP BY action_number, action_name
ORDER BY action_number;

-- ================================================
-- 6. View: активность по часам (для определения пиковых часов)
-- ================================================
CREATE OR REPLACE VIEW activity_by_hour AS
SELECT
  EXTRACT(HOUR FROM created_at) as hour,
  COUNT(*) as total_actions,
  COUNT(DISTINCT user_id) as unique_users,
  action_type
FROM button_analytics
WHERE created_at >= NOW() - INTERVAL '7 days'
GROUP BY EXTRACT(HOUR FROM created_at), action_type
ORDER BY hour, action_type;

-- ================================================
-- 7. Функция: очистка старых данных аналитики (опционально)
-- Хранить аналитику только за последние 90 дней
-- ================================================
CREATE OR REPLACE FUNCTION cleanup_old_analytics()
RETURNS void AS $$
BEGIN
  DELETE FROM button_analytics
  WHERE created_at < NOW() - INTERVAL '90 days';

  DELETE FROM analytics
  WHERE created_at < NOW() - INTERVAL '90 days';
END;
$$ LANGUAGE plpgsql;

-- ================================================
-- 8. Функция: получить топ действий за период
-- ================================================
CREATE OR REPLACE FUNCTION get_top_actions(
  days_back INT DEFAULT 7,
  limit_count INT DEFAULT 10
)
RETURNS TABLE (
  action_name VARCHAR(100),
  total_clicks BIGINT,
  unique_users BIGINT,
  avg_per_user NUMERIC
) AS $$
BEGIN
  RETURN QUERY
  SELECT
    ba.action_name,
    COUNT(*) as total_clicks,
    COUNT(DISTINCT ba.user_id) as unique_users,
    ROUND(COUNT(*)::NUMERIC / NULLIF(COUNT(DISTINCT ba.user_id), 0), 2) as avg_per_user
  FROM button_analytics ba
  WHERE ba.created_at >= NOW() - (days_back || ' days')::INTERVAL
  GROUP BY ba.action_name
  ORDER BY total_clicks DESC
  LIMIT limit_count;
END;
$$ LANGUAGE plpgsql;

-- ================================================
-- 9. Триггер для автообновления user_sessions.last_activity
-- ================================================
CREATE OR REPLACE FUNCTION update_session_last_activity()
RETURNS TRIGGER AS $$
BEGIN
  UPDATE user_sessions
  SET
    last_activity = NEW.created_at,
    total_actions = total_actions + 1
  WHERE id = NEW.session_id
    AND ended_at IS NULL;

  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trigger_update_session_activity ON button_analytics;
CREATE TRIGGER trigger_update_session_activity
  AFTER INSERT ON button_analytics
  FOR EACH ROW
  WHEN (NEW.session_id IS NOT NULL)
  EXECUTE FUNCTION update_session_last_activity();

-- ================================================
-- ГОТОВО!
-- Теперь у вас есть:
-- 1. Детальная таблица button_analytics
-- 2. Расширенная таблица analytics
-- 3. Таблица user_sessions для трекинга путей
-- 4. Views для быстрого анализа:
--    - popular_buttons_7d
--    - conversion_funnel
--    - activity_by_hour
-- 5. Функции для получения статистики
--
-- Выполните этот скрипт в Supabase SQL Editor!
-- ================================================
