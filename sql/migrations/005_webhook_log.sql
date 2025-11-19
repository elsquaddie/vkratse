-- ================================================
-- Migration 005: Webhook Idempotency Log
-- ================================================
-- Создаёт таблицу для предотвращения duplicate processing webhooks
-- от Telegram и YooKassa

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

-- Комментарии
COMMENT ON TABLE webhook_log IS 'Лог обработанных webhooks для idempotency check';
COMMENT ON COLUMN webhook_log.webhook_type IS 'Тип webhook: telegram или yookassa';
COMMENT ON COLUMN webhook_log.webhook_id IS 'Уникальный ID: update_id или payment_id';
COMMENT ON COLUMN webhook_log.payload IS 'Полный payload для отладки (опционально)';

-- Auto-cleanup старых записей (>7 дней)
-- Запускать через cron или manual cleanup script:
-- DELETE FROM webhook_log WHERE processed_at < NOW() - INTERVAL '7 days';
