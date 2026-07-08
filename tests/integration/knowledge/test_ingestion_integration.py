"""Integration test for the document ingestion pipeline.

This test verifies the complete vertical slice: a real PDF file on
disk → parsed text → Document entity → Chunks with page metadata →
all stored in repositories and queryable.

Unlike unit tests (which test individual components in isolation),
this integration test wires together all real adapters and verifies
the end-to-end behavior that a user would experience.

Why is this a separate test file?
  - Integration tests may be slower (they do real I/O).
  - They have different failure modes (dependency issues vs. logic bugs).
  - They can be run separately: `pytest -m integration`

Bounded Context: Knowledge
Test Layer: Integration
"""

from __future__ import annotations

from pathlib import Path

import pytest

from forgemind.knowledge.adapters.ingestion_service import (
    IngestionApplicationService,
)
from forgemind.knowledge.adapters.memory_chunk_repository import (
    InMemoryChunkRepository,
)
from forgemind.knowledge.adapters.memory_document_repository import (
    InMemoryDocumentRepository,
)
from forgemind.knowledge.adapters.pdf_parser import PdfDocumentParser

pytestmark = pytest.mark.integration


class TestIngestionPipelineIntegration:
    """End-to-end integration test for the ingestion pipeline.

    This test class uses real adapters (no mocks) to verify that
    the full pipeline works correctly from file to stored entities.
    """

    def test_full_pipeline_pdf_to_stored_chunks(self, sample_pdf_path: Path) -> None:
        """A real PDF should flow through the entire pipeline successfully.

        This is the "smoke test" for the ingestion pipeline. If this
        test passes, the core functionality works end-to-end.
        """
        # Arrange: Wire together real adapters
        doc_repo = InMemoryDocumentRepository()
        chunk_repo = InMemoryChunkRepository()
        service = IngestionApplicationService(
            parser=PdfDocumentParser(),
            document_repository=doc_repo,
            chunk_repository=chunk_repo,
        )

        # Act: Ingest the test PDF
        result = service.ingest_document(str(sample_pdf_path))

        # Assert: Document was stored
        stored_document = doc_repo.get(result.document.id)
        assert stored_document is not None
        assert stored_document.title == "pump_manual_p101"
        assert stored_document.page_count == 2

        # Assert: Chunks were stored and retrievable by document ID
        stored_chunks = chunk_repo.get_chunks_for_document(result.document.id)
        assert len(stored_chunks) > 0
        assert len(stored_chunks) == len(result.chunks)

        # Assert: Chunks are ordered by index
        chunk_indices = [chunk.chunk_index for chunk in stored_chunks]
        assert chunk_indices == sorted(chunk_indices)

    def test_chunks_contain_actual_pdf_content(
        self,
        sample_pdf_path: Path,
        sample_pdf_content: dict[str, str],
    ) -> None:
        """Chunks should contain actual text from the PDF, not garbage.

        We verify that key phrases from the original PDF appear
        somewhere in the chunked output. This catches extraction
        quality regressions.
        """
        doc_repo = InMemoryDocumentRepository()
        chunk_repo = InMemoryChunkRepository()
        service = IngestionApplicationService(
            parser=PdfDocumentParser(),
            document_repository=doc_repo,
            chunk_repository=chunk_repo,
        )

        result = service.ingest_document(str(sample_pdf_path))

        # Concatenate all chunk contents to search across chunks
        all_chunk_text = " ".join(chunk.content for chunk in result.chunks)

        # Key phrases from the test PDF should appear in the chunks.
        assert sample_pdf_content["equipment_name"] in all_chunk_text
        assert sample_pdf_content["manufacturer"] in all_chunk_text

    def test_chunk_metadata_has_page_numbers(self, sample_pdf_path: Path) -> None:
        """Every chunk should have a valid page number in its metadata.

        Page numbers are critical for showing users *where* in the
        original document an answer came from. This test ensures
        the page assignment logic works correctly.
        """
        doc_repo = InMemoryDocumentRepository()
        chunk_repo = InMemoryChunkRepository()
        service = IngestionApplicationService(
            parser=PdfDocumentParser(),
            document_repository=doc_repo,
            chunk_repository=chunk_repo,
        )

        result = service.ingest_document(str(sample_pdf_path))

        for chunk in result.chunks:
            # Every chunk must have a page number
            assert chunk.metadata.page_number is not None
            # Page numbers should be between 1 and the total page count
            assert 1 <= chunk.metadata.page_number <= result.document.page_count
            # Character offsets should be non-negative
            assert chunk.metadata.char_start >= 0
            assert chunk.metadata.char_end > chunk.metadata.char_start

    def test_repository_counts_match_result(self, sample_pdf_path: Path) -> None:
        """Repository counts should match the ingestion result."""
        doc_repo = InMemoryDocumentRepository()
        chunk_repo = InMemoryChunkRepository()
        service = IngestionApplicationService(
            parser=PdfDocumentParser(),
            document_repository=doc_repo,
            chunk_repository=chunk_repo,
        )

        result = service.ingest_document(str(sample_pdf_path))

        assert doc_repo.count() == 1
        assert chunk_repo.count() == len(result.chunks)
        assert chunk_repo.count_for_document(result.document.id) == len(result.chunks)
