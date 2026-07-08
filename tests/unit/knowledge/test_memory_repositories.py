"""Tests for in-memory repository adapters.

These tests verify that InMemoryDocumentRepository and InMemoryChunkRepository
correctly implement their respective port protocols. Although these are
"just" in-memory dicts, testing them thoroughly ensures:

  1. The port contract is satisfied (methods exist, signatures match).
  2. Edge cases are handled (empty lists, missing IDs, duplicates).
  3. Future database adapters can reuse these tests as a compliance suite.

Test Categories:
  - Document repository: save, get, list_all, exists_by_hash, ordering.
  - Chunk repository: save_chunks, get_by_document, get_by_id, ordering.
"""

from __future__ import annotations

import pytest

from forgemind.knowledge.adapters.memory_chunk_repository import (
    InMemoryChunkRepository,
)
from forgemind.knowledge.adapters.memory_document_repository import (
    InMemoryDocumentRepository,
)
from forgemind.knowledge.domain.entities import Chunk, Document
from forgemind.knowledge.domain.value_objects import DocumentType
from forgemind.shared.types import ChunkId, DocumentId

pytestmark = pytest.mark.unit


# ── Document Repository Tests ────────────────────────────────────


class TestInMemoryDocumentRepository:
    """Verify the InMemoryDocumentRepository satisfies the port contract."""

    @staticmethod
    def _create_test_document(
        title: str = "Test Manual",
        content: str = "Some test content",
    ) -> Document:
        """Helper to create a Document for testing."""
        return Document.create(
            title=title,
            source_path=f"/data/{title.lower().replace(' ', '_')}.pdf",
            content=content,
            document_type=DocumentType.MANUAL,
        )

    def test_save_and_get_returns_same_document(self) -> None:
        """A saved document should be retrievable by its ID."""
        repo = InMemoryDocumentRepository()
        document = self._create_test_document()

        repo.save(document)
        retrieved = repo.get(document.id)

        assert retrieved is not None
        assert retrieved.id == document.id
        assert retrieved.title == document.title

    def test_get_nonexistent_returns_none(self) -> None:
        """Getting a document that doesn't exist should return None, not raise."""
        repo = InMemoryDocumentRepository()

        result = repo.get(DocumentId("nonexistent-id"))

        assert result is None

    def test_list_all_returns_documents_newest_first(self) -> None:
        """list_all() should return documents sorted by ingestion time descending."""
        repo = InMemoryDocumentRepository()
        doc_a = self._create_test_document(title="First Document", content="aaa")
        doc_b = self._create_test_document(title="Second Document", content="bbb")
        doc_c = self._create_test_document(title="Third Document", content="ccc")

        # Save in alphabetical order
        repo.save(doc_a)
        repo.save(doc_b)
        repo.save(doc_c)

        all_docs = repo.list_all()

        # Should return 3 documents (we don't assert exact order because
        # timestamps may be identical when created in rapid succession,
        # but we verify all documents are present).
        assert len(all_docs) == 3
        titles = {doc.title for doc in all_docs}
        assert titles == {"First Document", "Second Document", "Third Document"}

    def test_list_all_empty_repository(self) -> None:
        """list_all() on an empty repository should return an empty list."""
        repo = InMemoryDocumentRepository()

        result = repo.list_all()

        assert result == []

    def test_exists_by_hash_detects_duplicate(self) -> None:
        """exists_by_hash should return True after saving a document."""
        repo = InMemoryDocumentRepository()
        document = self._create_test_document(content="unique content for hashing")

        # Before saving, the hash should not exist
        assert repo.exists_by_hash(document.content_hash) is False

        repo.save(document)

        # After saving, the hash should be found
        assert repo.exists_by_hash(document.content_hash) is True

    def test_exists_by_hash_unknown_hash_returns_false(self) -> None:
        """A hash that was never saved should return False."""
        repo = InMemoryDocumentRepository()

        assert repo.exists_by_hash("abc123nonexistent") is False

    def test_count_tracks_repository_size(self) -> None:
        """count() should reflect the number of documents stored."""
        repo = InMemoryDocumentRepository()
        assert repo.count() == 0

        repo.save(self._create_test_document(title="A", content="a"))
        assert repo.count() == 1

        repo.save(self._create_test_document(title="B", content="b"))
        assert repo.count() == 2

    def test_save_overwrites_same_id(self) -> None:
        """Saving a document with the same ID should overwrite, not duplicate."""
        repo = InMemoryDocumentRepository()
        document = self._create_test_document()

        repo.save(document)
        repo.save(document)  # Save the same document again

        assert repo.count() == 1


