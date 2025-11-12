"""
Domain models for PersonaChat V1

These dataclasses represent the core domain objects used throughout the application.
They provide type safety and clear structure for data flowing through services and routes.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Optional


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
            archived=row.get('archived', False),
            created_at=row.get('created_at'),
            updated_at=row.get('updated_at')
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
            created_at=row.get('created_at'),
            updated_at=row.get('updated_at')
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
    suggested_relationships: List[RelationshipSuggestion] = field(default_factory=list)
