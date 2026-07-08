"""Shared test fixtures for ForgeMind test suite.

This module provides reusable fixtures used across unit, integration,
and golden tests. Fixtures follow the principle of least surprise:
they provide minimal, predictable test data.

Fixture index:
  - test_settings: Test-safe application settings (no LLM calls).
  - sample_pdf_path: A generated 2-page PDF for ingestion testing.
  - sample_pdf_content: Expected key phrases from the sample PDF.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from forgemind.shared.config import AppSettings


@pytest.fixture()
def test_settings() -> AppSettings:
    """Provide test-safe application settings.

    Overrides defaults to disable LLM calls and use in-memory stores.
    """
    return AppSettings(
        env="testing",
        debug=True,
        log_level="DEBUG",
        log_format="console",
    )


# ── PDF Fixtures ─────────────────────────────────────────────────
#
# Why generate PDFs at runtime instead of committing binary files?
#   1. Binary files bloat git history and can't be diffed.
#   2. Generated fixtures are self-documenting — the code shows
#      exactly what content the PDF contains.
#   3. Easy to modify: change the text here, and the test PDF updates.
#
# The generated PDF simulates a 2-page equipment manual for the
# fictional "Meridian Petrochemical Plant — Pump P-101", which is
# the running example throughout the ForgeMind documentation.


@pytest.fixture()
def sample_pdf_path(tmp_path: Path) -> Path:
    """Generate a small synthetic PDF for testing the ingestion pipeline.

    Creates a 2-page PDF that simulates a maintenance manual for
    Pump P-101 at the Meridian Petrochemical Plant. The content is
    designed to be realistic enough for entity extraction testing
    while being short enough for fast test execution.

    Page 1: Equipment overview and specifications.
    Page 2: Troubleshooting guide with symptoms and actions.

    Args:
        tmp_path: Pytest's built-in temporary directory fixture.

    Returns:
        Path to the generated PDF file.
    """
    # Import fpdf2 here so it remains a test-only dependency.
    # If fpdf2 is not installed, the test will skip gracefully.
    fpdf2 = pytest.importorskip("fpdf", reason="fpdf2 required for PDF generation")
    FPDF = fpdf2.FPDF  # noqa: N806  — class name from external library

    pdf = FPDF()
    pdf.set_auto_page_break(auto=True, margin=15)

    # ── Page 1: Equipment Overview ───────────────────────────────
    pdf.add_page()
    pdf.set_font("Helvetica", "B", size=16)
    pdf.cell(text="Meridian Petrochemical Plant", new_x="LMARGIN", new_y="NEXT")
    pdf.cell(text="Pump P-101 Maintenance Manual", new_x="LMARGIN", new_y="NEXT")
    pdf.ln(10)

    pdf.set_font("Helvetica", size=11)
    page_1_paragraphs = [
        (
            "Pump P-101 is a centrifugal pump located in Production Unit 3. "
            "It operates at 3000 RPM and is critical for feedstock transfer. "
            "The pump was manufactured by AquaFlow Industries in 2019."
        ),
        (
            "The pump assembly consists of the following major components: "
            "the impeller, the mechanical seal, the bearing housing with "
            "SKF 6205 bearings, and the coupling connecting to the motor. "
            "Regular inspection of these components is required every 6 months."
        ),
        (
            "Operating parameters must be maintained within the following limits: "
            "inlet pressure between 2.0 and 4.0 bar, outlet pressure between "
            "8.0 and 12.0 bar, flow rate of 150 cubic meters per hour, and "
            "bearing temperature must not exceed 80 degrees Celsius."
        ),
    ]
    for paragraph in page_1_paragraphs:
        pdf.multi_cell(w=0, text=paragraph)
        pdf.ln(5)

    # ── Page 2: Troubleshooting Guide ────────────────────────────
    pdf.add_page()
    pdf.set_font("Helvetica", "B", size=14)
    pdf.cell(text="Troubleshooting Guide", new_x="LMARGIN", new_y="NEXT")
    pdf.ln(5)

    pdf.set_font("Helvetica", size=11)
    page_2_paragraphs = [
        (
            "Excessive vibration is a common symptom indicating bearing failure "
            "or shaft misalignment. When vibration levels exceed 4.5 mm/s, "
            "immediately reduce pump speed and schedule an inspection."
        ),
        (
            "High bearing temperature above 80 degrees Celsius indicates "
            "insufficient lubrication or bearing degradation. Replace the "
            "SKF 6205 bearing and verify the lubrication system is functioning."
        ),
        (
            "Reduced flow rate below 120 cubic meters per hour may indicate "
            "impeller wear or cavitation. Inspect the impeller for erosion "
            "damage and check the inlet pressure is within specification."
        ),
        (
            "Seal leakage at the mechanical seal requires immediate attention. "
            "Shut down the pump and replace the mechanical seal assembly. "
            "Operating with a leaking seal risks environmental contamination."
        ),
    ]
    for paragraph in page_2_paragraphs:
        pdf.multi_cell(w=0, text=paragraph)
        pdf.ln(5)

    # ── Save the PDF ─────────────────────────────────────────────
    pdf_file_path = tmp_path / "pump_manual_p101.pdf"
    pdf.output(str(pdf_file_path))

    return pdf_file_path


@pytest.fixture()
def sample_pdf_content() -> dict[str, str]:
    """Return the expected content strings for validation in tests.

    These strings match key phrases that should appear in the
    extracted text from the sample PDF. Tests use these to verify
    that the parser correctly extracted the content.

    Returns:
        A dict with keys for each expected phrase category.
    """
    return {
        "equipment_name": "Pump P-101",
        "manufacturer": "AquaFlow Industries",
        "component": "SKF 6205",
        "symptom": "Excessive vibration",
        "location": "Production Unit 3",
        "operating_param": "3000 RPM",
        "troubleshooting": "bearing failure",
        "action": "Replace the mechanical seal",
    }
