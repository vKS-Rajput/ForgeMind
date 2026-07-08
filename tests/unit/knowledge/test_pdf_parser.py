"""Tests for the PDF document parser adapter.

These tests verify that PdfDocumentParser correctly extracts text
from PDF files and handles error cases gracefully. The tests use
a fixture-generated PDF (see tests/fixtures/conftest.py) to avoid
committing binary files to the repository.

Test Categories:
  - Happy path: Parse a real PDF, verify text extraction quality.
  - Error handling: Missing files, wrong extensions, corrupt PDFs.
  - Metadata: Supported extensions, page count, metadata extraction.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from forgemind.knowledge.adapters.pdf_parser import PdfDocumentParser
from forgemind.shared.errors import DocumentParseError, UnsupportedFormatError

pytestmark = pytest.mark.unit


class TestPdfParserHappyPath:
    """Verify correct text extraction from valid PDF files."""

    def test_parse_extracts_text_from_all_pages(self, sample_pdf_path: Path) -> None:
        """The parser should extract text from every page of the PDF."""
        parser = PdfDocumentParser()

        parsed = parser.parse(sample_pdf_path)

        # The sample PDF has 2 pages, so we expect text from both.
        assert parsed.page_count == 2
        assert len(parsed.page_texts) == 2

    def test_parse_returns_non_empty_raw_text(self, sample_pdf_path: Path) -> None:
        """raw_text should contain the full concatenated text."""
        parser = PdfDocumentParser()

        parsed = parser.parse(sample_pdf_path)

        # The text should be substantial — at least several hundred characters.
        assert len(parsed.raw_text) > 200

    def test_parse_extracts_key_content(
        self,
        sample_pdf_path: Path,
        sample_pdf_content: dict[str, str],
    ) -> None:
        """The extracted text should contain key phrases from the PDF.

        This test verifies extraction quality — not just that we got
        *some* text, but that we got the *right* text.
        """
        parser = PdfDocumentParser()

        parsed = parser.parse(sample_pdf_path)

        # Each of these phrases appears in the generated test PDF.
        # If the parser fails to extract them, text quality is degraded.
        assert sample_pdf_content["equipment_name"] in parsed.raw_text
        assert sample_pdf_content["manufacturer"] in parsed.raw_text
        assert sample_pdf_content["component"] in parsed.raw_text
        assert sample_pdf_content["symptom"] in parsed.raw_text

    def test_parse_preserves_page_text_separately(self, sample_pdf_path: Path) -> None:
        """page_texts should contain per-page content, not just raw_text."""
        parser = PdfDocumentParser()

        parsed = parser.parse(sample_pdf_path)

        # Page 1 should have the equipment overview.
        page_1_text = parsed.page_texts[0]
        assert "Pump P-101" in page_1_text
        assert "centrifugal pump" in page_1_text

        # Page 2 should have the troubleshooting content.
        page_2_text = parsed.page_texts[1]
        assert "Troubleshooting" in page_2_text or "vibration" in page_2_text.lower()


class TestPdfParserErrorHandling:
    """Verify graceful error handling for invalid inputs."""

    def test_parse_missing_file_raises_file_not_found(self, tmp_path: Path) -> None:
        """A non-existent file should raise FileNotFoundError, not crash."""
        parser = PdfDocumentParser()
        non_existent_path = tmp_path / "this_file_does_not_exist.pdf"

        with pytest.raises(FileNotFoundError, match="not found"):
            parser.parse(non_existent_path)

    def test_parse_wrong_extension_raises_unsupported_format(self, tmp_path: Path) -> None:
        """A file with the wrong extension should be rejected early."""
        parser = PdfDocumentParser()

        # Create a text file with .txt extension
        text_file = tmp_path / "document.txt"
        text_file.write_text("This is plain text, not a PDF.")

        with pytest.raises(UnsupportedFormatError):
            parser.parse(text_file)

    def test_parse_corrupt_pdf_raises_document_parse_error(self, tmp_path: Path) -> None:
        """A file that has .pdf extension but isn't a real PDF should fail."""
        parser = PdfDocumentParser()

        # Create a file with .pdf extension but garbage content
        corrupt_pdf = tmp_path / "corrupt.pdf"
        corrupt_pdf.write_bytes(b"This is not a real PDF file content!")

        # This should raise DocumentParseError, not an unhandled exception.
        with pytest.raises((DocumentParseError, ValueError)):
            parser.parse(corrupt_pdf)

    def test_parse_empty_pdf_raises_error(self, tmp_path: Path) -> None:
        """A zero-byte .pdf file should fail gracefully."""
        parser = PdfDocumentParser()

        empty_pdf = tmp_path / "empty.pdf"
        empty_pdf.write_bytes(b"")

        with pytest.raises((DocumentParseError, ValueError)):
            parser.parse(empty_pdf)


class TestPdfParserMetadata:
    """Verify parser metadata and configuration."""

    def test_supported_extensions_contains_pdf(self) -> None:
        """The parser must declare support for .pdf files."""
        parser = PdfDocumentParser()

        extensions = parser.supported_extensions()

        assert ".pdf" in extensions

    def test_supported_extensions_is_frozen(self) -> None:
        """Supported extensions should be immutable (frozenset)."""
        parser = PdfDocumentParser()

        extensions = parser.supported_extensions()

        assert isinstance(extensions, frozenset)

    def test_parser_is_stateless(self, sample_pdf_path: Path) -> None:
        """Parsing the same file twice should produce identical results."""
        parser = PdfDocumentParser()

        first_parse = parser.parse(sample_pdf_path)
        second_parse = parser.parse(sample_pdf_path)

        assert first_parse.raw_text == second_parse.raw_text
        assert first_parse.page_count == second_parse.page_count
