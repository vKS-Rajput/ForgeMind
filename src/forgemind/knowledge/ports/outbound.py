"""Knowledge outbound ports — dependency interfaces.

These protocols define what the Knowledge bounded context needs
from external systems. Each protocol is implemented by one or
more adapters (e.g., file-based, database, LLM-based).

Bounded Context: Knowledge
Layer: Ports (Outbound)
Dependencies: knowledge.domain.entities, knowledge.domain.value_objects
"""

from __future__ import annotations

from typing import Protocol

from forgemind.knowledge.domain.entities import (
    Chunk,
    Document,
    KnowledgeEntity,
    KnowledgeRelationship,
)
from forgemind.knowledge.domain.value_objects import EntityType
from forgemind.shared.types import ChunkId, DocumentId


class DocumentRepository(Protocol):
    """Persistence interface for Documents.

    Implementations may use file storage, SQLite, PostgreSQL, etc.
    """

    def save(self, document: Document) -> DocumentId:
        """Persist a document.

        Args:
            document: The document to save.

        Returns:
            The document's ID.
        """
        ...

    def get(self, document_id: DocumentId) -> Document | None:
        """Retrieve a document by ID.

        Args:
            document_id: The document's unique identifier.

        Returns:
            The document, or None if not found.
        """
        ...

    def list_all(self) -> list[Document]:
        """List all stored documents.

        Returns:
            All documents, ordered by ingestion time (newest first).
        """
        ...

    def exists_by_hash(self, content_hash: str) -> bool:
        """Check if a document with the given content hash already exists.

        Args:
            content_hash: SHA-256 hash of the document content.

        Returns:
            True if a document with this hash is already stored.
        """
        ...


class ChunkRepository(Protocol):
    """Persistence interface for Chunks."""

    def save_chunks(self, chunks: list[Chunk]) -> list[ChunkId]:
        """Persist a batch of chunks.

        Args:
            chunks: The chunks to save.

        Returns:
            List of chunk IDs.
        """
        ...

    def get_chunks_for_document(self, document_id: DocumentId) -> list[Chunk]:
        """Retrieve all chunks belonging to a document.

        Args:
            document_id: The parent document's ID.

        Returns:
            List of chunks ordered by chunk_index.
        """
        ...

    def get_chunk(self, chunk_id: ChunkId) -> Chunk | None:
        """Retrieve a single chunk by ID.

        Args:
            chunk_id: The chunk's unique identifier.

        Returns:
            The chunk, or None if not found.
        """
        ...


class EntityExtractor(Protocol):
    """Extracts knowledge entities from text.

    Implementations may use rule-based patterns, spaCy NER,
    or LLM-based extraction.
    """

    def extract(
        self,
        text: str,
        entity_types: list[EntityType] | None = None,
    ) -> list[KnowledgeEntity]:
        """Extract entities from text.

        Args:
            text: The source text to extract from.
            entity_types: Optional filter — only extract these types.
                None means extract all types.

        Returns:
            List of extracted entities with provenance.
        """
        ...


class RelationshipExtractor(Protocol):
    """Extracts relationships between entities from text.

    Implementations may use co-occurrence heuristics, pattern matching,
    or LLM-based extraction.
    """

    def extract(
        self,
        text: str,
        entities: list[KnowledgeEntity],
    ) -> list[KnowledgeRelationship]:
        """Extract relationships between known entities from text.

        Args:
            text: The source text to extract from.
            entities: Entities already extracted from this text.

        Returns:
            List of extracted relationships with provenance.
        """
        ...