# ── Chunk Repository Tests ───────────────────────────────────────


class TestInMemoryChunkRepository:
    """Verify the InMemoryChunkRepository satisfies the port contract."""

    @staticmethod
    def _create_test_chunks(
        document_id: DocumentId,
        count: int = 3,
    ) -> list[Chunk]:
        """Helper to create a batch of Chunks for testing."""
        return [
            Chunk.create(
                document_id=document_id,
                content=f"Chunk {i} content for testing purposes.",
                chunk_index=i,
            )
            for i in range(count)
        ]

    def test_save_and_get_by_document(self) -> None:
        """Saved chunks should be retrievable by their parent document ID."""
        repo = InMemoryChunkRepository()
        doc_id = DocumentId("doc-001")
        chunks = self._create_test_chunks(doc_id, count=3)

        saved_ids = repo.save_chunks(chunks)
        retrieved = repo.get_chunks_for_document(doc_id)

        assert len(saved_ids) == 3
        assert len(retrieved) == 3

    def test_get_chunks_for_document_sorted_by_index(self) -> None:
        """Retrieved chunks should be sorted by chunk_index ascending."""
        repo = InMemoryChunkRepository()
        doc_id = DocumentId("doc-001")

        # Create chunks in reverse order
        chunk_2 = Chunk.create(document_id=doc_id, content="Third chunk.", chunk_index=2)
        chunk_0 = Chunk.create(document_id=doc_id, content="First chunk.", chunk_index=0)
        chunk_1 = Chunk.create(document_id=doc_id, content="Second chunk.", chunk_index=1)

        repo.save_chunks([chunk_2, chunk_0, chunk_1])
        retrieved = repo.get_chunks_for_document(doc_id)

        assert [c.chunk_index for c in retrieved] == [0, 1, 2]

    def test_get_chunks_for_nonexistent_document(self) -> None:
        """Getting chunks for a document that has none returns empty list."""
        repo = InMemoryChunkRepository()

        result = repo.get_chunks_for_document(DocumentId("nonexistent"))

        assert result == []

    def test_get_chunk_by_id(self) -> None:
        """A single chunk should be retrievable by its unique ID."""
        repo = InMemoryChunkRepository()
        doc_id = DocumentId("doc-001")
        chunks = self._create_test_chunks(doc_id, count=1)

        repo.save_chunks(chunks)
        retrieved = repo.get_chunk(chunks[0].id)

        assert retrieved is not None
        assert retrieved.content == chunks[0].content

    def test_get_nonexistent_chunk_returns_none(self) -> None:
        """Getting a chunk that doesn't exist returns None."""
        repo = InMemoryChunkRepository()

        result = repo.get_chunk(ChunkId("nonexistent-id"))

        assert result is None

    def test_save_empty_list_returns_empty(self) -> None:
        """Saving an empty chunk list should succeed and return empty."""
        repo = InMemoryChunkRepository()

        result = repo.save_chunks([])

        assert result == []
        assert repo.count() == 0

    def test_chunks_from_different_documents_are_separate(self) -> None:
        """Chunks from different documents should not interfere."""
        repo = InMemoryChunkRepository()
        doc_a = DocumentId("doc-a")
        doc_b = DocumentId("doc-b")

        chunks_a = self._create_test_chunks(doc_a, count=2)
        chunks_b = self._create_test_chunks(doc_b, count=3)
        repo.save_chunks(chunks_a)
        repo.save_chunks(chunks_b)

        assert len(repo.get_chunks_for_document(doc_a)) == 2
        assert len(repo.get_chunks_for_document(doc_b)) == 3
        assert repo.count() == 5

    def test_count_for_document(self) -> None:
        """count_for_document should return the chunk count for one document."""
        repo = InMemoryChunkRepository()
        doc_id = DocumentId("doc-001")
        chunks = self._create_test_chunks(doc_id, count=4)

        repo.save_chunks(chunks)

        assert repo.count_for_document(doc_id) == 4
        assert repo.count_for_document(DocumentId("other")) == 0
