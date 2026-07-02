"""Knowledge domain entities.

Core business objects of the Knowledge bounded context. Each entity
is immutable (frozen dataclass), identified by a unique ID, and
constructed via factory classmethods that validate inputs.

Bounded Context: Knowledge
Layer: Domain (Entities)
Dependencies: shared.types, knowledge.domain.value_objects
"""

from __future__ import annotations

import hashlib
import re
import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime

from forgemind.knowledge.domain.value_objects import (
    ChunkMetadata,
    DocumentType,
    EntityType,
    Provenance,
    RelationType,
)
from forgemind.shared.types import (
    ChunkId,
    DocumentId,
    EntityId,
    RelationshipId,
)

# ── Document ─────────────────────────────────────────────────────


@dataclass(frozen=True, slots=True)
class Document:
    """A source document ingested into ForgeMind.

    Documents are the raw input — PDFs, text files, or structured
    records. They are parsed into Chunks for processing.

    Args:
        id: Unique document identifier.
        title: Human-readable title or filename.
        source_path: Original file path or URI.
        document_type: Classification of the document.
        content_hash: SHA-256 hash of the raw content (for dedup).
        page_count: Number of pages (0 for non-paginated documents).
        ingested_at: When the document was ingested.
        metadata: Additional key-value metadata.
    """

    id: DocumentId
    title: str
    source_path: str
    document_type: DocumentType
    content_hash: str
    page_count: int = 0
    ingested_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    metadata: dict[str, str] = field(default_factory=dict)

    @classmethod
    def create(
        cls,
        title: str,
        source_path: str,
        content: str,
        document_type: DocumentType = DocumentType.UNKNOWN,
        page_count: int = 0,
        metadata: dict[str, str] | None = None,
    ) -> Document:
        """Create a new Document with auto-generated ID and content hash.

        Args:
            title: Human-readable title.
            source_path: Original file path or URI.
            content: Raw text content (used to compute hash).
            document_type: Classification of the document.
            page_count: Number of pages.
            metadata: Additional key-value metadata.

        Returns:
            A new Document instance.

        Raises:
            ValueError: If title or source_path is empty.
        """
        if not title.strip():
            msg = "Document title must not be empty"
            raise ValueError(msg)
        if not source_path.strip():
            msg = "Document source_path must not be empty"
            raise ValueError(msg)

        content_hash = hashlib.sha256(content.encode("utf-8")).hexdigest()

        return cls(
            id=DocumentId(str(uuid.uuid4())),
            title=title.strip(),
            source_path=source_path.strip(),
            document_type=document_type,
            content_hash=content_hash,
            page_count=page_count,
            ingested_at=datetime.now(UTC),
            metadata=metadata or {},
        )


# ── Chunk ────────────────────────────────────────────────────────


@dataclass(frozen=True, slots=True)
class Chunk:
    """A segment of a document, ready for embedding and extraction.

    Chunks are the atomic unit of text processing. Each chunk belongs
    to exactly one document and carries positional metadata.

    Args:
        id: Unique chunk identifier.
        document_id: ID of the parent document.
        content: The text content of this chunk.
        chunk_index: Position of this chunk within the document (0-indexed).
        metadata: Positional and structural metadata.
        embedding: Optional dense vector embedding (set by embedding adapter).
    """

    id: ChunkId
    document_id: DocumentId
    content: str
    chunk_index: int = 0
    metadata: ChunkMetadata = field(default_factory=ChunkMetadata)
    embedding: list[float] | None = None

    @classmethod
    def create(
        cls,
        document_id: DocumentId,
        content: str,
        chunk_index: int = 0,
        metadata: ChunkMetadata | None = None,
    ) -> Chunk:
        """Create a new Chunk with auto-generated ID.

        Args:
            document_id: ID of the parent document.
            content: Text content of the chunk.
            chunk_index: Position within the document.
            metadata: Positional metadata.

        Returns:
            A new Chunk instance.

        Raises:
            ValueError: If content is empty.
        """
        if not content.strip():
            msg = "Chunk content must not be empty"
            raise ValueError(msg)

        return cls(
            id=ChunkId(str(uuid.uuid4())),
            document_id=document_id,
            content=content,
            chunk_index=chunk_index,
            metadata=metadata or ChunkMetadata(),
        )


