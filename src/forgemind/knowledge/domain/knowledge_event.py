"""Knowledge event types — the audit trail of organizational memory evolution.

Every time knowledge changes (entity created, confidence increased,
contradiction detected), a KnowledgeEvent is recorded. These events
form the Organizational Learning Timeline — showing judges how
ForgeMind's understanding evolves with each uploaded document.

Bounded Context: Knowledge
Layer: Domain (Value Objects)
Dependencies: None (pure Python)
"""

from __future__ import annotations

import enum
import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime


class KnowledgeEventType(enum.Enum):
    """Classification of how knowledge changed.

    Each event type represents a specific kind of knowledge evolution.
    The Knowledge Evolution Engine emits these events as it merges
    new information into the existing graph.
    """

    ENTITY_CREATED = "entity_created"
    """A brand-new concept was added to the knowledge graph."""

    ENTITY_UPDATED = "entity_updated"
    """An existing entity's metadata was enriched with new information."""

    CONFIDENCE_INCREASED = "confidence_increased"
    """An existing claim gained supporting evidence from a new document."""

    RELATIONSHIP_CREATED = "relationship_created"
    """A new connection between concepts was discovered."""

    RELATIONSHIP_STRENGTHENED = "relationship_strengthened"
    """An existing relationship gained additional supporting evidence."""

    CONTRADICTION_DETECTED = "contradiction_detected"
    """New evidence contradicts existing knowledge — requires attention."""


@dataclass(frozen=True, slots=True)
class KnowledgeEvent:
    """Immutable audit record of a knowledge evolution event.

    Every change to the knowledge graph produces one or more events.
    These events form the Organizational Learning Timeline, showing
    how ForgeMind's understanding of the organization's assets,
    failures, and procedures evolves over time.

    Args:
        id: Unique event identifier.
        event_type: What kind of change occurred.
        entity_name: The entity or concept that changed.
        old_confidence: Previous confidence (None if newly created).
        new_confidence: Updated confidence after this event.
        evidence_count: How many documents now support this knowledge.
        source_document_id: Which document triggered this event.
        source_document_title: Human-readable title for display.
        timestamp: When the event occurred.
        details: Human-readable explanation of what changed and why.
    """

    id: str
    event_type: KnowledgeEventType
    entity_name: str
    old_confidence: float | None
    new_confidence: float
    evidence_count: int
    source_document_id: str
    source_document_title: str
    timestamp: datetime = field(default_factory=lambda: datetime.now(UTC))
    details: str = ""

    @classmethod
    def create(
        cls,
        event_type: KnowledgeEventType,
        entity_name: str,
        new_confidence: float,
        evidence_count: int,
        source_document_id: str,
        source_document_title: str,
        old_confidence: float | None = None,
        details: str = "",
    ) -> KnowledgeEvent:
        """Create a new KnowledgeEvent with auto-generated ID and timestamp.

        Args:
            event_type: What kind of change occurred.
            entity_name: The entity that changed.
            new_confidence: Updated confidence.
            evidence_count: Number of supporting documents.
            source_document_id: ID of the triggering document.
            source_document_title: Title of the triggering document.
            old_confidence: Previous confidence (None if new).
            details: Human-readable explanation.

        Returns:
            A new immutable KnowledgeEvent.
        """
        return cls(
            id=str(uuid.uuid4()),
            event_type=event_type,
            entity_name=entity_name,
            old_confidence=old_confidence,
            new_confidence=new_confidence,
            evidence_count=evidence_count,
            source_document_id=source_document_id,
            source_document_title=source_document_title,
            timestamp=datetime.now(UTC),
            details=details,
        )
