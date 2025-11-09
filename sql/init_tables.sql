-- ================================================
-- SQL Script: Initialization Tables
-- Project: Что было в чате (@chto_bilo_v_chate_bot)
-- Description: Создание всех таблиц для Supabase
-- ================================================

-- ================================================
-- 1. Таблица: messages
-- Хранит все сообщения из чатов
-- Автоочистка: 7 дней
-- ================================================
CREATE TABLE IF NOT EXISTS messages (
  id BIGSERIAL PRIMARY KEY,
  chat_id BIGINT NOT NULL,
  user_id BIGINT,
  username TEXT,
  message_text TEXT,
  created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Индекс для быстрой выборки по чату и времени
CREATE INDEX IF NOT EXISTS idx_messages_chat_time ON messages(chat_id, created_at DESC);

-- Индекс для поиска по юзеру в чате
CREATE INDEX IF NOT EXISTS idx_messages_chat_user ON messages(chat_id, user_id);

-- ================================================
-- 2. Таблица: personalities
-- Базовые и кастомные личности AI
-- ================================================
CREATE TABLE IF NOT EXISTS personalities (
  id SERIAL PRIMARY KEY,
  name VARCHAR(100) UNIQUE NOT NULL,           -- 'neutral', 'bydlan', 'philosopher', etc
  display_name VARCHAR(100) NOT NULL,          -- 'Нейтральный', 'Быдлан', 'Философ'
  system_prompt TEXT NOT NULL,                 -- Промпт для AI (sanitized!)
  is_custom BOOLEAN DEFAULT FALSE,             -- Кастомная от юзера?
  created_by_user_id BIGINT,                   -- Кто создал (для кастомных)
  is_active BOOLEAN DEFAULT TRUE,              -- Активна ли личность
  created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Индекс для быстрого поиска активных личностей
CREATE INDEX IF NOT EXISTS idx_personalities_active ON personalities(is_active) WHERE is_active = TRUE;

-- Индекс для поиска кастомных личностей юзера
CREATE INDEX IF NOT EXISTS idx_personalities_custom ON personalities(created_by_user_id) WHERE is_custom = TRUE;

-- ================================================
-- 3. Таблица: user_settings
-- Настройки каждого пользователя
-- ================================================
CREATE TABLE IF NOT EXISTS user_settings (
  user_id BIGINT PRIMARY KEY,
  username TEXT,
  selected_personality VARCHAR(100) DEFAULT 'neutral',  -- Дефолт: нейтральная личность
  created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
  updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- ================================================
-- 4. Таблица: chat_metadata
-- Метаданные о чатах где есть бот
-- ================================================
CREATE TABLE IF NOT EXISTS chat_metadata (
  chat_id BIGINT PRIMARY KEY,
  chat_title TEXT,
  chat_type TEXT,                              -- 'group', 'supergroup', 'private'
  bot_added_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
  last_activity TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Индекс для поиска по типу чата
CREATE INDEX IF NOT EXISTS idx_chat_metadata_type ON chat_metadata(chat_type);

-- ================================================
-- 5. Таблица: cooldowns
-- Защита от спама (cooldown на команды)
-- ================================================
CREATE TABLE IF NOT EXISTS cooldowns (
  chat_id BIGINT PRIMARY KEY,
  last_summary_at TIMESTAMP WITH TIME ZONE,
  last_judge_at TIMESTAMP WITH TIME ZONE,
  updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- ================================================
-- 6. Таблица: analytics (опционально)
-- Статистика использования
-- ================================================
CREATE TABLE IF NOT EXISTS analytics (
  id BIGSERIAL PRIMARY KEY,
  user_id BIGINT,
  chat_id BIGINT,
  event_type VARCHAR(50),                      -- 'summary', 'judge', 'personality_change'
  metadata JSONB,                              -- Дополнительные данные
  created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Индекс для аналитики по событиям
CREATE INDEX IF NOT EXISTS idx_analytics_event ON analytics(event_type, created_at DESC);

-- Индекс для аналитики по юзеру
CREATE INDEX IF NOT EXISTS idx_analytics_user ON analytics(user_id, created_at DESC);

-- ================================================
-- ФУНКЦИЯ: Автоочистка старых сообщений (7 дней)
-- ================================================
CREATE OR REPLACE FUNCTION delete_old_messages()
RETURNS void AS $$
BEGIN
  DELETE FROM messages
  WHERE created_at < NOW() - INTERVAL '7 days';
END;
$$ LANGUAGE plpgsql;

-- ================================================
-- ФУНКЦИЯ: Обновление updated_at при изменении
-- ================================================
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
  NEW.updated_at = NOW();
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Триггер для user_settings
DROP TRIGGER IF EXISTS update_user_settings_updated_at ON user_settings;
CREATE TRIGGER update_user_settings_updated_at
  BEFORE UPDATE ON user_settings
  FOR EACH ROW
  EXECUTE FUNCTION update_updated_at_column();

-- Триггер для cooldowns
DROP TRIGGER IF EXISTS update_cooldowns_updated_at ON cooldowns;
CREATE TRIGGER update_cooldowns_updated_at
  BEFORE UPDATE ON cooldowns
  FOR EACH ROW
  EXECUTE FUNCTION update_updated_at_column();

-- ================================================
-- ПРИМЕЧАНИЕ:
-- Для автоочистки сообщений нужно настроить cron job:
--
-- Вариант 1: pg_cron (если доступен в Supabase)
-- SELECT cron.schedule('delete-old-messages', '0 2 * * *', 'SELECT delete_old_messages()');
--
-- Вариант 2: Вызывать delete_old_messages() из Python кода
-- ================================================

-- ================================================
-- ГОТОВО!
-- Выполни этот скрипт в Supabase SQL Editor
-- Затем выполни sql/seed_personalities.sql
-- ================================================
