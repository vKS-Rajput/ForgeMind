"""Ingestion application service — orchestrates the document ingestion pipeline.

This is the most important file in the adapters layer. It implements the
IngestionService inbound port by coordinating four collaborators:

  1. DocumentParser    — reads a file and produces text (e.g., PdfDocumentParser)
  2. DocumentRepository — stores the Document entity (e.g., InMemoryDocumentRepository)
  3. ChunkRepository    — stores the Chunk entities (e.g., InMemoryChunkRepository)
  4. Domain services    — chunk_text() for splitting text into chunks

The pipeline flow:

    ┌──────────────┐     ┌────────────────────┐     ┌──────────────────┐
    │  File on disk │────>│  DocumentParser     │────>│  ParsedDocument  │
    │  (PDF, etc.)  │     │  (reads bytes)      │     │  (raw text)      │
    └──────────────┘     └────────────────────┘     └────────┬─────────┘
                                                             │
                                                             ▼
                          ┌────────────────────┐     ┌──────────────────┐
                          │  Dedup check       │<────│  Compute hash    │
                          │  (exists_by_hash)  │     │  (SHA-256)       │
                          └────────┬───────────┘     └──────────────────┘
                                   │ (new document)
                                   ▼
    ┌──────────────┐     ┌────────────────────┐     ┌──────────────────┐
    │  Document    │<────│  Document.create()  │     │  chunk_text()    │
    │  Repository  │     │  (domain factory)   │     │  (domain svc)    │
    └──────────────┘     └────────────────────┘     └────────┬─────────┘
                                                             │
                                                             ▼
    ┌──────────────┐     ┌────────────────────┐     ┌──────────────────┐
    │  Chunk       │<────│  Chunk.create()     │<────│  Chunk strings   │
    │  Repository  │     │  (domain factory)   │     │  with metadata   │
    └──────────────┘     └────────────────────┘     └──────────────────┘
                                                             │
                                                             ▼
                                                     ┌──────────────────┐
                                                     │ DocumentIngested │
                                                     │ (domain event)   │
                                                     └──────────────────┘

Why is this in adapters/ and not a domain service?
  - It orchestrates I/O operations (file parsing, repository persistence).
  - Domain services are pure functions with no I/O.
  - The inbound PORT (IngestionService protocol) lives in ports/inbound.py.
  - This SERVICE (implementation) lives in adapters/ because it touches adapters.

Bounded Context: Knowledge
Layer: Adapters (Application Service)
Dependencies: All knowledge domain + ports + other adapters

Usage:
    from forgemind.knowledge.adapters.ingestion_service import (
        IngestionApplicationService,
    )

    service = IngestionApplicationService(
        parser=PdfDocumentParser(),
        document_repository=InMemoryDocumentRepository(),
        chunk_repository=InMemoryChunkRepository(),
    )
    document, event = service.ingest_document("/data/pump_manual.pdf")
    print(f"Ingested '{document.title}' with {event.chunk_count} chunks")
"""

from __future__ import annotations

import time
from dataclasses import dataclass
from pathlib import Path

from forgemind.knowledge.domain.entities import Chunk, Document
from forgemind.knowledge.domain.events import DocumentIngested
from forgemind.knowledge.domain.parsed_document import ParsedDocument
from forgemind.knowledge.domain.services import chunk_text
from forgemind.knowledge.domain.value_objects import ChunkMetadata, DocumentType
from forgemind.knowledge.ports.document_parser import DocumentParser
from forgemind.knowledge.ports.outbound import ChunkRepository, DocumentRepository
from forgemind.shared.errors import IngestionError
from forgemind.shared.logging import get_logger
from forgemind.shared.types import DocumentId

# ── Logger ───────────────────────────────────────────────────────
logger = get_logger(__name__)

# ── Constants ────────────────────────────────────────────────────

# Default chunk size in characters. 500 characters is roughly 80-100 words,
# which is a good balance between:
#   - Too small (loses context, fragments sentences)
#   - Too large (dilutes relevance in vector search, exceeds LLM context)
# This can be overridden per-call via the chunk_size parameter.
_DEFAULT_CHUNK_SIZE: int = 500

