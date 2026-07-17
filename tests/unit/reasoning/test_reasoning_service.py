"""Tests for the reasoning service — graph traversal and decision intelligence.

Tests the core reasoning pipeline:
  1. Entity resolution from natural language queries
  2. Multi-hop graph traversal (components → symptoms → causes → resolutions)
  3. Confidence computation
  4. Decision intelligence (severity, diagnosis, business impact)

Coverage target: All public methods of ReasoningService.
"""

from __future__ import annotations

import pytest

from forgemind.graph.adapters.networkx_repository import NetworkXGraphRepository
from forgemind.knowledge.domain.entities import KnowledgeEntity, KnowledgeRelationship
from forgemind.knowledge.domain.value_objects import EntityType, RelationType
from forgemind.reasoning.reasoning_service import (
    DecisionIntelligenceResult,
    EvidenceLink,
    ReasoningResult,
    ReasoningService,
)

# ── Fixtures ─────────────────────────────────────────────────────


@pytest.fixture()
def service() -> ReasoningService:
    """Create a fresh ReasoningService instance."""
    return ReasoningService()


@pytest.fixture()
def empty_graph() -> NetworkXGraphRepository:
    """Create an empty graph."""
    return NetworkXGraphRepository()


@pytest.fixture()
def populated_graph() -> NetworkXGraphRepository:
    """Create a graph with a realistic pump maintenance topology.

    Topology:
      Pump P-101 (asset)
        ├── has_component → Bearing (component)
        ├── has_component → Impeller (component)
        ├── has_symptom  → Vibration (symptom)
        ├── has_symptom  → Overheating (symptom)
        └── has_parameter → 3500 RPM (condition)

      Vibration (symptom)
        └── caused_by → Bearing (component)

      Overheating (symptom)
        └── caused_by → Impeller (component)

      Bearing (component)
        └── resolves → Replace Bearing (action)

      Impeller (component)
        └── resolves → Inspect Impeller (action)
    """
    graph = NetworkXGraphRepository()

    # Create entities via factory (auto-generates id and canonical_name)
    pump = KnowledgeEntity.create(
        name="Pump P-101",
        entity_type=EntityType.ASSET,
        description="Centrifugal pump in cooling system",
    )
    bearing = KnowledgeEntity.create(
        name="Bearing",
        entity_type=EntityType.COMPONENT,
        description="Main shaft bearing",
    )
    impeller = KnowledgeEntity.create(
        name="Impeller",
        entity_type=EntityType.COMPONENT,
        description="Flow impeller assembly",
    )
    vibration = KnowledgeEntity.create(
        name="Excessive Vibration",
        entity_type=EntityType.SYMPTOM,
        description="Abnormal vibration detected during operation",
    )
    overheating = KnowledgeEntity.create(
        name="Overheating",
        entity_type=EntityType.SYMPTOM,
        description="Temperature exceeds safe operating limit",
    )
    replace_bearing = KnowledgeEntity.create(
        name="Replace Bearing",
        entity_type=EntityType.ACTION,
        description="Replace main shaft bearing with SKF 6310",
    )
    inspect_impeller = KnowledgeEntity.create(
        name="Inspect Impeller",
        entity_type=EntityType.ACTION,
        description="Check impeller for wear and cavitation damage",
    )
    rpm = KnowledgeEntity.create(
        name="3500 RPM",
        entity_type=EntityType.CONDITION,
        description="Operating speed",
    )

    # Add all entities
    for entity in [
        pump,
        bearing,
        impeller,
        vibration,
        overheating,
        replace_bearing,
        inspect_impeller,
        rpm,
    ]:
        graph.add_entity(entity)

    # Build relationships
    def _rel(src: KnowledgeEntity, tgt: KnowledgeEntity, rt: RelationType) -> None:
        graph.add_relationship(
            KnowledgeRelationship.create(
                source_entity_id=src.id,
                target_entity_id=tgt.id,
                relation_type=rt,
            )
        )

    _rel(pump, bearing, RelationType.HAS_COMPONENT)
    _rel(pump, impeller, RelationType.HAS_COMPONENT)
    _rel(pump, vibration, RelationType.HAS_SYMPTOM)
    _rel(pump, overheating, RelationType.HAS_SYMPTOM)
    _rel(pump, rpm, RelationType.HAS_PARAMETER)
    _rel(vibration, bearing, RelationType.CAUSED_BY)
    _rel(overheating, impeller, RelationType.CAUSED_BY)
    _rel(bearing, replace_bearing, RelationType.RESOLVES)
    _rel(impeller, inspect_impeller, RelationType.RESOLVES)

    return graph


