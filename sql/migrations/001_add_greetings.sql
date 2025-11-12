-- Migration: Add greeting_message column to personalities table
-- Date: 2025-11-12
-- Description: Adds personalized greeting messages for each personality

-- Add greeting_message column if it doesn't exist
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'personalities'
        AND column_name = 'greeting_message'
    ) THEN
        ALTER TABLE personalities
        ADD COLUMN greeting_message TEXT DEFAULT NULL;

        RAISE NOTICE 'Added greeting_message column to personalities table';
    ELSE
        RAISE NOTICE 'greeting_message column already exists, skipping';
    END IF;
END $$;

-- Update base personalities with their greetings
UPDATE personalities
SET greeting_message = 'Йоу, братан! Ну че, приехали? Че надо?
Не стой как столб, давай базарь чё к чему! 🏭'
WHERE name = 'bydlan' AND greeting_message IS NULL;

UPDATE personalities
SET greeting_message = 'Приветствую тебя, путник. Ты пришёл в поисках истины,
или просто заблудился в лабиринте бытия? 🧙'
WHERE name = 'philosopher' AND greeting_message IS NULL;

UPDATE personalities
SET greeting_message = 'Йоу, пацан! Заходи, не стесняйся.
Че надо? По делу или так, потрепаться? 👟'
WHERE name = 'gopnik' AND greeting_message IS NULL;

UPDATE personalities
SET greeting_message = 'Здравствуйте! Рад приветствовать вас.
У меня сегодня отличное настроение - яхта пришвартовалась в Монако. Чем могу помочь? 💼'
WHERE name = 'oligarch' AND greeting_message IS NULL;

UPDATE personalities
SET greeting_message = 'Эй, народ! Готовы посмеяться?
Обещаю, будет весело! Ну или хотя бы не скучно 😂'
WHERE name = 'comedian' AND greeting_message IS NULL;

UPDATE personalities
SET greeting_message = 'Приветствую! Готов к научной дискуссии.
У меня тут интересные данные по вашему запросу... 🔬'
WHERE name = 'scientist' AND greeting_message IS NULL;

UPDATE personalities
SET greeting_message = 'Здравствуйте! Я готов помочь вам.
Чем могу быть полезен? 🎓'
WHERE name = 'neutral' AND greeting_message IS NULL;

-- Verify migration
DO $$
DECLARE
    greeting_count INTEGER;
BEGIN
    SELECT COUNT(*) INTO greeting_count
    FROM personalities
    WHERE greeting_message IS NOT NULL AND is_custom = FALSE;

    RAISE NOTICE 'Migration completed. % base personalities have greetings', greeting_count;
END $$;
