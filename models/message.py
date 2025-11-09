"""
Message model
Represents a single message from a chat
"""

from dataclasses import dataclass
from datetime import datetime
from typing import Optional


@dataclass
class Message:
    """Represents a chat message"""

    id: int
    chat_id: int
    user_id: Optional[int]
    username: Optional[str]  # Actually stores display name (first_name), not @username
    message_text: Optional[str]
    created_at: datetime

    @classmethod
    def from_dict(cls, data: dict) -> 'Message':
        """Create Message from database row"""
        return cls(
            id=data['id'],
            chat_id=data['chat_id'],
            user_id=data.get('user_id'),
            username=data.get('username'),
            message_text=data.get('message_text'),
            created_at=data['created_at'] if isinstance(data['created_at'], datetime)
                      else datetime.fromisoformat(data['created_at'].replace('Z', '+00:00'))
        )

    def to_dict(self) -> dict:
        """Convert to dictionary"""
        return {
            'id': self.id,
            'chat_id': self.chat_id,
            'user_id': self.user_id,
            'username': self.username,
            'message_text': self.message_text,
            'created_at': self.created_at.isoformat()
        }

    def __str__(self) -> str:
        """Format message for display"""
        username = self.username or f"User {self.user_id}"
        return f"{username}: {self.message_text}"
