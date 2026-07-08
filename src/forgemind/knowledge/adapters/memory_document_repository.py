"""In-memory document repository — stores documents in a Python dict.

This adapter implements the DocumentRepository port using a simple
in-memory dictionary. It's designed for:

  1. **Development**: Fast iteration without database setup.
  2. **Testing**: Deterministic behavior, no external dependencies.
  3. **Demos**: Self-contained demos that work without infrastructure.

When ForgeMind graduates to production, this adapter will be replaced
by a PostgreSQL or SQLite adapter that implements the same port.
The rest of the codebase won't change — that's the power of ports.

Thread Safety:
    All read and write operations are protected by a threading.Lock.
    This isn't strictly necessary for V1 (which is single-threaded),
    but it prevents subtle bugs if someone adds concurrency later.

Bounded Context: Knowledge
Layer: Adapters (Outbound)
Dependencies: knowledge.domain.entities, shared.types, shared.logging

Usage:
    from forgemind.knowledge.adapters.memory_document_repository import (
        InMemoryDocumentRepository,
    )

    repository = InMemoryDocumentRepository()
    document = Document.create(title="Manual", source_path="/data/manual.pdf", content="...")
    repository.save(document)
    retrieved = repository.get(document.id)
"""

from __future__ import annotations

import threading

from forgemind.knowledge.domain.entities import Document
from forgemind.shared.logging import get_logger
from forgemind.shared.types import DocumentId

# Each adapter gets its own named logger for clear log attribution.
logger = get_logger(__name__)

# ── Constants ────────────────────────────────────────────────────

# If the repository grows beyond this many documents, we log a warning.
# This is a gentle nudge that in-memory storage is reaching its practical
# limits and a persistent database should be considered.
_CAPACITY_WARNING_THRESHOLD: int = 1000


class InMemoryDocumentRepository:
    """Stores Document entities in memory using a Python dictionary.

    Documents are keyed by their unique DocumentId. The repository
    provides deduplication via content hash lookup and returns documents
    ordered by ingestion time when listing.

    This implementation satisfies the DocumentRepository protocol
    defined in knowledge/ports/outbound.py. It does NOT inherit from
    the protocol — Python's structural typing (Protocol) means any
    class with matching method signatures is automatically compatible.

    Attributes:
        _documents: Internal storage mapping document IDs to Document entities.
        _hash_index: Secondary index mapping content hashes to document IDs,
            enabling O(1) duplicate detection instead of scanning all documents.
        _lock: Threading lock to ensure safe concurrent access.
    """

    def __init__(self) -> None:
        """Initialize an empty document repository."""
        # Primary storage: document_id → Document
        self._documents: dict[DocumentId, Document] = {}

        # Secondary index for deduplication: content_hash → document_id.
        # This allows exists_by_hash() to run in O(1) instead of
        # iterating through all documents to compare hashes.
        self._hash_index: dict[str, DocumentId] = {}

        # Lock for thread safety. Even though V1 is single-threaded,
        # protecting state mutations prevents bugs if concurrency is
        # added later (e.g., async ingestion workers).
        self._lock = threading.Lock()

    def save(self, document: Document) -> DocumentId:
        """Persist a document in memory.

        If a document with the same ID already exists, it is overwritten.
        The content hash index is updated to reflect the new document.

        Args:
            document: The Document entity to store.

        Returns:
            The document's ID (same as document.id).
        """
        with self._lock:
            self._documents[document.id] = document
            self._hash_index[document.content_hash] = document.id

            current_count = len(self._documents)

        logger.info(
            "document_saved",
            document_id=str(document.id),
            title=document.title,
            content_hash_prefix=document.content_hash[:12],
            total_documents_stored=current_count,
        )

        # Warn if the repository is getting large — a signal to the
        # operator that they should consider switching to a database.
        if current_count >= _CAPACITY_WARNING_THRESHOLD:
            logger.warning(
                "repository_capacity_warning",
                total_documents_stored=current_count,
                threshold=_CAPACITY_WARNING_THRESHOLD,
                recommendation="Consider migrating to a persistent database.",
            )

        return document.id

    def get(self, document_id: DocumentId) -> Document | None:
        """Retrieve a document by its unique ID.

        Args:
            document_id: The document's unique identifier.

        Returns:
            The Document entity, or None if no document with that ID exists.
        """
        with self._lock:
            document = self._documents.get(document_id)

        if document is None:
            logger.debug(
                "document_not_found",
                document_id=str(document_id),
            )

        return document

    def list_all(self) -> list[Document]:
        """List all stored documents, newest first.

        Returns documents sorted by their `ingested_at` timestamp
        in descending order (most recently ingested first). This
        ordering matches what users typically expect when browsing
        their document library.

        Returns:
            A list of all stored Document entities, sorted by
            ingestion time descending. Empty list if no documents.
        """
        with self._lock:
            all_documents = list(self._documents.values())

        # Sort by ingested_at descending (newest first).
        # The key function extracts the timestamp; reverse=True gives descending.
        all_documents.sort(key=lambda doc: doc.ingested_at, reverse=True)

        return all_documents

    def exists_by_hash(self, content_hash: str) -> bool:
        """Check if a document with the given content hash already exists.

        This enables idempotent ingestion: if the same file is uploaded
        twice, the second upload is detected and can be skipped rather
        than creating a duplicate entry.

        Uses the secondary hash index for O(1) lookup performance.

        Args:
            content_hash: SHA-256 hex digest of the document content.

        Returns:
            True if a document with this exact content hash is stored.
        """
        with self._lock:
            return content_hash in self._hash_index

    def count(self) -> int:
        """Return the total number of documents stored.

        Returns:
            The count of documents in the repository.
        """
        with self._lock:
            return len(self._documents)