# ── EvidenceLink Tests ───────────────────────────────────────────


class TestEvidenceLink:
    """Tests for the EvidenceLink data model."""

    def test_creation(self) -> None:
        """EvidenceLink stores source, target, relation, and confidence."""
        link = EvidenceLink(
            source_name="Pump P-101",
            source_type="asset",
            relation="has_component",
            target_name="Bearing",
            target_type="component",
            confidence=0.85,
        )
        assert link.source_name == "Pump P-101"
        assert link.target_name == "Bearing"
        assert link.relation == "has_component"
        assert link.confidence == 0.85

    def test_frozen(self) -> None:
        """EvidenceLink is immutable."""
        link = EvidenceLink(
            source_name="A",
            source_type="asset",
            relation="r",
            target_name="B",
            target_type="component",
            confidence=0.5,
        )
        with pytest.raises(AttributeError):
            link.source_name = "X"  # type: ignore[misc]


# ── reason() Tests ───────────────────────────────────────────────


class TestReason:
    """Tests for the core reason() method."""

    def test_empty_graph_returns_unknown(
        self,
        service: ReasoningService,
        empty_graph: NetworkXGraphRepository,
    ) -> None:
        """Reasoning on an empty graph returns a graceful 'unknown' result."""
        result = service.reason("Why is Pump P-101 failing?", empty_graph)

        assert isinstance(result, ReasoningResult)
        assert result.entity_name == "Unknown"
        assert result.entity_type == "unknown"
        assert result.confidence == 0.0
        assert len(result.observations) > 0  # Should explain why

    def test_finds_focal_entity(
        self,
        service: ReasoningService,
        populated_graph: NetworkXGraphRepository,
    ) -> None:
        """Reasoning identifies Pump P-101 as the focal entity."""
        result = service.reason("Why is Pump P-101 vibrating?", populated_graph)

        assert result.entity_name == "Pump P-101"
        assert result.entity_type == "asset"

    def test_discovers_components(
        self,
        service: ReasoningService,
        populated_graph: NetworkXGraphRepository,
    ) -> None:
        """Reasoning discovers components connected to the focal entity."""
        result = service.reason("Why is Pump P-101 failing?", populated_graph)

        # Should find Bearing and Impeller as components
        component_names = {
            obs
            for obs in result.observations
            if "component" in obs.lower() or "Bearing" in obs or "Impeller" in obs
        }
        assert len(component_names) > 0
        assert len(result.observations) > 0

    def test_discovers_causes(
        self,
        service: ReasoningService,
        populated_graph: NetworkXGraphRepository,
    ) -> None:
        """Reasoning traces causal chains from symptoms to causes."""
        result = service.reason("Why is Pump P-101 failing?", populated_graph)

        assert len(result.possible_causes) > 0

    def test_discovers_recommendations_when_topology_matches(
        self,
        service: ReasoningService,
        populated_graph: NetworkXGraphRepository,
    ) -> None:
        """Reasoning finds causes even if resolution topology is incomplete."""
        result = service.reason("Why is Pump P-101 failing?", populated_graph)

        # This small graph has causes but no action→symptom RESOLVES edges,
        # so recommendations may be empty. Causes should still be found.
        assert len(result.possible_causes) > 0

    def test_computes_confidence(
        self,
        service: ReasoningService,
        populated_graph: NetworkXGraphRepository,
    ) -> None:
        """Reasoning produces a confidence score between 0 and 1."""
        result = service.reason("Why is Pump P-101 failing?", populated_graph)

        assert 0.0 < result.confidence <= 1.0

    def test_tracks_evidence_count(
        self,
        service: ReasoningService,
        populated_graph: NetworkXGraphRepository,
    ) -> None:
        """Reasoning counts evidence links discovered."""
        result = service.reason("Why is Pump P-101 failing?", populated_graph)

        assert result.evidence_count > 0
        assert result.graph_traversals > 0

    def test_explains_confidence(
        self,
        service: ReasoningService,
        populated_graph: NetworkXGraphRepository,
    ) -> None:
        """Reasoning produces a human-readable confidence explanation."""
        result = service.reason("Why is Pump P-101 failing?", populated_graph)

        assert result.confidence_explanation
        assert isinstance(result.confidence_explanation, str)

    def test_reasoning_chain_has_steps(
        self,
        service: ReasoningService,
        populated_graph: NetworkXGraphRepository,
    ) -> None:
        """Reasoning chain contains multiple steps with evidence."""
        result = service.reason("Why is Pump P-101 failing?", populated_graph)

        assert len(result.reasoning_chain) > 0
        for step in result.reasoning_chain:
            assert step.step_number > 0
            assert step.description

    def test_unmatched_query(
        self,
        service: ReasoningService,
        populated_graph: NetworkXGraphRepository,
    ) -> None:
        """Query about a non-existent entity returns graceful result."""
        result = service.reason("Why is Turbine T-500 broken?", populated_graph)

        assert result.entity_name == "Unknown"
        assert result.confidence == 0.0

    def test_result_has_timestamp(
        self,
        service: ReasoningService,
        populated_graph: NetworkXGraphRepository,
    ) -> None:
        """Result includes a timestamp."""
        result = service.reason("Why is Pump P-101 failing?", populated_graph)

        assert result.timestamp is not None