# Default overlap in characters between adjacent chunks. 50 characters
# (roughly 8-12 words) ensures that sentences split across chunk boundaries
# appear in at least one chunk in their entirety. This improves retrieval
# quality by preventing "cliff edge" information loss at chunk boundaries.
_DEFAULT_CHUNK_OVERLAP: int = 50


# ── Result Type ──────────────────────────────────────────────────


@dataclass(frozen=True, slots=True)
class IngestionResult:
    """The outcome of ingesting a document.

    Returned by the ingestion service to give the caller everything
    they need: the stored document, the chunks produced, and the
    domain event describing what happened.

    Attributes:
        document: The Document entity that was created and stored.
        chunks: The list of Chunk entities that were created and stored.
        event: The DocumentIngested domain event describing this ingestion.
    """

    document: Document
    chunks: list[Chunk]
    event: DocumentIngested


# ── Application Service ─────────────────────────────────────────


class IngestionApplicationService:
    """Orchestrates the full document ingestion pipeline.

    This service is the entry point for getting documents into ForgeMind.
    It coordinates parsing, deduplication, chunking, and storage —
    returning a complete IngestionResult with the stored entities.

    The service is stateless — all state lives in the repositories.
    Multiple instances can safely share the same repository objects.

    Args:
        parser: Adapter that reads files and produces text.
        document_repository: Adapter that stores Document entities.
        chunk_repository: Adapter that stores Chunk entities.
        default_chunk_size: Default maximum chunk size in characters.
        default_chunk_overlap: Default overlap between adjacent chunks.

    Example:
        >>> service = IngestionApplicationService(
        ...     parser=PdfDocumentParser(),
        ...     document_repository=InMemoryDocumentRepository(),
        ...     chunk_repository=InMemoryChunkRepository(),
        ... )
        >>> result = service.ingest_document("/data/pump_manual.pdf")
        >>> print(f"Created {len(result.chunks)} chunks from '{result.document.title}'")
    """

    def __init__(
        self,
        parser: DocumentParser,
        document_repository: DocumentRepository,
        chunk_repository: ChunkRepository,
        default_chunk_size: int = _DEFAULT_CHUNK_SIZE,
        default_chunk_overlap: int = _DEFAULT_CHUNK_OVERLAP,
    ) -> None:
        """Initialize the ingestion service with its collaborators.

        Args:
            parser: The document parser adapter to use for reading files.
            document_repository: The repository for storing Document entities.
                Must implement the DocumentRepository protocol.
            chunk_repository: The repository for storing Chunk entities.
                Must implement the ChunkRepository protocol.
            default_chunk_size: Maximum characters per chunk (default: 500).
            default_chunk_overlap: Character overlap between chunks (default: 50).
        """
        # Store collaborators as private attributes.
        self._parser = parser
        self._document_repository = document_repository
        self._chunk_repository = chunk_repository
        self._default_chunk_size = default_chunk_size
        self._default_chunk_overlap = default_chunk_overlap

    def ingest_document(
        self,
        file_path: str,
        *,
        document_type: DocumentType = DocumentType.UNKNOWN,
        chunk_size: int | None = None,
        chunk_overlap: int | None = None,
    ) -> IngestionResult:
        """Ingest a document file through the full pipeline.

        This is the primary entry point. It performs these steps:
          1. Parse the file into text using the DocumentParser adapter.
          2. Check if this exact document was already ingested (by content hash).
          3. Create and store a Document domain entity.
          4. Split the text into chunks using the domain chunking service.
          5. Create and store Chunk domain entities with page metadata.
          6. Emit a DocumentIngested domain event.

        Args:
            file_path: Path to the document file (PDF, etc.).
            document_type: Classification for the document. Defaults to UNKNOWN
                if the caller doesn't know the type.
            chunk_size: Override the default maximum chunk size (in characters).
                If None, uses the service's default_chunk_size.
            chunk_overlap: Override the default chunk overlap (in characters).
                If None, uses the service's default_chunk_overlap.

        Returns:
            An IngestionResult containing the Document, Chunks, and event.

        Raises:
            FileNotFoundError: If the file does not exist.
            UnsupportedFormatError: If the file format is not supported.
            DocumentParseError: If the file is corrupt or unreadable.
            IngestionError: If a document with the same content already exists.
        """
        pipeline_start_time = time.monotonic()
        effective_chunk_size = chunk_size or self._default_chunk_size
        effective_chunk_overlap = chunk_overlap or self._default_chunk_overlap
        path = Path(file_path)

        logger.info(
            "ingestion_started",
            file_path=file_path,
            file_name=path.name,
            document_type=document_type.value,
            chunk_size=effective_chunk_size,
            chunk_overlap=effective_chunk_overlap,
        )

        # ── Step 1: Parse the file into text ─────────────────────
        # The parser handles all file-level concerns: reading bytes,
        # extracting text, handling corrupt files, etc.
        parsed: ParsedDocument = self._parser.parse(path)

        logger.info(
            "ingestion_parse_complete",
            file_name=path.name,
            page_count=parsed.page_count,
            total_characters=len(parsed.raw_text),
        )

        # ── Step 2: Check for duplicates ─────────────────────────
        # We compute the content hash to detect if this exact document
        # was already ingested. This makes ingestion idempotent: uploading
        # the same file twice doesn't create duplicate entries.
        import hashlib

        content_hash = hashlib.sha256(parsed.raw_text.encode("utf-8")).hexdigest()

        if self._document_repository.exists_by_hash(content_hash):
            pipeline_duration = time.monotonic() - pipeline_start_time
            logger.warning(
                "ingestion_duplicate_detected",
                file_name=path.name,
                content_hash_prefix=content_hash[:12],
                duration_seconds=round(pipeline_duration, 3),
            )
            raise IngestionError(
                message=(
                    f"Document '{path.name}' has already been ingested. "
                    f"Content hash: {content_hash[:12]}... "
                    f"Duplicate ingestion was skipped to prevent data duplication."
                ),
                context={
                    "file_path": file_path,
                    "content_hash": content_hash,
                },
            )

        # ── Step 3: Create and store the Document entity ─────────
        document = Document.create(
            title=path.stem,
            source_path=str(path.resolve()),
            content=parsed.raw_text,
            document_type=document_type,
            page_count=parsed.page_count,
            metadata=parsed.metadata,
        )

        self._document_repository.save(document)

        logger.info(
            "ingestion_document_created",
            document_id=str(document.id),
            title=document.title,
            content_hash_prefix=document.content_hash[:12],
        )

        # ── Step 4: Split text into chunks ───────────────────────
        # The chunk_text() domain service splits at sentence boundaries
        # with configurable overlap. It returns plain strings — the
        # domain entities are created in the next step.
        chunk_content_strings: list[str] = chunk_text(
            text=parsed.raw_text,
            max_chunk_size=effective_chunk_size,
            overlap_size=effective_chunk_overlap,
        )

        logger.info(
            "ingestion_chunking_complete",
            document_id=str(document.id),
            chunk_count=len(chunk_content_strings),
            chunk_size_setting=effective_chunk_size,
            overlap_setting=effective_chunk_overlap,
        )

        # ── Step 5: Create Chunk entities with page metadata ─────
        # For each chunk string, we determine which page it belongs to
        # by tracking character positions in the original text.
        chunks: list[Chunk] = _create_chunks_with_metadata(
            document_id=document.id,
            chunk_strings=chunk_content_strings,
            parsed_document=parsed,
        )

        # ── Step 6: Store chunks ─────────────────────────────────
        self._chunk_repository.save_chunks(chunks)

        # ── Step 7: Emit domain event ────────────────────────────
        pipeline_duration = time.monotonic() - pipeline_start_time

        event = DocumentIngested(
            document_id=str(document.id),
            title=document.title,
            chunk_count=len(chunks),
        )

        logger.info(
            "ingestion_completed",
            document_id=str(document.id),
            title=document.title,
            chunk_count=len(chunks),
            total_characters=len(parsed.raw_text),
            page_count=parsed.page_count,
            duration_seconds=round(pipeline_duration, 3),
        )

        return IngestionResult(
            document=document,
            chunks=chunks,
            event=event,
        )

    def ingest_text(
        self,
        text: str,
        title: str,
        *,
        document_type: DocumentType = DocumentType.UNKNOWN,
        metadata: dict[str, str] | None = None,
        chunk_size: int | None = None,
        chunk_overlap: int | None = None,
    ) -> IngestionResult:
        """Ingest raw text content directly, without a file.

        Useful for ingesting text from APIs, databases, or user input
        where there is no file on disk to parse.

        Args:
            text: The raw text content to ingest.
            title: Human-readable title for the document.
            document_type: Classification for the document.
            metadata: Optional additional metadata key-value pairs.
            chunk_size: Override the default chunk size.
            chunk_overlap: Override the default chunk overlap.

        Returns:
            An IngestionResult containing the Document, Chunks, and event.

        Raises:
            ValueError: If text or title is empty.
            IngestionError: If this exact text was already ingested.
        """
        pipeline_start_time = time.monotonic()
        effective_chunk_size = chunk_size or self._default_chunk_size
        effective_chunk_overlap = chunk_overlap or self._default_chunk_overlap

        if not text.strip():
            msg = "Cannot ingest empty text. Provide non-whitespace content."
            raise ValueError(msg)
        if not title.strip():
            msg = "Cannot ingest text without a title. Provide a descriptive title."
            raise ValueError(msg)

        logger.info(
            "text_ingestion_started",
            title=title,
            text_length=len(text),
            document_type=document_type.value,
        )

        # ── Deduplication check ──────────────────────────────────
        import hashlib

        content_hash = hashlib.sha256(text.encode("utf-8")).hexdigest()

        if self._document_repository.exists_by_hash(content_hash):
            raise IngestionError(
                message=(
                    f"Text with title '{title}' has already been ingested. "
                    f"Content hash: {content_hash[:12]}..."
                ),
                context={"title": title, "content_hash": content_hash},
            )

        # ── Create Document entity ───────────────────────────────
        document = Document.create(
            title=title,
            source_path="<direct-text-input>",
            content=text,
            document_type=document_type,
            page_count=1,
            metadata=metadata or {},
        )

        self._document_repository.save(document)

        # ── Chunk the text ───────────────────────────────────────
        chunk_content_strings = chunk_text(
            text=text,
            max_chunk_size=effective_chunk_size,
            overlap_size=effective_chunk_overlap,
        )

        # For direct text input, we create a simple ParsedDocument
        # with a single page so the metadata assignment works uniformly.
        parsed = ParsedDocument(
            raw_text=text,
            page_texts=(text,),
            page_count=1,
            metadata=metadata or {},
        )

        chunks = _create_chunks_with_metadata(
            document_id=document.id,
            chunk_strings=chunk_content_strings,
            parsed_document=parsed,
        )

        self._chunk_repository.save_chunks(chunks)

        # ── Emit domain event ────────────────────────────────────
        pipeline_duration = time.monotonic() - pipeline_start_time

        event = DocumentIngested(
            document_id=str(document.id),
            title=document.title,
            chunk_count=len(chunks),
        )

        logger.info(
            "text_ingestion_completed",
            document_id=str(document.id),
            title=document.title,
            chunk_count=len(chunks),
            duration_seconds=round(pipeline_duration, 3),
        )

        return IngestionResult(
            document=document,
            chunks=chunks,
            event=event,
        )


