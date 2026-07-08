"""PDF document parser — extracts text from PDF files using pdfplumber.

This adapter implements the DocumentParser port for PDF files. It uses
the `pdfplumber` library, which is built on top of `pdfminer.six` and
provides reliable text extraction from real-world PDFs, including those
with complex layouts, tables, and multi-column formats.

Why pdfplumber over alternatives?
  - PyPDF2/pypdf: Fast but poor text extraction quality on complex layouts.
  - pdfminer.six: Powerful but low-level API, requires manual page handling.
  - pdfplumber: Best balance of extraction quality and developer experience.
  - Tika: Requires a Java server — too heavy for V1.

Architecture:
  - This file is an ADAPTER — it lives in the adapters/ directory.
  - It implements the DocumentParser port defined in ports/document_parser.py.
  - It imports from the domain layer (ParsedDocument) but never the reverse.
  - The domain layer has no idea that pdfplumber exists.

Bounded Context: Knowledge
Layer: Adapters (Outbound)
Dependencies: pdfplumber (external), knowledge.domain, knowledge.ports, shared

Usage:
    from forgemind.knowledge.adapters.pdf_parser import PdfDocumentParser

    parser = PdfDocumentParser()
    parsed = parser.parse(Path("data/pump_manual.pdf"))
    print(f"Extracted {parsed.page_count} pages")
    print(f"Total text length: {len(parsed.raw_text)} characters")
"""

from __future__ import annotations

import time
from pathlib import Path

import pdfplumber

from forgemind.knowledge.domain.parsed_document import ParsedDocument
from forgemind.shared.errors import DocumentParseError, UnsupportedFormatError
from forgemind.shared.logging import get_logger

# ── Logger ───────────────────────────────────────────────────────
# Each adapter gets its own named logger so log output clearly shows
# which component produced each message.
logger = get_logger(__name__)

# ── Constants ────────────────────────────────────────────────────

# File extensions this parser can handle. Must be lowercase with dots.
_SUPPORTED_EXTENSIONS: frozenset[str] = frozenset({".pdf"})

# Pages that produce fewer characters than this threshold are treated
# as "effectively blank" — they're likely cover pages, blank separator
# pages, or pages that contain only images (which pdfplumber can't
# extract text from). We still include them in page_texts but log a
# warning so operators know the extraction was incomplete.
_MIN_MEANINGFUL_PAGE_TEXT_LENGTH: int = 10

# Separator inserted between pages when concatenating raw_text.
# Two newlines create a visual paragraph break, which helps the
# sentence-boundary chunker in domain/services.py avoid merging
# the last sentence of page N with the first sentence of page N+1.
_PAGE_SEPARATOR: str = "\n\n"