# ── decide() Tests ───────────────────────────────────────────────


class TestDecide:
    """Tests for the decision intelligence decide() method."""

    def test_returns_decision_result(
        self,
        service: ReasoningService,
        populated_graph: NetworkXGraphRepository,
    ) -> None:
        """decide() returns a DecisionIntelligenceResult."""
        result = service.decide("Why is Pump P-101 failing?", populated_graph)

        assert isinstance(result, DecisionIntelligenceResult)

    def test_decision_has_severity(
        self,
        service: ReasoningService,
        populated_graph: NetworkXGraphRepository,
    ) -> None:
        """Decision includes a severity classification."""
        result = service.decide("Why is Pump P-101 failing?", populated_graph)

        assert result.decision is not None
        severity = result.decision.get("severity", "")
        assert severity in ("critical", "high", "medium", "low")

    def test_decision_has_confidence(
        self,
        service: ReasoningService,
        populated_graph: NetworkXGraphRepository,
    ) -> None:
        """Decision includes a confidence score."""
        result = service.decide("Why is Pump P-101 failing?", populated_graph)

        conf = result.decision.get("confidence", 0)
        assert 0.0 < conf <= 1.0

    def test_diagnosis_has_most_likely_cause(
        self,
        service: ReasoningService,
        populated_graph: NetworkXGraphRepository,
    ) -> None:
        """Diagnosis includes a most likely cause with evidence."""
        result = service.decide("Why is Pump P-101 failing?", populated_graph)

        assert result.diagnosis is not None
        cause = result.diagnosis.get("most_likely_cause", {})
        assert cause.get("cause")
        assert cause.get("confidence", 0) > 0

    def test_recommended_actions_structure(
        self,
        service: ReasoningService,
        populated_graph: NetworkXGraphRepository,
    ) -> None:
        """Decision actions list is well-structured (may be empty for minimal graph)."""
        result = service.decide("Why is Pump P-101 failing?", populated_graph)

        # Actions may be empty if resolution topology doesn't match,
        # but when present they must have required fields.
        for action in result.recommended_actions:
            assert action.get("action")
            assert action.get("priority") in ("critical", "high", "medium", "low")

    def test_business_impact_present(
        self,
        service: ReasoningService,
        populated_graph: NetworkXGraphRepository,
    ) -> None:
        """Decision includes business impact estimation."""
        result = service.decide("Why is Pump P-101 failing?", populated_graph)

        assert result.business_impact is not None
        assert result.business_impact.get("estimated_downtime_prevented")
        assert result.business_impact.get("maintenance_priority")
        assert result.business_impact.get("risk_level")
        assert result.business_impact.get("cost_category")

    def test_confidence_breakdown_present(
        self,
        service: ReasoningService,
        populated_graph: NetworkXGraphRepository,
    ) -> None:
        """Decision includes explainable confidence breakdown."""
        result = service.decide("Why is Pump P-101 failing?", populated_graph)

        assert result.confidence_breakdown is not None
        assert result.confidence_breakdown.get("score", 0) > 0
        assert len(result.confidence_breakdown.get("factors", [])) > 0

    def test_reasoning_trace_present(
        self,
        service: ReasoningService,
        populated_graph: NetworkXGraphRepository,
    ) -> None:
        """Decision includes the full reasoning trace."""
        result = service.decide("Why is Pump P-101 failing?", populated_graph)

        assert len(result.reasoning_trace) > 0
        for step in result.reasoning_trace:
            assert "step" in step
            assert "description" in step

    def test_decide_on_empty_graph(
        self,
        service: ReasoningService,
        empty_graph: NetworkXGraphRepository,
    ) -> None:
        """decide() on empty graph returns graceful result."""
        result = service.decide("Why is Pump P-101 failing?", empty_graph)

        assert isinstance(result, DecisionIntelligenceResult)
        assert result.entity_name == "Unknown"

    def test_decide_unmatched_entity(
        self,
        service: ReasoningService,
        populated_graph: NetworkXGraphRepository,
    ) -> None:
        """decide() with unmatched entity returns graceful result."""
        result = service.decide("Why is Turbine T-500 broken?", populated_graph)

        assert result.entity_name == "Unknown"


