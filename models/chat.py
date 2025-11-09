"""
Chat model
Represents a Telegram chat where bot is present
"""

from dataclasses import dataclass
from datetime import datetime
from typing import Optional


@dataclass
class Chat:
    """Represents a Telegram chat"""

    chat_id: int
    chat_title: Optional[str]
    chat_type: str
    bot_added_at: datetime
    last_activity: datetime

    @classmethod
    def from_dict(cls, data: dict) -> 'Chat':
        """Create Chat from database row"""
        return cls(
            chat_id=data['chat_id'],
            chat_title=data.get('chat_title'),
            chat_type=data.get('chat_type', 'group'),
            bot_added_at=data['bot_added_at'] if isinstance(data['bot_added_at'], datetime)
                        else datetime.fromisoformat(data['bot_added_at'].replace('Z', '+00:00')),
            last_activity=data['last_activity'] if isinstance(data['last_activity'], datetime)
                         else datetime.fromisoformat(data['last_activity'].replace('Z', '+00:00'))
        )

    def to_dict(self) -> dict:
        """Convert to dictionary"""
        return {
            'chat_id': self.chat_id,
            'chat_title': self.chat_title,
            'chat_type': self.chat_type,
            'bot_added_at': self.bot_added_at.isoformat(),
            'last_activity': self.last_activity.isoformat()
        }

    @property
    def emoji(self) -> str:
        """Get emoji for chat type"""
        emoji_map = {
            'private': '👤',
            'group': '👥',
            'supergroup': '👥',
            'channel': '📢'
        }
        return emoji_map.get(self.chat_type, '💬')

    def __str__(self) -> str:
        """Format for display"""
        return f"{self.emoji} {self.chat_title or f'Chat {self.chat_id}'}"