class PdfDocumentParser:
    """Extracts text from PDF files using pdfplumber.

    This parser reads a PDF file page-by-page, extracts the text content
    from each page, and assembles the results into a ParsedDocument.

    It handles common real-world issues:
      - Blank or image-only pages (logged as warnings, not errors)
      - Corrupt PDFs (raised as DocumentParseError with context)
      - Wrong file extension (raised as UnsupportedFormatError)
      - Missing files (raised as FileNotFoundError)

    Thread Safety:
        This parser is stateless and thread-safe. Multiple threads can
        call parse() concurrently without issues.

    Example:
        >>> parser = PdfDocumentParser()
        >>> parsed = parser.parse(Path("equipment_manual.pdf"))
        >>> print(parsed.page_count)
        42
        >>> print(len(parsed.raw_text))
        158923
    """

    def parse(self, file_path: Path) -> ParsedDocument:
        """Parse a PDF file and extract its text content.

        Opens the PDF with pdfplumber, iterates through every page,
        extracts text, and assembles a ParsedDocument with both the
        full concatenated text and the per-page breakdown.

        Args:
            file_path: Path to the PDF file. Can be absolute or relative.

        Returns:
            A ParsedDocument with the extracted text and metadata.

        Raises:
            FileNotFoundError: If the file does not exist.
            UnsupportedFormatError: If the file extension is not .pdf.
            DocumentParseError: If pdfplumber cannot read the file
                (corrupt, encrypted, or otherwise unreadable).
        """
        # ── Step 1: Validate that the file exists ────────────────
        resolved_path = file_path.resolve()

        if not resolved_path.exists():
            msg = f"PDF file not found: {resolved_path}"
            raise FileNotFoundError(msg)

        # ── Step 2: Validate the file extension ──────────────────
        file_extension = resolved_path.suffix.lower()

        if file_extension not in _SUPPORTED_EXTENSIONS:
            raise UnsupportedFormatError(
                message=(
                    f"File '{resolved_path.name}' has extension '{file_extension}', "
                    f"but this parser only supports: {', '.join(sorted(_SUPPORTED_EXTENSIONS))}. "
                    f"Use a different parser for this file type."
                ),
                context={"file_path": str(resolved_path), "extension": file_extension},
            )

        # ── Step 3: Open and parse the PDF ───────────────────────
        logger.info(
            "parsing_pdf_started",
            file_path=str(resolved_path),
            file_name=resolved_path.name,
            file_size_bytes=resolved_path.stat().st_size,
        )

        parse_start_time = time.monotonic()
        page_texts: list[str] = []
        pdf_metadata: dict[str, str] = {}

        try:
            with pdfplumber.open(resolved_path) as pdf:
                # Extract metadata from the PDF's document info dictionary.
                # pdfplumber exposes this as pdf.metadata, a dict that may
                # contain keys like "Title", "Author", "Creator", etc.
                # We only keep non-empty string values.
                if pdf.metadata:
                    pdf_metadata = {
                        key: str(value)
                        for key, value in pdf.metadata.items()
                        if value and str(value).strip()
                    }

                # ── Step 4: Extract text from each page ──────────
                for page_index, page in enumerate(pdf.pages):
                    # page_index is 0-based; human-readable page numbers are 1-based
                    page_number = page_index + 1

                    # extract_text() returns None if the page has no extractable text
                    extracted_text = page.extract_text() or ""
                    cleaned_text = extracted_text.strip()

                    if len(cleaned_text) < _MIN_MEANINGFUL_PAGE_TEXT_LENGTH:
                        # This page is effectively blank — likely an image-only
                        # page or a blank separator. We keep it in the page_texts
                        # list (to preserve correct page numbering) but log it
                        # so operators can investigate if too many pages are blank.
                        logger.debug(
                            "page_has_minimal_text",
                            page_number=page_number,
                            character_count=len(cleaned_text),
                            threshold=_MIN_MEANINGFUL_PAGE_TEXT_LENGTH,
                            file_name=resolved_path.name,
                        )

                    page_texts.append(cleaned_text)

        except Exception as error:
            # pdfplumber can raise various exceptions for corrupt PDFs:
            # - pdfminer.pdfparser.PDFSyntaxError for malformed PDF structure
            # - pdfminer.pdfdocument.PDFPasswordIncorrect for encrypted files
            # - Various other exceptions for damaged content streams
            #
            # We catch all exceptions here and wrap them in DocumentParseError
            # so the caller gets a consistent, domain-specific error type
            # regardless of which low-level library issue occurred.
            parse_duration_seconds = time.monotonic() - parse_start_time

            logger.error(
                "parsing_pdf_failed",
                file_path=str(resolved_path),
                file_name=resolved_path.name,
                error_type=type(error).__name__,
                error_message=str(error),
                duration_seconds=round(parse_duration_seconds, 3),
            )

            raise DocumentParseError(
                message=(
                    f"Failed to parse PDF file '{resolved_path.name}': {error}. "
                    f"The file may be corrupt, encrypted, or in an unsupported PDF format."
                ),
                context={
                    "file_path": str(resolved_path),
                    "error_type": type(error).__name__,
                },
            ) from error

        # ── Step 5: Assemble the ParsedDocument ──────────────────
        # Concatenate all page texts with a separator that helps the
        # chunker maintain page boundaries.
        raw_text = _PAGE_SEPARATOR.join(page_texts)
        total_pages = len(page_texts)
        parse_duration_seconds = time.monotonic() - parse_start_time

        # Count how many pages actually had meaningful text
        meaningful_page_count = sum(
            1 for text in page_texts if len(text) >= _MIN_MEANINGFUL_PAGE_TEXT_LENGTH
        )

        logger.info(
            "parsing_pdf_completed",
            file_path=str(resolved_path),
            file_name=resolved_path.name,
            total_pages=total_pages,
            meaningful_pages=meaningful_page_count,
            total_characters=len(raw_text),
            duration_seconds=round(parse_duration_seconds, 3),
            metadata_keys=list(pdf_metadata.keys()),
        )

        # If the entire PDF produced no usable text, this is likely an
        # image-only PDF (scanned document without OCR). We still return
        # a result, but the ParsedDocument's __post_init__ validation
        # will raise ValueError if raw_text is empty.
        return ParsedDocument(
            raw_text=raw_text,
            page_texts=tuple(page_texts),
            page_count=total_pages,
            metadata=pdf_metadata,
        )

    def supported_extensions(self) -> frozenset[str]:
        """Return the file extensions this parser can handle.

        Returns:
            frozenset containing ".pdf".
        """
        return _SUPPORTED_EXTENSIONS