# ── Private Helper ───────────────────────────────────────────────


def _create_chunks_with_metadata(
    document_id: DocumentId,
    chunk_strings: list[str],
    parsed_document: ParsedDocument,
) -> list[Chunk]:
    """Create Chunk entities from content strings, assigning page metadata.

    For each chunk string, we determine which page it most likely belongs
    to by finding where the chunk's content appears in the per-page texts.
    This gives chunks accurate page_number metadata, which is critical
    for showing users *where* in the original document an answer came from.

    The algorithm works by tracking a character cursor through the
    concatenated raw text and mapping cursor positions to page boundaries.

    Args:
        document_id: The ID of the parent Document.
        chunk_strings: List of text strings produced by chunk_text().
        parsed_document: The ParsedDocument with per-page text breakdown.

    Returns:
        A list of Chunk entities with ChunkMetadata populated.
    """
    # Build a lookup table: for each page, what character offset does it
    # start at in the raw_text? This lets us map any character position
    # to a page number.
    page_boundaries: list[int] = _compute_page_boundaries(parsed_document)

    chunks: list[Chunk] = []
    # Track where we are in the raw_text as we assign chunks.
    # This cursor advances as we process each chunk string.
    character_cursor: int = 0

    for chunk_index, chunk_content in enumerate(chunk_strings):
        # Find where this chunk's content starts in the raw_text.
        # We search from the current cursor position forward to handle
        # overlapping chunks correctly (overlap means the same text
        # appears in consecutive chunks).
        content_position = parsed_document.raw_text.find(chunk_content, character_cursor)

        # If we can't find the exact chunk in raw_text (possible with
        # overlap or whitespace normalization), fall back to the cursor.
        if content_position == -1:
            content_position = character_cursor

        # Determine which page this chunk belongs to by finding the
        # last page boundary that is <= the chunk's starting position.
        page_number = _position_to_page_number(content_position, page_boundaries)

        # Create the Chunk entity with full positional metadata.
        chunk = Chunk.create(
            document_id=document_id,
            content=chunk_content,
            chunk_index=chunk_index,
            metadata=ChunkMetadata(
                page_number=page_number,
                position_in_document=chunk_index,
                char_start=content_position,
                char_end=content_position + len(chunk_content),
            ),
        )

        chunks.append(chunk)

        # Advance the cursor past this chunk's content.
        # We don't advance past the full chunk length when there's overlap,
        # because the next chunk might start in the middle of this one.
        character_cursor = content_position + 1

    return chunks


