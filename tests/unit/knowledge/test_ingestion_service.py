"""Tests for the ingestion application service.

These tests verify the full ingestion pipeline by wiring together
real adapters (in-memory repositories) with the PDF parser. They
test the orchestration logic: parsing → dedup → Document → chunks → event.

Test Categories:
  - File ingestion: End-to-end PDF ingestion.
  - Text ingestion: Direct text ingestion without a file.
  - Deduplication: Duplicate detection and rejection.
  - Error handling: Invalid inputs, empty content.
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
from forgemind.knowledge.domain.value_objects import DocumentType
from forgemind.shared.errors import IngestionError

pytestmark = pytest.mark.unit


# ── Fixture ──────────────────────────────────────────────────────


@pytest.fixture()
def ingestion_service() -> IngestionApplicationService:
    """Create an IngestionApplicationService with fresh in-memory adapters.

    Each test gets its own service instance with empty repositories,
    ensuring tests don't interfere with each other.
    """
    return IngestionApplicationService(
        parser=PdfDocumentParser(),
        document_repository=InMemoryDocumentRepository(),
        chunk_repository=InMemoryChunkRepository(),
    )


@pytest.fixture()
def ingestion_service_with_repos() -> tuple[
    IngestionApplicationService, InMemoryDocumentRepository, InMemoryChunkRepository
]:
    """Create an IngestionApplicationService with accessible repositories.

    Returns both the service and the repositories so tests can inspect
    the stored state after ingestion.
    """
    doc_repo = InMemoryDocumentRepository()
    chunk_repo = InMemoryChunkRepository()
    service = IngestionApplicationService(
        parser=PdfDocumentParser(),
        document_repository=doc_repo,
        chunk_repository=chunk_repo,
    )
    return service, doc_repo, chunk_repo


# ── File Ingestion Tests ─────────────────────────────────────────


class TestFileIngestion:
    """Verify the end-to-end file ingestion pipeline."""

    def test_ingest_pdf_creates_document_and_chunks(
        self,
        sample_pdf_path: Path,
        ingestion_service: IngestionApplicationService,
    ) -> None:
        """Ingesting a PDF should produce a Document and multiple Chunks."""
        result = ingestion_service.ingest_document(str(sample_pdf_path))

        assert result.document is not None
        assert result.document.title == "pump_manual_p101"
        assert result.document.page_count == 2
        assert len(result.chunks) > 0

    def test_ingest_pdf_emits_correct_event(
        self,
        sample_pdf_path: Path,
        ingestion_service: IngestionApplicationService,
    ) -> None:
        """The ingestion event should have the correct document ID and chunk count."""
        result = ingestion_service.ingest_document(str(sample_pdf_path))

        assert result.event.document_id == str(result.document.id)
        assert result.event.chunk_count == len(result.chunks)
        assert result.event.title == result.document.title

    def test_ingest_pdf_stores_in_repositories(
        self,
        sample_pdf_path: Path,
        ingestion_service_with_repos: tuple,
    ) -> None:
        """After ingestion, the Document and Chunks should be in their repositories."""
        service, doc_repo, chunk_repo = ingestion_service_with_repos

        result = service.ingest_document(str(sample_pdf_path))

        # Document should be in the repository
        stored_doc = doc_repo.get(result.document.id)
        assert stored_doc is not None
        assert stored_doc.id == result.document.id

        # Chunks should be in the repository
        stored_chunks = chunk_repo.get_chunks_for_document(result.document.id)
        assert len(stored_chunks) == len(result.chunks)

    def test_ingest_pdf_chunks_have_content(
        self,
        sample_pdf_path: Path,
        ingestion_service: IngestionApplicationService,
    ) -> None:
        """Every chunk should contain non-empty text content."""
        result = ingestion_service.ingest_document(str(sample_pdf_path))

        for chunk in result.chunks:
            assert len(chunk.content.strip()) > 0, f"Chunk {chunk.chunk_index} has empty content"

    def test_ingest_pdf_chunks_have_page_metadata(
        self,
        sample_pdf_path: Path,
        ingestion_service: IngestionApplicationService,
    ) -> None:
        """Chunks should have page_number metadata populated."""
        result = ingestion_service.ingest_document(str(sample_pdf_path))

        for chunk in result.chunks:
            assert chunk.metadata.page_number is not None, (
                f"Chunk {chunk.chunk_index} is missing page_number metadata"
            )
            assert chunk.metadata.page_number >= 1, (
                f"Chunk {chunk.chunk_index} has invalid page_number: {chunk.metadata.page_number}"
            )

    def test_ingest_with_document_type(
        self,
        sample_pdf_path: Path,
        ingestion_service: IngestionApplicationService,
    ) -> None:
        """The caller can specify the document type."""
        result = ingestion_service.ingest_document(
            str(sample_pdf_path),
            document_type=DocumentType.MANUAL,
        )

        assert result.document.document_type is DocumentType.MANUAL


# ── Text Ingestion Tests ─────────────────────────────────────────


class TestTextIngestion:
    """Verify direct text ingestion without a file."""

    def test_ingest_text_creates_document(
        self,
        ingestion_service: IngestionApplicationService,
    ) -> None:
        """Ingesting raw text should create a Document entity."""
        result = ingestion_service.ingest_text(
            text="Pump P-101 operates at 3000 RPM. Regular maintenance is required.",
            title="Pump Notes",
        )

        assert result.document is not None
        assert result.document.title == "Pump Notes"
        assert result.document.source_path == "<direct-text-input>"

    def test_ingest_text_creates_chunks(
        self,
        ingestion_service: IngestionApplicationService,
    ) -> None:
        """Ingested text should be chunked."""
        result = ingestion_service.ingest_text(
            text="Pump P-101 operates at 3000 RPM. Regular maintenance is required.",
            title="Pump Notes",
        )

        assert len(result.chunks) >= 1
        assert result.event.chunk_count == len(result.chunks)

    def test_ingest_text_empty_raises_value_error(
        self,
        ingestion_service: IngestionApplicationService,
    ) -> None:
        """Empty text should be rejected immediately."""
        with pytest.raises(ValueError, match="empty"):
            ingestion_service.ingest_text(text="", title="Empty")

    def test_ingest_text_empty_title_raises_value_error(
        self,
        ingestion_service: IngestionApplicationService,
    ) -> None:
        """Empty title should be rejected."""
        with pytest.raises(ValueError, match="title"):
            ingestion_service.ingest_text(text="Some content.", title="")


# ── Deduplication Tests ──────────────────────────────────────────


class TestDeduplication:
    """Verify duplicate document detection and rejection."""

    def test_duplicate_file_is_rejected(
        self,
        sample_pdf_path: Path,
        ingestion_service: IngestionApplicationService,
    ) -> None:
        """Ingesting the same file twice should raise IngestionError."""
        # First ingestion should succeed
        ingestion_service.ingest_document(str(sample_pdf_path))

        # Second ingestion should be rejected as duplicate
        with pytest.raises(IngestionError, match="already been ingested"):
            ingestion_service.ingest_document(str(sample_pdf_path))

    def test_duplicate_text_is_rejected(
        self,
        ingestion_service: IngestionApplicationService,
    ) -> None:
        """Ingesting the same text twice should raise IngestionError."""
        text = "Pump P-101 maintenance procedures for bearing replacement."

        ingestion_service.ingest_text(text=text, title="First Upload")

        with pytest.raises(IngestionError, match="already been ingested"):
            ingestion_service.ingest_text(text=text, title="Second Upload")

    def test_different_content_is_not_duplicate(
        self,
        ingestion_service_with_repos: tuple,
    ) -> None:
        """Different content should not trigger duplicate detection."""
        service, doc_repo, _ = ingestion_service_with_repos

        service.ingest_text(text="Content A is unique.", title="Doc A")
        service.ingest_text(text="Content B is different.", title="Doc B")

        assert doc_repo.count() == 2
