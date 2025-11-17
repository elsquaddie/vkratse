-- ================================================
-- Analytics Queries for Dashboard
-- Готовые SQL запросы для анализа данных бота
-- ================================================

-- ================================================
-- 📊 ОБЩАЯ СТАТИСТИКА
-- ================================================

-- 1. Общее количество взаимодействий за все время
SELECT
  COUNT(*) as total_interactions,
  COUNT(DISTINCT user_id) as unique_users,
  COUNT(DISTINCT chat_id) as unique_chats,
  MIN(created_at) as first_interaction,
  MAX(created_at) as last_interaction
FROM button_analytics;

-- 2. Статистика по типам действий
SELECT
  action_type,
  COUNT(*) as count,
  COUNT(DISTINCT user_id) as unique_users,
  ROUND(100.0 * COUNT(*) / SUM(COUNT(*)) OVER (), 2) as percentage
FROM button_analytics
WHERE created_at >= NOW() - INTERVAL '30 days'
GROUP BY action_type
ORDER BY count DESC;

-- 3. Топ-20 действий за последние 30 дней
SELECT
  action_name,
  action_type,
  COUNT(*) as total_count,
  COUNT(DISTINCT user_id) as unique_users,
  COUNT(DISTINCT chat_id) as unique_chats,
  ROUND(COUNT(*)::NUMERIC / COUNT(DISTINCT user_id), 2) as avg_per_user
FROM button_analytics
WHERE created_at >= NOW() - INTERVAL '30 days'
GROUP BY action_name, action_type
ORDER BY total_count DESC
LIMIT 20;

-- ================================================
-- 🔘 КНОПКИ (Button Clicks)
-- ================================================

-- 4. Топ-10 кликов по кнопкам за последние 7 дней
SELECT
  action_name,
  button_text,
  COUNT(*) as total_clicks,
  COUNT(DISTINCT user_id) as unique_users,
  ROUND(100.0 * COUNT(*) / SUM(COUNT(*)) OVER (), 2) as click_share_percent
FROM button_analytics
WHERE action_type = 'button_click'
  AND created_at >= NOW() - INTERVAL '7 days'
GROUP BY action_name, button_text
ORDER BY total_clicks DESC
LIMIT 10;

-- 5. Популярность кнопок по дням (для графика)
SELECT
  DATE(created_at) as date,
  action_name,
  button_text,
  COUNT(*) as clicks
FROM button_analytics
WHERE action_type = 'button_click'
  AND created_at >= NOW() - INTERVAL '30 days'
GROUP BY DATE(created_at), action_name, button_text
ORDER BY date DESC, clicks DESC;

-- 6. Кнопки с самой высокой конверсией (кто кликнул - тот вернулся)
WITH button_users AS (
  SELECT
    action_name,
    user_id,
    MIN(created_at) as first_click
  FROM button_analytics
  WHERE action_type = 'button_click'
    AND created_at >= NOW() - INTERVAL '30 days'
  GROUP BY action_name, user_id
),
returning_users AS (
  SELECT
    bu.action_name,
    bu.user_id,
    CASE
      WHEN EXISTS (
        SELECT 1 FROM button_analytics ba
        WHERE ba.user_id = bu.user_id
          AND ba.created_at > bu.first_click + INTERVAL '1 hour'
      ) THEN 1 ELSE 0
    END as returned
  FROM button_users bu
)
SELECT
  action_name,
  COUNT(*) as total_users,
  SUM(returned) as returned_users,
  ROUND(100.0 * SUM(returned) / COUNT(*), 2) as return_rate_percent
FROM returning_users
GROUP BY action_name
HAVING COUNT(*) >= 5  -- Только кнопки с минимум 5 кликами
ORDER BY return_rate_percent DESC
LIMIT 10;

-- ================================================
-- ⚡ КОМАНДЫ (Commands)
-- ================================================

-- 7. Топ команд за последние 30 дней
SELECT
  action_name as command,
  COUNT(*) as usage_count,
  COUNT(DISTINCT user_id) as unique_users,
  ROUND(COUNT(*)::NUMERIC / COUNT(DISTINCT user_id), 2) as avg_per_user
FROM button_analytics
WHERE action_type = 'command'
  AND created_at >= NOW() - INTERVAL '30 days'