# ── Knowledge Entity ─────────────────────────────────────────────


def _normalize_name(name: str) -> str:
    """Normalize an entity name to a canonical form.

    Lowercases, strips whitespace, replaces non-alphanumeric
    characters with underscores, and collapses multiple underscores.

    Args:
        name: Raw entity name.

    Returns:
        Canonical normalized name.
    """
    canonical = name.lower().strip()
    canonical = re.sub(r"[^a-z0-9]+", "_", canonical)
    canonical = canonical.strip("_")
    return canonical


@dataclass(frozen=True, slots=True)
class KnowledgeEntity:
    """An extracted knowledge entity — a node in the knowledge graph.

    Entities represent domain concepts: assets, components, failure
    modes, symptoms, actions, etc. Each entity has a canonical name
    for deduplication and a provenance chain for traceability.

    Args:
        id: Unique entity identifier.
        name: Human-readable name as extracted from source text.
        canonical_name: Normalized name for deduplication and matching.
        entity_type: Classification of this entity.
        description: Optional longer description or context.
        provenance: Where this entity was extracted from.
        attributes: Additional key-value attributes (flexible schema).
    """

    id: EntityId
    name: str
    canonical_name: str
    entity_type: EntityType
    description: str = ""
    provenance: Provenance | None = None
    attributes: dict[str, str] = field(default_factory=dict)

    @classmethod
    def create(
        cls,
        name: str,
        entity_type: EntityType,
        description: str = "",
        provenance: Provenance | None = None,
        attributes: dict[str, str] | None = None,
    ) -> KnowledgeEntity:
        """Create a new KnowledgeEntity with auto-generated ID and canonical name.

        Args:
            name: Human-readable entity name.
            entity_type: Classification of this entity.
            description: Optional description.
            provenance: Extraction provenance.
            attributes: Additional attributes.

        Returns:
            A new KnowledgeEntity instance.

        Raises:
            ValueError: If name is empty.
        """
        if not name.strip():
            msg = "Entity name must not be empty"
            raise ValueError(msg)

        return cls(
            id=EntityId(str(uuid.uuid4())),
            name=name.strip(),
            canonical_name=_normalize_name(name),
            entity_type=entity_type,
            description=description.strip(),
            provenance=provenance,
            attributes=attributes or {},
        )


# ── Knowledge Relationship ───────────────────────────────────────


@dataclass(frozen=True, slots=True)
class KnowledgeRelationship:
    """An extracted relationship between two knowledge entities — an edge in the graph.

    Relationships are directed: source_entity → relation → target_entity.
    Each relationship carries provenance for traceability.

    Args:
        id: Unique relationship identifier.
        source_entity_id: ID of the source (origin) entity.
        target_entity_id: ID of the target (destination) entity.
        relation_type: Classification of this relationship.
        provenance: Where this relationship was extracted from.
        attributes: Additional key-value attributes.
    """

    id: RelationshipId
    source_entity_id: EntityId
    target_entity_id: EntityId
    relation_type: RelationType
    provenance: Provenance | None = None
    attributes: dict[str, str] = field(default_factory=dict)

    @classmethod
    def create(
        cls,
        source_entity_id: EntityId,
        target_entity_id: EntityId,
        relation_type: RelationType,
        provenance: Provenance | None = None,
        attributes: dict[str, str] | None = None,
    ) -> KnowledgeRelationship:
        """Create a new KnowledgeRelationship with auto-generated ID.

        Args:
            source_entity_id: ID of the source entity.
            target_entity_id: ID of the target entity.
            relation_type: Type of relationship.
            provenance: Extraction provenance.
            attributes: Additional attributes.

        Returns:
            A new KnowledgeRelationship instance.

        Raises:
            ValueError: If source and target are the same entity.
        """
        if source_entity_id == target_entity_id:
            msg = "Relationship source and target must be different entities"
            raise ValueError(msg)

        return cls(
            id=RelationshipId(str(uuid.uuid4())),
            source_entity_id=source_entity_id,
            target_entity_id=target_entity_id,
            relation_type=relation_type,
            provenance=provenance,
            attributes=attributes or {},
        )