def _compute_page_boundaries(parsed_document: ParsedDocument) -> list[int]:
    r"""Compute the character offset where each page starts in raw_text.

    Given a ParsedDocument with per-page texts, calculates the cumulative
    character offsets that mark where each page begins in the concatenated
    raw_text string.

    Args:
        parsed_document: The ParsedDocument with page_texts.

    Returns:
        A list of character offsets, one per page. Index 0 is the start
        offset of page 1, index 1 is the start of page 2, etc.

    Example:
        If page_texts = ("Hello world", "Second page"), with page separator
        "\\n\\n", then raw_text = "Hello world\\n\\nSecond page" and the
        boundaries would be [0, 13] (13 = len("Hello world") + len("\\n\\n")).
    """
    # The page separator used by PdfDocumentParser when concatenating pages.
    # This must match the separator in pdf_parser.py. We define it here
    # rather than importing to avoid coupling between adapters.
    page_separator_length = 2  # "\n\n" is 2 characters

    boundaries: list[int] = []
    cumulative_offset: int = 0

    for page_index, page_text in enumerate(parsed_document.page_texts):
        boundaries.append(cumulative_offset)
        # After each page's text, add the separator length (except for the last page)
        cumulative_offset += len(page_text)
        if page_index < len(parsed_document.page_texts) - 1:
            cumulative_offset += page_separator_length

    return boundaries


def _position_to_page_number(
    character_position: int,
    page_boundaries: list[int],
) -> int:
    """Convert a character position in raw_text to a 1-based page number.

    Finds the last page boundary that is <= the character position,
    which corresponds to the page that contains that position.

    Args:
        character_position: A character offset in the raw_text string.
        page_boundaries: The list of page start offsets from
            _compute_page_boundaries().

    Returns:
        A 1-based page number (page 1 is the first page).
        Returns 1 if page_boundaries is empty.
    """
    if not page_boundaries:
        return 1

    # Walk backwards through page boundaries to find the page that
    # contains this character position. The first boundary that is
    # <= the position tells us the page.
    for page_index in range(len(page_boundaries) - 1, -1, -1):
        if page_boundaries[page_index] <= character_position:
            return page_index + 1  # Convert 0-based index to 1-based page number

    # Fallback: if the position is before any boundary, it's on page 1.
    return 1
