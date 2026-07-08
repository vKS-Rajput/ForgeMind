"""Document parser port — the ability to read a file and extract text.

This port defines what the Knowledge bounded context needs from
"something that can read document files." It does NOT define how
that reading happens — that's the adapter's job.

Why is this separate from EntityExtractor?
  - DocumentParser reads *files* and produces *text*.
  - EntityExtractor reads *text* and produces *domain entities*.
  - They change for different reasons (new file format vs. new NLP model).
  - Keeping them separate follows the Single Responsibility Principle.

Bounded Context: Knowledge
Layer: Ports (Outbound)
Dependencies: knowledge.domain.parsed_document

Usage:
    # The port is consumed by the IngestionService, not called directly.
    class IngestionService:
        def __init__(self, parser: DocumentParser, ...):
            self._parser = parser

        def ingest(self, path: Path) -> Document:
            parsed = self._parser.parse(path)  # port call
            ...
"""

from __future__ import annotations

from pathlib import Path
from typing import Protocol

from forgemind.knowledge.domain.parsed_document import ParsedDocument


class DocumentParser(Protocol):
    """Reads a document file from disk and extracts its text content.

    Implementations of this protocol handle the actual byte-level
    parsing of specific file formats. Each implementation declares
    which file extensions it supports via `supported_extensions()`.

    Contract:
        - `parse()` MUST return a ParsedDocument with non-empty raw_text.
        - `parse()` MUST raise DocumentParseError if the file is corrupt.
        - `parse()` MUST raise UnsupportedFormatError if the extension is wrong.
        - `parse()` MUST raise FileNotFoundError if the file doesn't exist.
        - `supported_extensions()` MUST return lowercase extensions with dots
          (e.g., frozenset({".pdf", ".PDF"}) is WRONG; use frozenset({".pdf"})).
    """

    def parse(self, file_path: Path) -> ParsedDocument:
        """Parse a document file and extract its text content.

        This is the core operation of the parser. It opens the file,
        reads its contents, extracts text (preserving page boundaries
        where applicable), and returns a ParsedDocument.

        Args:
            file_path: Absolute or relative path to the document file.
                The file must exist and be readable.

        Returns:
            A ParsedDocument containing the extracted text, per-page
            breakdown, page count, and any metadata the parser discovered.

        Raises:
            FileNotFoundError: The file does not exist at the given path.
            DocumentParseError: The file exists but could not be parsed
                (e.g., corrupt PDF, encrypted file, password-protected).
            UnsupportedFormatError: The file extension is not supported
                by this parser implementation.
        """
        ...

    def supported_extensions(self) -> frozenset[str]:
        """Return the set of file extensions this parser can handle.

        Extensions are lowercase and include the leading dot.

        Returns:
            An immutable set of supported extensions.
            Example: frozenset({".pdf"})
        """
        ...
