"""Parsed document — the intermediate result of file parsing.

When we read a PDF (or any document file) from disk, we don't immediately
create a domain Document entity. Instead, we produce a ParsedDocument —
a lightweight, immutable snapshot of what the parser found. This separation
exists because:

  1. Parsing is about *reading bytes from a file*.
  2. Creating a Document is about *assigning identity and business meaning*.

The ParsedDocument carries the raw text, per-page breakdown, and any
metadata the parser discovered (like the PDF title or author). The
ingestion service then uses this data to create the proper domain entities.

Bounded Context: Knowledge
Layer: Domain (Value Object)
Dependencies: None (pure Python)

Usage:
    # Created by a DocumentParser adapter, consumed by IngestionService
    parsed = pdf_parser.parse(Path("manual.pdf"))
    print(f"Extracted {parsed.page_count} pages, {len(parsed.raw_text)} chars")
    for page_number, page_text in enumerate(parsed.page_texts, start=1):
        print(f"  Page {page_number}: {len(page_text)} characters")
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True, slots=True)
class ParsedDocument:
    """The result of parsing a document file into text.

    This is NOT a domain entity — it has no identity (no ID field).
    It's a value object that exists only during the ingestion pipeline,
    bridging the gap between "raw file on disk" and "domain Document."

    Attributes:
        raw_text: The full text content of the document, concatenated
            from all pages. This is what gets chunked and embedded.
        page_texts: Text content broken down by page. Tuple index 0
            corresponds to page 1 of the document. Used to assign
            accurate page numbers to chunks.
        page_count: Total number of pages in the source document.
            For non-paginated documents (plain text), this is 1.
        metadata: Key-value pairs of parser-discovered metadata.
            Examples: {"title": "Pump P-101 Manual", "author": "Meridian Engineering"}
            This dict is intentionally string-only for serialization safety.
    """

    raw_text: str
    page_texts: tuple[str, ...] = ()
    page_count: int = 1
    metadata: dict[str, str] = field(default_factory=dict)

    def __post_init__(self) -> None:
        """Validate that the parsed document contains usable content."""
        if not self.raw_text.strip():
            msg = (
                "ParsedDocument.raw_text must not be empty. "
                "The parser extracted no usable text from the file. "
                "This usually means the file is image-only or corrupt."
            )
            raise ValueError(msg)

        if self.page_count < 1:
            msg = (
                f"ParsedDocument.page_count must be >= 1, got {self.page_count}. "
                "Even a single-page document has page_count=1."
            )
            raise ValueError(msg)