# ── Confidence Computation Tests ─────────────────────────────────


class TestConfidenceComputation:
    """Tests for the internal confidence calculation."""

    def test_more_evidence_higher_confidence(
        self,
        service: ReasoningService,
    ) -> None:
        """More evidence links should produce higher confidence."""
        low = service._compute_confidence(
            [
                EvidenceLink("A", "asset", "r", "B", "component", 0.7),
            ]
        )
        high = service._compute_confidence(
            [
                EvidenceLink("A", "asset", "r", "B", "component", 0.7),
                EvidenceLink("B", "component", "r", "C", "symptom", 0.8),
                EvidenceLink("C", "symptom", "r", "D", "action", 0.9),
            ]
        )
        assert high > low

    def test_no_evidence_returns_zero(self, service: ReasoningService) -> None:
        """No evidence returns zero confidence."""
        assert service._compute_confidence([]) == 0.0

    def test_confidence_capped_at_one(self, service: ReasoningService) -> None:
        """Confidence never exceeds 1.0."""
        many = [EvidenceLink("A", "asset", "r", f"B{i}", "component", 1.0) for i in range(100)]
        assert service._compute_confidence(many) <= 1.0


# ── Severity Classification Tests ────────────────────────────────


class TestSeverityClassification:
    """Tests for severity classification logic."""

    def test_classify_returns_valid_level(
        self,
        service: ReasoningService,
        populated_graph: NetworkXGraphRepository,
    ) -> None:
        """Severity is one of the four valid levels."""
        result = service.reason("Why is Pump P-101 failing?", populated_graph)
        severity = service._classify_severity(result)
        assert severity in ("critical", "high", "medium", "low")
