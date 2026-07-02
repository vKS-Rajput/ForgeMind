"""Knowledge domain events.

Events represent significant things that have happened within the
Knowledge bounded context. In V1, events are type definitions only —
returned from service methods and logged. No event bus or pub/sub.

Bounded Context: Knowledge
Layer: Domain (Events)
Dependencies: shared.types
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime


@dataclass(frozen=True, slots=True)
class DocumentIngested:
    """A document has been successfully ingested and chunked.

    Args:
        document_id: ID of the ingested document.
        title: Title of the document.
        chunk_count: Number of chunks produced.
        timestamp: When ingestion completed.
    """

    document_id: str
    title: str
    chunk_count: int
    timestamp: datetime = field(default_factory=lambda: datetime.now(UTC))


@dataclass(frozen=True, slots=True)
class EntitiesExtracted:
    """Entities have been extracted from a document's chunks.

    Args:
        document_id: ID of the source document.
        entity_ids: IDs of the extracted entities.
        entity_count: Number of entities extracted.
        timestamp: When extraction completed.
    """

    document_id: str
    entity_ids: tuple[str, ...] = ()
    entity_count: int = 0
    timestamp: datetime = field(default_factory=lambda: datetime.now(UTC))


@dataclass(frozen=True, slots=True)
class RelationshipsExtracted:
    """Relationships have been extracted from a document's chunks.

    Args:
        document_id: ID of the source document.
        relationship_ids: IDs of the extracted relationships.
        relationship_count: Number of relationships extracted.
        timestamp: When extraction completed.
    """

    document_id: str
    relationship_ids: tuple[str, ...] = ()
    relationship_count: int = 0
    timestamp: datetime = field(default_factory=lambda: datetime.now(UTC))


@dataclass(frozen=True, slots=True)
class GraphUpdated:
    """The knowledge graph has been updated with new entities and relationships.

    Args:
        nodes_added: Number of new nodes added.
        edges_added: Number of new edges added.
        total_nodes: Total nodes in the graph after update.
        total_edges: Total edges in the graph after update.
        timestamp: When the update completed.
    """

    nodes_added: int = 0
    edges_added: int = 0
    total_nodes: int = 0
    total_edges: int = 0
    timestamp: datetime = field(default_factory=lambda: datetime.now(UTC))
