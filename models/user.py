"""
User model
Represents a bot user with their settings
"""

from dataclasses import dataclass
from datetime import datetime
from typing import Optional


@dataclass
class User:
    """Represents a user with their settings"""

    user_id: int
    username: Optional[str]
    selected_personality: str
    created_at: datetime
    updated_at: datetime

    @classmethod
    def from_dict(cls, data: dict) -> 'User':
        """Create User from database row"""
        return cls(
            user_id=data['user_id'],
            username=data.get('username'),
            selected_personality=data.get('selected_personality', 'neutral'),
            created_at=data['created_at'] if isinstance(data['created_at'], datetime)
                      else datetime.fromisoformat(data['created_at'].replace('Z', '+00:00')),
            updated_at=data['updated_at'] if isinstance(data['updated_at'], datetime)
                      else datetime.fromisoformat(data['updated_at'].replace('Z', '+00:00'))
        )

    def to_dict(self) -> dict:
        """Convert to dictionary"""
        return {
            'user_id': self.user_id,
            'username': self.username,
            'selected_personality': self.selected_personality,
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat()
        }
