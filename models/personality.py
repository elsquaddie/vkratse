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
    is_custom: bool
    created_by_user_id: Optional[int]
    is_active: bool
    created_at: datetime

    @classmethod
    def from_dict(cls, data: dict) -> 'Personality':
        """Create Personality from database row"""
        return cls(
            id=data['id'],
            name=data['name'],
            display_name=data['display_name'],
            system_prompt=data['system_prompt'],
            is_custom=data.get('is_custom', False),
            created_by_user_id=data.get('created_by_user_id'),
            is_active=data.get('is_active', True),
            created_at=data['created_at'] if isinstance(data['created_at'], datetime)
                      else datetime.fromisoformat(data['created_at'].replace('Z', '+00:00'))
        )

    def to_dict(self) -> dict:
        """Convert to dictionary"""
        return {
            'id': self.id,
            'name': self.name,
            'display_name': self.display_name,
            'system_prompt': self.system_prompt,
            'is_custom': self.is_custom,
            'created_by_user_id': self.created_by_user_id,
            'is_active': self.is_active,
            'created_at': self.created_at.isoformat()
        }

    @property
    def emoji(self) -> str:
        """Get emoji for personality"""
        emoji_map = {
            'neutral': '🎓',
            'bydlan': '🏭',
            'philosopher': '🧙',
            'gopnik': '👟',
            'oligarch': '💼',
            'comedian': '😂',
            'scientist': '🔬'
        }
        return emoji_map.get(self.name, '🎭')

    def __str__(self) -> str:
        """Format for display"""
        return f"{self.emoji} {self.display_name}"
