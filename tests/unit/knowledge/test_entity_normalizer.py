"""Tests for the entity normalizer.

Verifies that raw analysis strings are correctly classified into
typed KnowledgeEntity objects with proper EntityType, Provenance,
and source reliability weighting.

Bounded Context: Knowledge
Test Layer: Unit
"""

from __future__ import annotations

import pytest

from forgemind.knowledge.adapters.analysis_service import DocumentInsights
from forgemind.knowledge.adapters.entity_normalizer import (
    SOURCE_RELIABILITY,
    EntityNormalizer,
)
from forgemind.knowledge.domain.value_objects import DocumentType, EntityType

# ── Fixtures ─────────────────────────────────────────────────────


@pytest.fixture()
def normalizer() -> EntityNormalizer:
    """Fresh entity normalizer."""
    return EntityNormalizer()


@pytest.fixture()
def sample_insights() -> DocumentInsights:
    """Sample analysis insights from a maintenance manual."""
    return DocumentInsights(
        equipment=["Pump P-101"],
        parts=["SKF 6205-2RS", "John Crane Type 2100"],
        materials=["AISI 4140", "Grade 25"],
        instruments=["PSV-101", "FS-101"],
        parameters=["3000 RPM", "80 degrees Celsius"],
        symptoms=[
            "Excessive Vibration",
            "High Bearing Temperature",
            "Seal Leakage",
        ],
        actions=[
            "Replace mechanical seal assembly.",
            "Check vibration levels with portable analyzer.",
            "Verify inlet and outlet pressure readings on local gauges.",
        ],
        key_sentences=["Pump P-101 is a single-stage centrifugal pump."],
        summary_stats={"total_words": 500},
    )


# ══════════════════════════════════════════════════════════════════
# Entity Type Classification
# ══════════════════════════════════════════════════════════════════


class TestEntityTypeClassification:
    """Verify that raw strings map to correct EntityType."""

    def test_equipment_becomes_asset(
        self, normalizer: EntityNormalizer, sample_insights: DocumentInsights
    ) -> None:
        entities = normalizer.normalize(sample_insights, "doc-1", "manual.pdf")
        assets = [e for e in entities if e.entity_type == EntityType.ASSET]
        assert len(assets) == 1
        assert assets[0].name == "Pump P-101"

    def test_parts_become_part_type(
        self, normalizer: EntityNormalizer, sample_insights: DocumentInsights
    ) -> None:
        entities = normalizer.normalize(sample_insights, "doc-1", "manual.pdf")
        parts = [e for e in entities if e.entity_type == EntityType.PART]
        part_names = {p.name for p in parts}
        assert "SKF 6205-2RS" in part_names
        assert "John Crane Type 2100" in part_names

    def test_materials_become_part_type(
        self, normalizer: EntityNormalizer, sample_insights: DocumentInsights
    ) -> None:
        entities = normalizer.normalize(sample_insights, "doc-1", "manual.pdf")
        parts = [e for e in entities if e.entity_type == EntityType.PART]
        part_names = {p.name for p in parts}
        assert "AISI 4140" in part_names
        assert "Grade 25" in part_names

    def test_symptoms_become_symptom_type(
        self, normalizer: EntityNormalizer, sample_insights: DocumentInsights
    ) -> None:
        entities = normalizer.normalize(sample_insights, "doc-1", "manual.pdf")
        symptoms = [e for e in entities if e.entity_type == EntityType.SYMPTOM]
        symptom_names = {s.name for s in symptoms}
        assert "Excessive Vibration" in symptom_names
        assert "High Bearing Temperature" in symptom_names
        assert "Seal Leakage" in symptom_names

    def test_actions_become_action_type(
        self, normalizer: EntityNormalizer, sample_insights: DocumentInsights
    ) -> None:
        entities = normalizer.normalize(sample_insights, "doc-1", "manual.pdf")
        actions = [e for e in entities if e.entity_type == EntityType.ACTION]
        assert len(actions) == 3


# ══════════════════════════════════════════════════════════════════
# Provenance and Traceability
# ══════════════════════════════════════════════════════════════════


class TestProvenance:
    """Verify that every entity carries correct provenance."""

    def test_provenance_has_document_id(
        self, normalizer: EntityNormalizer, sample_insights: DocumentInsights
    ) -> None:
        entities = normalizer.normalize(sample_insights, "doc-123", "manual.pdf")
        for entity in entities:
            assert entity.provenance is not None
            assert entity.provenance.source_document_id == "doc-123"

    def test_provenance_has_extraction_method(
        self, normalizer: EntityNormalizer, sample_insights: DocumentInsights
    ) -> None:
        entities = normalizer.normalize(sample_insights, "doc-1", "manual.pdf")
        for entity in entities:
            assert entity.provenance is not None
            assert entity.provenance.extraction_method == "pattern_based"

    def test_description_contains_document_title(
        self, normalizer: EntityNormalizer, sample_insights: DocumentInsights
    ) -> None:
        entities = normalizer.normalize(sample_insights, "doc-1", "pump_p101_manual.pdf")
        # ACTION entities use full sentence as description, others reference the doc title
        non_actions = [e for e in entities if e.entity_type != EntityType.ACTION]
        for entity in non_actions:
            assert "pump_p101_manual.pdf" in entity.description


