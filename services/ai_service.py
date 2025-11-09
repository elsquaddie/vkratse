"""
AI Service
Wrapper around Anthropic Claude API
"""

from typing import List
import anthropic
import config
from config import logger
from models import Message, Personality


class AIService:
    """Service for AI operations using Claude"""

    def __init__(self):
        """Initialize Anthropic client"""
        self.client = anthropic.Anthropic(api_key=config.ANTHROPIC_API_KEY)
        self.model = config.ANTHROPIC_MODEL
        logger.info("AIService initialized")

    def generate_summary(
        self,
        messages: List[Message],
        personality: Personality,
        period_description: str = "последние сообщения"
    ) -> str:
        """
        Generate a summary of chat messages using specified personality

        Args:
            messages: List of messages to summarize
            personality: AI personality to use
            period_description: Description of time period (e.g., "за последние 2 часа")

        Returns:
            Summary text
        """
        if not messages:
            return "📭 В чате пока нет сообщений за этот период."

        # Format messages for the prompt
        formatted_messages = self._format_messages(messages)

        # Create prompt
        prompt = f"""
{personality.system_prompt}

Твоя задача: сделать краткий саммари чата.

Период: {period_description}
Количество сообщений: {len(messages)}

Сообщения из чата:
{formatted_messages}

Требования к саммари:
1. Кратко опиши основные темы обсуждения
2. Выдели ключевые моменты или решения
3. Укажи настроение беседы (если уместно)
4. Отвечай в стиле своей личности
5. Саммари должен быть коротким (3-5 предложений обычно)

Твой саммари:
"""

        try:
            # Call Claude API
            response = self.client.messages.create(
                model=self.model,
                max_tokens=1024,
                messages=[
                    {"role": "user", "content": prompt}
                ]
            )

            summary = response.content[0].text.strip()
            logger.info(f"Generated summary using personality '{personality.name}'")
            return summary

        except Exception as e:
            logger.error(f"Error generating summary: {e}")
            return f"❌ Ошибка при генерации саммари: {str(e)}"

    def generate_judge_verdict(
        self,
        dispute_text: str,
        messages: List[Message],
        personality: Personality
    ) -> str:
        """
        Generate a verdict for a dispute

        Args:
            dispute_text: Description of the dispute
            messages: Context messages from the chat
            personality: AI personality to use

        Returns:
            Verdict text
        """
        formatted_messages = self._format_messages(messages) if messages else "Нет контекста"

        prompt = f"""
{personality.system_prompt}

Твоя задача: рассудить спор.

Спор: {dispute_text}

Контекст из чата (последние сообщения):
{formatted_messages}

Требования к вердикту:
1. Кратко опиши позиции сторон
2. Рассуди, кто прав и почему (или оба правы/не правы)
3. Дай своё заключение
4. Отвечай в стиле своей личности
5. Будь справедливым, но можешь добавить юмор

Твой вердикт:
"""

        try:
            response = self.client.messages.create(
                model=self.model,
                max_tokens=1024,
                messages=[
                    {"role": "user", "content": prompt}
                ]
            )

            verdict = response.content[0].text.strip()
            logger.info(f"Generated verdict using personality '{personality.name}'")
            return verdict

        except Exception as e:
            logger.error(f"Error generating verdict: {e}")
            return f"❌ Ошибка при генерации вердикта: {str(e)}"

    def _format_messages(self, messages: List[Message]) -> str:
        """
        Format messages for AI prompt

        Args:
            messages: List of messages

        Returns:
            Formatted string
        """
        formatted = []
        for msg in messages:
            username = msg.username or f"User{msg.user_id}"
            text = msg.message_text or "[нет текста]"
            formatted.append(f"{username}: {text}")

        return "\n".join(formatted)
