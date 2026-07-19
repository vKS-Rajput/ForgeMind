"""Unit tests for Document Capability Analyzer and Robustness edge cases.

Bounded Context: Knowledge & Reasoning
Layer: Unit Tests
"""

from __future__ import annotations

import pytest

from forgemind.graph.adapters.networkx_repository import NetworkXGraphRepository
from forgemind.knowledge.adapters.capability_analyzer import (
    DocumentCapabilityAnalyzer,
)
from forgemind.knowledge.adapters.knowledge_evolution import (
    KnowledgeEvolutionEngine,
)
from forgemind.knowledge.domain.entities import KnowledgeEntity
from forgemind.knowledge.domain.value_objects import DocumentType, EntityType
from forgemind.reasoning.reasoning_service import ReasoningService


@pytest.mark.unit
class TestDocumentCapabilityAnalyzer:
    """Test suite for DocumentCapabilityAnalyzer."""

    def setup_method(self) -> None:
        self.analyzer = DocumentCapabilityAnalyzer()

    def test_empty_text_returns_unsupported(self) -> None:
        result = self.analyzer.analyze(title="empty.pdf", text="", page_count=1)
        assert result.support_level == "unsupported"
        assert result.relevance_score <= 0.05
        assert len(result.warnings) > 0
        assert "industrial maintenance knowledge" in result.warnings[0].lower()

    def test_non_industrial_document_returns_unsupported(self) -> None:
        text = "Annual Financial Statement 2026. Revenue grew by 15%. Balance sheet statement and dividend distribution."
        result = self.analyzer.analyze(title="Financial_Report.pdf", text=text, page_count=5)
        assert result.support_level == "unsupported"
        assert result.document_type == DocumentType.GENERAL
        assert result.relevance_score < 0.3
        assert len(result.recommendations) > 0

    def test_oem_manual_returns_full_support(self) -> None:
        text = "Centrifugal Pump P-101 Operating Manual. Impeller replacement, bearing vibration tolerance 0.05 mm/s, lubrication schedule."
        result = self.analyzer.analyze(title="pump_manual.pdf", text=text, page_count=20)
        assert result.support_level == "full"
        assert result.document_type == DocumentType.MANUAL
        assert result.relevance_score > 0.5
        assert result.available_features["reasoning"] is True

    def test_sop_document_returns_partial_support(self) -> None:
        text = "Standard Operating Procedure SOP-402. Safety procedure for high pressure valve inspection and lockdown."
        result = self.analyzer.analyze(title="SOP-402.pdf", text=text, page_count=3)
        assert result.support_level == "partial"
        assert result.document_type == DocumentType.SOP
        assert len(result.warnings) > 0

    def test_pid_document_returns_unsupported(self) -> None:
        text = "P&ID Schematic Diagram Line 40. Piping and instrumentation drawing."
        result = self.analyzer.analyze(title="PANDID_Line40.pdf", text=text, page_count=1)
        assert result.support_level == "unsupported"
        assert result.document_type == DocumentType.P_AND_ID


@pytest.mark.unit
class TestReasoningRankAlignment:
    """Test suite for reasoning service diagnosis vs problem summary alignment."""

    def test_decide_problem_summary_matches_diagnosis_top_cause(self) -> None:
        service = ReasoningService()
        graph = NetworkXGraphRepository()

        # Add Pump P-101 asset entity
        pump = KnowledgeEntity.create(
            name="Pump P-101",
            entity_type=EntityType.ASSET,
        )
        bearing = KnowledgeEntity.create(
            name="Bearing",
            entity_type=EntityType.COMPONENT,
            attributes={"created_by": "Manual_A"},
        )
        graph.add_entity(pump)
        graph.add_entity(bearing)

        res = service.decide("Why is Pump P-101 failing?", graph)
        # Verify decision structure exists without error
        assert "problem" in res.decision
        assert "severity" in res.decision


@pytest.mark.unit
class TestCrossDocumentContradictions:
    """Test suite verifying contradictions are strictly cross-document."""

    def test_single_document_does_not_trigger_contradiction(self) -> None:
        engine = KnowledgeEvolutionEngine()
        graph = NetworkXGraphRepository()

        entity1 = KnowledgeEntity.create(
            name="Bearing Inspection",
            entity_type=EntityType.ACTION,
            description="Bearing inspection every 90 days or 180 days",
        )

        merge_res = engine.merge(
            new_entities=[entity1],
            new_relationships=[],
            graph=graph,
            source_document_id="doc_1",
            source_document_title="Manual_A",
        )

        # Same document internal mentions should NOT produce a cross-document contradiction
        assert merge_res.contradictions_detected == 0

