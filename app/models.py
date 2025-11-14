"""
Domain models for PersonaChat V1

These dataclasses represent the core domain objects used throughout the application.
They provide type safety and clear structure for data flowing through services and routes.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Optional, Any


def _parse_timestamp(timestamp_str: Optional[str]) -> Optional[datetime]:
    """Parse ISO 8601 timestamp string from Supabase to datetime object

    Handles variable-length microseconds (e.g., '2025-11-13T20:45:25.57284+00:00')
    by padding to 6 digits as required by Python's fromisoformat().
    """
    if not timestamp_str:
        return None
    if isinstance(timestamp_str, datetime):
        return timestamp_str

    # Handle ISO 8601 with 'Z' timezone indicator
    timestamp_str = timestamp_str.replace('Z', '+00:00')

    # Normalize microseconds to 6 digits for fromisoformat()
    # Example: '2025-11-13T20:45:25.57284+00:00' -> '2025-11-13T20:45:25.572840+00:00'
    import re
    match = re.match(r'(\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2})\.(\d+)([\+\-]\d{2}:\d{2})', timestamp_str)
    if match:
        date_time, microseconds, timezone = match.groups()
        # Pad microseconds to 6 digits (or truncate if longer)
        microseconds = microseconds.ljust(6, '0')[:6]
        timestamp_str = f"{date_time}.{microseconds}{timezone}"

    return datetime.fromisoformat(timestamp_str)


@dataclass
class Persona:
    """An AI persona with rich profile information"""
    id: str
    user_id: str
    name: str
    role: Optional[str] = None
    company: Optional[str] = None
    age_stage: Optional[str] = None
    goals: List[str] = field(default_factory=list)
    pains: List[str] = field(default_factory=list)
    behaviors: Optional[str] = None
    tools: Optional[str] = None
    quotes: List[str] = field(default_factory=list)
    tags: List[str] = field(default_factory=list)
    notes: Optional[str] = None
    avatar_emoji: Optional[str] = None
    avatar_color: Optional[str] = None
    custom_fields: Dict[str, Any] = field(default_factory=dict)
    archived: bool = False
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    def to_dict(self):
        """Convert to dictionary for JSON serialization"""
        return {
            'id': self.id,
            'user_id': self.user_id,
            'name': self.name,
            'role': self.role,
            'company': self.company,
            'age_stage': self.age_stage,
            'goals': self.goals,
            'pains': self.pains,
            'behaviors': self.behaviors,
            'tools': self.tools,
            'quotes': self.quotes,
            'tags': self.tags,
            'notes': self.notes,
            'avatar_emoji': self.avatar_emoji,
            'avatar_color': self.avatar_color,
            'custom_fields': self.custom_fields,
            'archived': self.archived,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }

    @staticmethod
    def from_db_row(row: dict):
        """Create Persona from database row"""
        return Persona(
            id=row['id'],
            user_id=row['user_id'],
            name=row['name'],
            role=row.get('role'),
            company=row.get('company'),
            age_stage=row.get('age_stage'),
            goals=row.get('goals', []),
            pains=row.get('pains', []),
            behaviors=row.get('behaviors'),
            tools=row.get('tools'),
            quotes=row.get('quotes', []),
            tags=row.get('tags', []),
            notes=row.get('notes'),
            avatar_emoji=row.get('avatar_emoji'),
            avatar_color=row.get('avatar_color'),
            custom_fields=row.get('custom_fields', {}),
            archived=row.get('archived', False),
            created_at=_parse_timestamp(row.get('created_at')),
            updated_at=_parse_timestamp(row.get('updated_at'))
        )


@dataclass
class Conversation:
    """A multi-persona chat session"""
    id: str
    user_id: str
    title: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


@dataclass
class ConversationParticipant:
    """A persona participating in a conversation"""
    conversation_id: str
    persona_id: str
    joined_at: Optional[datetime] = None
    active: bool = True


@dataclass
class Message:
    """A single message in a conversation"""
    id: str
    conversation_id: str
    content: str
    persona_id: Optional[str] = None  # None if user message
    user_id: Optional[str] = None  # For user messages
    created_at: Optional[datetime] = None

    @property
    def is_user_message(self) -> bool:
        """Check if this is a user message (vs persona message)"""
        return self.persona_id is None

    def to_dict(self):
        """Convert to dictionary for JSON serialization"""
        return {
            'id': self.id,
            'conversation_id': self.conversation_id,
            'content': self.content,
            'persona_id': self.persona_id,
            'user_id': self.user_id,
            'is_user_message': self.is_user_message,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }


@dataclass
class PersonaRelationship:
    """A relationship between two personas"""
    id: str
    user_id: str
    from_persona_id: str
    to_persona_id: str
    relationship_type: str  # e.g., colleague, supervisor, friend, rival
    label: Optional[str] = None
    shared_context: Optional[str] = None  # Shared history, location, background
    interaction_style: Optional[str] = None  # How they typically interact
    notes: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    @staticmethod
    def from_db_row(row: dict):
        """Create PersonaRelationship from database row"""
        return PersonaRelationship(
            id=row['id'],
            user_id=row['user_id'],
            from_persona_id=row['from_persona_id'],
            to_persona_id=row['to_persona_id'],
            relationship_type=row['relationship_type'],
            label=row.get('label'),
            shared_context=row.get('shared_context'),
            interaction_style=row.get('interaction_style'),
            notes=row.get('notes'),
            created_at=_parse_timestamp(row.get('created_at')),
            updated_at=_parse_timestamp(row.get('updated_at'))
        )

    def to_dict(self):
        """Convert to dictionary for JSON serialization"""
        return {
            'id': self.id,
            'user_id': self.user_id,
            'from_persona_id': self.from_persona_id,
            'to_persona_id': self.to_persona_id,
            'relationship_type': self.relationship_type,
            'label': self.label,
            'shared_context': self.shared_context,
            'interaction_style': self.interaction_style,
            'notes': self.notes,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }


@dataclass
class RelationshipSuggestion:
    """AI-suggested relationship between personas during enrichment"""
    persona_id: str
    persona_name: str
    relationship_type: str
    shared_context: str
    interaction_style: str


@dataclass
class PersonaEnrichment:
    """AI-generated persona enrichment from user description"""
    name: str
    role: str
    company: Optional[str] = None
    age_stage: Optional[str] = None
    goals: List[str] = field(default_factory=list)
    pains: List[str] = field(default_factory=list)
    behaviors: Optional[str] = None
    tools: Optional[str] = None
    quotes: List[str] = field(default_factory=list)
    tags: List[str] = field(default_factory=list)
    avatar_emoji: Optional[str] = None
    avatar_color: Optional[str] = None
    custom_fields: Dict[str, Any] = field(default_factory=dict)
    suggested_relationships: List[RelationshipSuggestion] = field(default_factory=list)