GROUP BY action_name
ORDER BY usage_count DESC;

-- 8. Первые команды новых пользователей (onboarding)
WITH first_commands AS (
  SELECT
    user_id,
    action_name,
    ROW_NUMBER() OVER (PARTITION BY user_id ORDER BY created_at) as command_rank
  FROM button_analytics
  WHERE action_type = 'command'
)
SELECT
  action_name as first_command,
  COUNT(*) as users_count,
  ROUND(100.0 * COUNT(*) / SUM(COUNT(*)) OVER (), 2) as percentage
FROM first_commands
WHERE command_rank = 1
GROUP BY action_name
ORDER BY users_count DESC;

-- ================================================
-- 🤖 AI ГЕНЕРАЦИИ (Summaries, Judges, Chat Responses)
-- ================================================

-- 9. Статистика AI генераций по типам
SELECT
  action_name as generation_type,
  COUNT(*) as total_generations,
  COUNT(DISTINCT user_id) as unique_users,
  COUNT(DISTINCT chat_id) as unique_chats
FROM button_analytics
WHERE action_type = 'ai_generation'
  AND created_at >= NOW() - INTERVAL '30 days'
GROUP BY action_name
ORDER BY total_generations DESC;

-- 10. Популярность личностей в AI генерациях
SELECT
  metadata->>'personality' as personality,
  COUNT(*) as usage_count,
  ROUND(100.0 * COUNT(*) / SUM(COUNT(*)) OVER (), 2) as usage_percent
FROM button_analytics
WHERE action_type = 'ai_generation'
  AND metadata->>'personality' IS NOT NULL
  AND created_at >= NOW() - INTERVAL '30 days'
GROUP BY metadata->>'personality'
ORDER BY usage_count DESC;

-- 11. Средняя длина контекста для AI генераций
SELECT
  action_name as generation_type,
  ROUND(AVG((metadata->>'messages_count')::INTEGER), 2) as avg_messages_count,
  ROUND(AVG((metadata->>'context_messages')::INTEGER), 2) as avg_context_messages
FROM button_analytics
WHERE action_type = 'ai_generation'
  AND (metadata->>'messages_count' IS NOT NULL OR metadata->>'context_messages' IS NOT NULL)
  AND created_at >= NOW() - INTERVAL '30 days'
GROUP BY action_name;

-- ================================================
-- 👥 ПОЛЬЗОВАТЕЛИ (Users)
-- ================================================

-- 12. Топ-10 самых активных пользователей
SELECT
  user_id,
  username,
  COUNT(*) as total_actions,
  COUNT(CASE WHEN action_type = 'button_click' THEN 1 END) as button_clicks,
  COUNT(CASE WHEN action_type = 'command' THEN 1 END) as commands,
  COUNT(CASE WHEN action_type = 'message' THEN 1 END) as messages,
  MAX(created_at) as last_activity
FROM button_analytics
WHERE created_at >= NOW() - INTERVAL '30 days'
GROUP BY user_id, username
ORDER BY total_actions DESC
LIMIT 10;

-- 13. Новые пользователи по дням
SELECT
  DATE(first_action) as date,
  COUNT(*) as new_users
FROM (
  SELECT
    user_id,
    MIN(created_at) as first_action
  FROM button_analytics
  GROUP BY user_id
) as user_first_actions
WHERE first_action >= NOW() - INTERVAL '30 days'
GROUP BY DATE(first_action)
ORDER BY date DESC;

-- 14. Retention: сколько пользователей вернулись через N дней
WITH user_cohorts AS (
  SELECT
    user_id,
    DATE(MIN(created_at)) as cohort_date
  FROM button_analytics
  GROUP BY user_id
),
user_activity AS (
  SELECT
    ba.user_id,
    uc.cohort_date,
    DATE(ba.created_at) as activity_date,
    DATE(ba.created_at) - uc.cohort_date as days_since_cohort
  FROM button_analytics ba
  JOIN user_cohorts uc ON ba.user_id = uc.user_id
)
SELECT
  days_since_cohort,
  COUNT(DISTINCT user_id) as active_users
FROM user_activity
WHERE cohort_date >= NOW() - INTERVAL '30 days'
  AND days_since_cohort BETWEEN 0 AND 30
