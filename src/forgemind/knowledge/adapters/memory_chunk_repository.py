"""In-memory chunk repository — stores document chunks in a Python dict.

This adapter implements the ChunkRepository port using in-memory storage.
It complements the InMemoryDocumentRepository by storing the text chunks
that are produced when a document is processed by the ingestion pipeline.

Key design feature: **secondary index by document_id**.
  - Chunks are primarily keyed by chunk_id (for direct lookup).
  - A secondary index maps each document_id to a list of its chunk_ids.
  - This makes get_chunks_for_document() run in O(k) where k is the
    number of chunks for that document, instead of O(n) scanning ALL chunks.

Thread Safety:
    Same as InMemoryDocumentRepository — all mutations are lock-protected.

Bounded Context: Knowledge
Layer: Adapters (Outbound)
Dependencies: knowledge.domain.entities, shared.types, shared.logging

Usage:
    from forgemind.knowledge.adapters.memory_chunk_repository import (
        InMemoryChunkRepository,
    )

    repository = InMemoryChunkRepository()
    chunks = [Chunk.create(document_id=doc.id, content="...")]
    saved_ids = repository.save_chunks(chunks)
    retrieved = repository.get_chunks_for_document(doc.id)
"""

from __future__ import annotations

import threading
from collections import defaultdict

from forgemind.knowledge.domain.entities import Chunk
from forgemind.shared.logging import get_logger
from forgemind.shared.types import ChunkId, DocumentId

# Each adapter gets its own named logger for clear log attribution.
logger = get_logger(__name__)


class InMemoryChunkRepository:
    """Stores Chunk entities in memory with indexed document lookup.

    Chunks are the atomic units of text that get embedded and searched.
    Each chunk belongs to exactly one document, identified by its
    document_id. This repository provides fast lookup both by individual
    chunk_id and by parent document_id.

    This implementation satisfies the ChunkRepository protocol defined
    in knowledge/ports/outbound.py via structural typing (Protocol).

    Attributes:
        _chunks: Primary storage mapping chunk_id → Chunk entity.
        _document_index: Secondary index mapping document_id → list of
            chunk_ids belonging to that document. This avoids scanning
            all chunks when retrieving chunks for a specific document.
        _lock: Threading lock for safe concurrent access.
    """

    def __init__(self) -> None:
        """Initialize an empty chunk repository."""
        # Primary storage: chunk_id → Chunk entity
        self._chunks: dict[ChunkId, Chunk] = {}

        # Secondary index: document_id → list of chunk_ids.
        # defaultdict(list) automatically creates an empty list when
        # accessing a document_id for the first time, avoiding KeyError.
        self._document_index: dict[DocumentId, list[ChunkId]] = defaultdict(list)

        # Lock for thread safety.
        self._lock = threading.Lock()

    def save_chunks(self, chunks: list[Chunk]) -> list[ChunkId]:
        """Persist a batch of chunks in memory.

        All chunks in the batch are saved atomically — either all succeed
        or none do (within the scope of this in-memory implementation).

        Args:
            chunks: The list of Chunk entities to store.

        Returns:
            A list of chunk IDs in the same order as the input chunks.
        """
        if not chunks:
            return []

        saved_ids: list[ChunkId] = []
        total_characters = 0

        with self._lock:
            for chunk in chunks:
                self._chunks[chunk.id] = chunk
                self._document_index[chunk.document_id].append(chunk.id)
                saved_ids.append(chunk.id)
                total_characters += len(chunk.content)

        # Log the batch save with useful diagnostics for debugging.
        # Knowing the total character count helps identify if chunks
        # are unexpectedly short (bad chunking) or huge (bad splitting).
        logger.info(
            "chunks_saved",
            chunk_count=len(saved_ids),
            document_id=str(chunks[0].document_id),
            total_characters=total_characters,
            average_chunk_size=round(total_characters / len(chunks)),
            total_chunks_stored=len(self._chunks),
        )

        return saved_ids

    def get_chunks_for_document(self, document_id: DocumentId) -> list[Chunk]:
        """Retrieve all chunks belonging to a specific document.

        Returns chunks sorted by their chunk_index, which represents
        their original position within the document. This ordering
        is important for reconstructing the document's logical flow.

        Uses the secondary document_index for O(k) lookup where k is
        the number of chunks for this document.

        Args:
            document_id: The parent document's unique identifier.

        Returns:
            A list of Chunk entities sorted by chunk_index (ascending).
            Empty list if no chunks exist for this document.
        """
        with self._lock:
            chunk_ids = self._document_index.get(document_id, [])
            chunks = [self._chunks[cid] for cid in chunk_ids if cid in self._chunks]

        # Sort by chunk_index to preserve the document's reading order.
        chunks.sort(key=lambda chunk: chunk.chunk_index)

        return chunks

    def get_chunk(self, chunk_id: ChunkId) -> Chunk | None:
        """Retrieve a single chunk by its unique ID.

        Args:
            chunk_id: The chunk's unique identifier.

        Returns:
            The Chunk entity, or None if not found.
        """
        with self._lock:
            chunk = self._chunks.get(chunk_id)

        if chunk is None:
            logger.debug(
                "chunk_not_found",
                chunk_id=str(chunk_id),
            )

        return chunk

    def count(self) -> int:
        """Return the total number of chunks stored.

        Returns:
            The count of chunks across all documents.
        """
        with self._lock:
            return len(self._chunks)

    def count_for_document(self, document_id: DocumentId) -> int:
        """Return the number of chunks stored for a specific document.

        Args:
            document_id: The parent document's unique identifier.

        Returns:
            The count of chunks belonging to this document.
        """
        with self._lock:
            return len(self._document_index.get(document_id, []))
