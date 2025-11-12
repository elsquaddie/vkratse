"""
Personality model
Represents an AI personality (base or custom)
"""

from dataclasses import dataclass
from datetime import datetime
from typing import Optional


@dataclass
class Personality:
    """Represents an AI personality"""

    id: int
    name: str
    display_name: str
    system_prompt: str
    emoji: str
    is_custom: bool
    created_by_user_id: Optional[int]
    is_active: bool
    created_at: datetime
    greeting_message: Optional[str] = None  # Added by migration 001_add_greetings.sql

    @classmethod
    def from_dict(cls, data: dict) -> 'Personality':
        """Create Personality from database row"""
        return cls(
            id=data['id'],
            name=data['name'],
            display_name=data['display_name'],
            system_prompt=data['system_prompt'],
            emoji=data.get('emoji', '🎭'),
            is_custom=data.get('is_custom', False),
            created_by_user_id=data.get('created_by_user_id'),
            is_active=data.get('is_active', True),
            created_at=data['created_at'] if isinstance(data['created_at'], datetime)
                      else datetime.fromisoformat(data['created_at'].replace('Z', '+00:00')),
            greeting_message=data.get('greeting_message')
        )

    def to_dict(self) -> dict:
        """Convert to dictionary"""
        return {
            'id': self.id,
            'name': self.name,
            'display_name': self.display_name,
            'system_prompt': self.system_prompt,
            'emoji': self.emoji,
            'is_custom': self.is_custom,
            'created_by_user_id': self.created_by_user_id,
            'is_active': self.is_active,
            'created_at': self.created_at.isoformat(),
            'greeting_message': self.greeting_message
        }

    def __str__(self) -> str:
        """Format for display"""
        return f"{self.emoji} {self.display_name}"