GROUP BY days_since_cohort
ORDER BY days_since_cohort;

-- ================================================
-- 📈 ВОРОНКИ (Funnels)
-- ================================================

-- 15. Воронка: /start → выбор личности → первое сообщение
WITH funnel_steps AS (
  SELECT
    user_id,
    MAX(CASE WHEN action_name = '/start' THEN 1 ELSE 0 END) as did_start,
    MAX(CASE WHEN action_name LIKE '%personality%' THEN 1 ELSE 0 END) as selected_personality,
    MAX(CASE WHEN action_type = 'message' AND action_name = 'message_text' THEN 1 ELSE 0 END) as sent_message
  FROM button_analytics
  WHERE created_at >= NOW() - INTERVAL '30 days'
  GROUP BY user_id
)
SELECT
  'Step 1: Started bot' as step,
  SUM(did_start) as users,
  100.0 as conversion_rate
FROM funnel_steps
UNION ALL
SELECT
  'Step 2: Selected personality',
  SUM(selected_personality),
  ROUND(100.0 * SUM(selected_personality) / NULLIF(SUM(did_start), 0), 2)
FROM funnel_steps
UNION ALL
SELECT
  'Step 3: Sent first message',
  SUM(sent_message),
  ROUND(100.0 * SUM(sent_message) / NULLIF(SUM(selected_personality), 0), 2)
FROM funnel_steps;

-- 16. Воронка: групповое саммари
WITH summary_funnel AS (
  SELECT
    user_id,
    chat_id,
    MAX(CASE WHEN action_name = 'group_summary' THEN 1 ELSE 0 END) as clicked_summary,
    MAX(CASE WHEN action_name LIKE 'summary_personality%' THEN 1 ELSE 0 END) as selected_personality,
    MAX(CASE WHEN action_type = 'ai_generation' AND action_name = 'summary' THEN 1 ELSE 0 END) as got_summary
  FROM button_analytics
  WHERE created_at >= NOW() - INTERVAL '30 days'
  GROUP BY user_id, chat_id
)
SELECT
  'Clicked Summary Button' as step,
  SUM(clicked_summary) as users,
  100.0 as conversion_rate
FROM summary_funnel
UNION ALL
SELECT
  'Selected Personality',
  SUM(selected_personality),
  ROUND(100.0 * SUM(selected_personality) / NULLIF(SUM(clicked_summary), 0), 2)
FROM summary_funnel
UNION ALL
SELECT
  'Received Summary',
  SUM(got_summary),
  ROUND(100.0 * SUM(got_summary) / NULLIF(SUM(selected_personality), 0), 2)
FROM summary_funnel;

-- ================================================
-- 🕐 ВРЕМЕННЫЕ ПАТТЕРНЫ (Time Patterns)
-- ================================================

-- 17. Активность по часам дня (для определения пиковых часов)
SELECT
  EXTRACT(HOUR FROM created_at) as hour,
  COUNT(*) as total_actions,
  COUNT(DISTINCT user_id) as unique_users,
  ROUND(COUNT(*)::NUMERIC / COUNT(DISTINCT user_id), 2) as avg_actions_per_user
FROM button_analytics
WHERE created_at >= NOW() - INTERVAL '7 days'
GROUP BY EXTRACT(HOUR FROM created_at)
ORDER BY hour;

-- 18. Активность по дням недели
SELECT
  TO_CHAR(created_at, 'Day') as day_of_week,
  EXTRACT(DOW FROM created_at) as dow_number,  -- 0=Sunday, 6=Saturday
  COUNT(*) as total_actions,
  COUNT(DISTINCT user_id) as unique_users
FROM button_analytics
WHERE created_at >= NOW() - INTERVAL '30 days'
GROUP BY TO_CHAR(created_at, 'Day'), EXTRACT(DOW FROM created_at)
ORDER BY dow_number;

-- 19. Тренд активности: сравнение недель
WITH weekly_stats AS (
  SELECT
    DATE_TRUNC('week', created_at) as week,
    COUNT(*) as total_actions,
    COUNT(DISTINCT user_id) as unique_users
  FROM button_analytics
  WHERE created_at >= NOW() - INTERVAL '8 weeks'
  GROUP BY DATE_TRUNC('week', created_at)
)
SELECT
  week,
  total_actions,
  unique_users,
  LAG(total_actions) OVER (ORDER BY week) as prev_week_actions,
  ROUND(
    100.0 * (total_actions - LAG(total_actions) OVER (ORDER BY week)) /
    NULLIF(LAG(total_actions) OVER (ORDER BY week), 0),
    2
  ) as growth_percent
