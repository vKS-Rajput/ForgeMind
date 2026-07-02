"""Knowledge inbound ports — use case interfaces.

These protocols define what the outside world can ask the Knowledge
bounded context to do. Implemented by application services that
orchestrate domain logic and adapters.

Bounded Context: Knowledge
Layer: Ports (Inbound)
Dependencies: knowledge.domain.entities
"""

from __future__ import annotations

from typing import Protocol

from forgemind.knowledge.domain.entities import (
    Chunk,
    Document,
    KnowledgeEntity,
    KnowledgeRelationship,
)


class IngestionService(Protocol):
    """Orchestrates document ingestion: parsing, chunking, and storage.

    Implementations coordinate a DocumentParser adapter, the domain
    chunking logic, and repository adapters to produce stored
    Documents and Chunks.
    """

    def ingest_document(self, path: str) -> Document:
        """Parse and ingest a document from a file path.

        Args:
            path: Path to the document file (PDF, text, etc.).

        Returns:
            The ingested Document with generated ID and content hash.

        Raises:
            DocumentParseError: If the file cannot be parsed.
            UnsupportedFormatError: If the file format is not supported.
        """
        ...

    def ingest_text(
        self,
        text: str,
        title: str,
        metadata: dict[str, str] | None = None,
    ) -> Document:
        """Ingest raw text content directly.

        Args:
            text: The raw text content.
            title: Human-readable title for the document.
            metadata: Optional additional metadata.

        Returns:
            The ingested Document.
        """
        ...


class ExtractionService(Protocol):
    """Orchestrates entity and relationship extraction from chunks.

    Implementations coordinate EntityExtractor and RelationshipExtractor
    adapters with domain deduplication and validation logic.
    """

    def extract_entities(
        self,
        chunks: list[Chunk],
    ) -> list[KnowledgeEntity]:
        """Extract knowledge entities from document chunks.

        Args:
            chunks: List of text chunks to extract from.

        Returns:
            Deduplicated list of extracted entities with provenance.
        """
        ...

    def extract_relationships(
        self,
        chunks: list[Chunk],
        entities: list[KnowledgeEntity],
    ) -> list[KnowledgeRelationship]:
        """Extract relationships between entities from document chunks.

        Args:
            chunks: List of text chunks to extract from.
            entities: Previously extracted entities to find relationships between.

        Returns:
            List of extracted relationships with provenance.
        """
        ...