# ══════════════════════════════════════════════════════════════════
# Source Reliability
# ══════════════════════════════════════════════════════════════════


class TestSourceReliability:
    """Verify confidence is weighted by source document type."""

    def test_manual_has_highest_reliability(self) -> None:
        assert SOURCE_RELIABILITY[DocumentType.MANUAL] == 1.0

    def test_incident_report_has_lower_reliability(self) -> None:
        assert SOURCE_RELIABILITY[DocumentType.INCIDENT_REPORT] < 1.0

    def test_unknown_has_lowest_reliability(self) -> None:
        assert SOURCE_RELIABILITY[DocumentType.UNKNOWN] < SOURCE_RELIABILITY[DocumentType.MANUAL]

    def test_manual_entities_have_higher_confidence(self, normalizer: EntityNormalizer) -> None:
        insights = DocumentInsights(equipment=["Pump P-101"])
        manual_entities = normalizer.normalize(
            insights, "doc-1", "manual.pdf", DocumentType.MANUAL
        )
        unknown_entities = normalizer.normalize(
            insights, "doc-2", "note.txt", DocumentType.UNKNOWN
        )

        assert manual_entities[0].provenance is not None
        assert unknown_entities[0].provenance is not None
        assert manual_entities[0].provenance.confidence > unknown_entities[0].provenance.confidence


# ══════════════════════════════════════════════════════════════════
# Deduplication
# ══════════════════════════════════════════════════════════════════


class TestDeduplication:
    """Verify entities are deduplicated within a single normalization batch."""

    def test_duplicate_names_produce_one_entity(self, normalizer: EntityNormalizer) -> None:
        insights = DocumentInsights(equipment=["Pump P-101", "pump p-101", "PUMP P-101"])
        entities = normalizer.normalize(insights, "doc-1", "manual.pdf")
        assets = [e for e in entities if e.entity_type == EntityType.ASSET]
        assert len(assets) == 1

    def test_short_names_are_filtered(self, normalizer: EntityNormalizer) -> None:
        insights = DocumentInsights(equipment=["P", "AB", "Pump P-101"])
        entities = normalizer.normalize(insights, "doc-1", "manual.pdf")
        assert len(entities) == 1


# ══════════════════════════════════════════════════════════════════
# Action Name Extraction
# ══════════════════════════════════════════════════════════════════


class TestActionNameExtraction:
    """Verify that long action sentences are shortened to graph labels."""

    def test_long_sentence_is_truncated_to_6_words(self, normalizer: EntityNormalizer) -> None:
        insights = DocumentInsights(
            actions=[
                "Verify all safety instrumentation including pressure relief valve and flow switch"
            ]
        )
        entities = normalizer.normalize(insights, "doc-1", "manual.pdf")
        action = entities[0]
        assert len(action.name.split()) <= 6

    def test_short_sentence_preserved(self, normalizer: EntityNormalizer) -> None:
        insights = DocumentInsights(actions=["Replace bearing"])
        entities = normalizer.normalize(insights, "doc-1", "manual.pdf")
        assert entities[0].name == "Replace bearing"

    def test_action_description_has_full_sentence(self, normalizer: EntityNormalizer) -> None:
        full_sentence = "Check vibration levels with portable analyzer."
        insights = DocumentInsights(actions=[full_sentence])
        entities = normalizer.normalize(insights, "doc-1", "manual.pdf")
        assert full_sentence in entities[0].description


# ══════════════════════════════════════════════════════════════════
# Edge Cases
# ══════════════════════════════════════════════════════════════════


class TestEdgeCases:
    """Edge case handling."""

    def test_empty_insights_returns_empty(self, normalizer: EntityNormalizer) -> None:
        insights = DocumentInsights()
        entities = normalizer.normalize(insights, "doc-1", "manual.pdf")
        assert entities == []

    def test_total_entity_count(
        self, normalizer: EntityNormalizer, sample_insights: DocumentInsights
    ) -> None:
        """Verify that all categories produce the expected total."""
        entities = normalizer.normalize(sample_insights, "doc-1", "manual.pdf")
        # 1 equipment + 2 parts + 2 materials + 3 symptoms + 3 actions
        # + 2 parameters (CONDITIONS) + 2 instruments (COMPONENTS)
        # + implicit components from key_sentences ("Pump P-101 is a single-stage centrifugal pump.")
        # Implicit components: none from this short sentence
        assert len(entities) >= 15