FROM weekly_stats
ORDER BY week DESC;

-- ================================================
-- 💬 ЧАТЫ (Chats)
-- ================================================

-- 20. Топ-10 самых активных чатов
SELECT
  ba.chat_id,
  ba.chat_type,
  cm.chat_title,
  COUNT(*) as total_actions,
  COUNT(DISTINCT ba.user_id) as unique_users,
  MAX(ba.created_at) as last_activity
FROM button_analytics ba
LEFT JOIN chat_metadata cm ON ba.chat_id = cm.chat_id
WHERE ba.created_at >= NOW() - INTERVAL '30 days'
GROUP BY ba.chat_id, ba.chat_type, cm.chat_title
ORDER BY total_actions DESC
LIMIT 10;

-- 21. Распределение активности по типам чатов
SELECT
  chat_type,
  COUNT(*) as total_actions,
  COUNT(DISTINCT user_id) as unique_users,
  COUNT(DISTINCT chat_id) as unique_chats,
  ROUND(100.0 * COUNT(*) / SUM(COUNT(*)) OVER (), 2) as percentage
FROM button_analytics
WHERE created_at >= NOW() - INTERVAL '30 days'
  AND chat_type IS NOT NULL
GROUP BY chat_type
ORDER BY total_actions DESC;

-- ================================================
-- ❌ ОШИБКИ (Errors)
-- ================================================

-- 22. Топ ошибок за последние 7 дней
SELECT
  action_name as error_type,
  metadata->>'error_message' as error_message,
  COUNT(*) as error_count,
  COUNT(DISTINCT user_id) as affected_users,
  MAX(created_at) as last_occurrence
FROM button_analytics
WHERE action_type = 'error'
  AND created_at >= NOW() - INTERVAL '7 days'
GROUP BY action_name, metadata->>'error_message'
ORDER BY error_count DESC
LIMIT 20;

-- ================================================
-- 🎯 ПЕРСОНАЛИЗИРОВАННЫЕ ЗАПРОСЫ
-- ================================================

-- 23. Путь конкретного пользователя (User Journey)
-- Замените 123456 на реальный user_id
SELECT
  created_at,
  action_type,
  action_name,
  button_text,
  chat_type,
  metadata
FROM button_analytics
WHERE user_id = 123456  -- ЗАМЕНИТЕ НА РЕАЛЬНЫЙ user_id
  AND created_at >= NOW() - INTERVAL '7 days'
ORDER BY created_at ASC;

-- 24. Сессии пользователя с деталями
SELECT
  us.id as session_id,
  us.user_id,
  us.chat_id,
  us.started_at,
  us.ended_at,
  us.last_activity,
  us.total_actions,
  EXTRACT(EPOCH FROM (COALESCE(us.ended_at, us.last_activity) - us.started_at)) / 60 as duration_minutes
FROM user_sessions us
WHERE us.user_id = 123456  -- ЗАМЕНИТЕ НА РЕАЛЬНЫЙ user_id
ORDER BY us.started_at DESC
LIMIT 10;

-- ================================================
-- 🧹 MAINTENANCE QUERIES
-- ================================================

-- 25. Размер таблицы аналитики
SELECT
  pg_size_pretty(pg_total_relation_size('button_analytics')) as table_size,
  (SELECT COUNT(*) FROM button_analytics) as total_rows,
  (SELECT COUNT(*) FROM button_analytics WHERE created_at >= NOW() - INTERVAL '30 days') as rows_last_30d;

-- 26. Очистка старых данных (запускать вручную или через cron)
-- SELECT cleanup_old_analytics();

-- 27. Пересчёт статистики для оптимизации запросов
-- ANALYZE button_analytics;
-- ANALYZE user_sessions;

-- ================================================
-- ГОТОВО!
-- Используйте эти запросы в Supabase SQL Editor
-- или подключите к BI инструменту (Metabase, Data Studio)
-- ================================================
