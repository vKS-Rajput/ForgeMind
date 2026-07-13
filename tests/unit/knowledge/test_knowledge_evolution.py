"""Tests for the Knowledge Evolution Engine.

Verifies:
  - New entities are created with computed confidence
  - Existing entities get confidence increases
  - Relationships are created and strengthened
  - Every change produces a KnowledgeEvent
  - Confidence is computed from evidence (not stored statically)

Bounded Context: Knowledge
Test Layer: Unit
"""

from __future__ import annotations

import pytest

from forgemind.graph.adapters.networkx_repository import NetworkXGraphRepository
from forgemind.knowledge.adapters.knowledge_evolution import (
    KnowledgeEvolutionEngine,
    compute_confidence,
)
from forgemind.knowledge.domain.entities import (
    KnowledgeEntity,
    KnowledgeRelationship,
)
from forgemind.knowledge.domain.knowledge_event import KnowledgeEventType
from forgemind.knowledge.domain.value_objects import EntityType, RelationType

# ── Fixtures ─────────────────────────────────────────────────────


@pytest.fixture()
def graph() -> NetworkXGraphRepository:
    """Fresh empty graph."""
    return NetworkXGraphRepository()


@pytest.fixture()
def engine() -> KnowledgeEvolutionEngine:
    """Fresh evolution engine."""
    return KnowledgeEvolutionEngine()


@pytest.fixture()
def pump() -> KnowledgeEntity:
    return KnowledgeEntity.create("Pump P-101", EntityType.ASSET)


@pytest.fixture()
def bearing() -> KnowledgeEntity:
    return KnowledgeEntity.create("Bearing", EntityType.COMPONENT)


@pytest.fixture()
def vibration() -> KnowledgeEntity:
    return KnowledgeEntity.create("Excessive Vibration", EntityType.SYMPTOM)


# ══════════════════════════════════════════════════════════════════
# Confidence Computation
# ══════════════════════════════════════════════════════════════════


class TestComputeConfidence:
    """Verify the computed confidence formula."""

    def test_empty_evidence_returns_zero(self) -> None:
        assert compute_confidence([]) == 0.0

    def test_single_manual_gives_moderate_confidence(self) -> None:
        # 1.0 / 3.0 ≈ 0.33
        result = compute_confidence([1.0])
        assert 0.3 <= result <= 0.4

    def test_two_sources_give_higher_confidence(self) -> None:
        # (1.0 + 0.85) / 3.0 ≈ 0.62
        result = compute_confidence([1.0, 0.85])
        assert 0.5 <= result <= 0.7

    def test_three_sources_give_high_confidence(self) -> None:
        # (1.0 + 0.85 + 0.9) / 3.0 ≈ 0.92
        result = compute_confidence([1.0, 0.85, 0.9])
        assert 0.85 <= result <= 1.0

    def test_never_exceeds_one(self) -> None:
        result = compute_confidence([1.0, 1.0, 1.0, 1.0, 1.0])
        assert result <= 1.0

    def test_more_evidence_increases_confidence(self) -> None:
        c1 = compute_confidence([0.7])
        c2 = compute_confidence([0.7, 0.7])
        c3 = compute_confidence([0.7, 0.7, 0.7])
        assert c1 < c2 < c3


# ══════════════════════════════════════════════════════════════════
# Entity Creation
# ══════════════════════════════════════════════════════════════════


class TestEntityCreation:
    """Verify new entities are correctly added to the graph."""

    def test_new_entity_is_added(
        self,
        engine: KnowledgeEvolutionEngine,
        graph: NetworkXGraphRepository,
        pump: KnowledgeEntity,
    ) -> None:
        result = engine.merge([pump], [], graph, "doc-1", "manual.pdf")
        assert result.entities_created == 1
        assert graph.get_entity_count() == 1

    def test_new_entity_gets_evidence_count(
        self,
        engine: KnowledgeEvolutionEngine,
        graph: NetworkXGraphRepository,
        pump: KnowledgeEntity,
    ) -> None:
        engine.merge([pump], [], graph, "doc-1", "manual.pdf")
        stored = graph.get_entity(pump.id)
        assert stored is not None
        assert stored.attributes["evidence_count"] == "1"

    def test_creation_produces_event(
        self,
        engine: KnowledgeEvolutionEngine,
        graph: NetworkXGraphRepository,
        pump: KnowledgeEntity,
    ) -> None:
        result = engine.merge([pump], [], graph, "doc-1", "manual.pdf")
        created_events = [
            e for e in result.events if e.event_type == KnowledgeEventType.ENTITY_CREATED
        ]
        assert len(created_events) == 1
        assert created_events[0].entity_name == "Pump P-101"
        assert created_events[0].evidence_count == 1


# ══════════════════════════════════════════════════════════════════
# Confidence Evolution
# ══════════════════════════════════════════════════════════════════


class TestConfidenceEvolution:
    """Verify confidence increases with more evidence."""

    def test_second_document_increases_confidence(
        self,
        engine: KnowledgeEvolutionEngine,
        graph: NetworkXGraphRepository,
    ) -> None:
        pump1 = KnowledgeEntity.create("Pump P-101", EntityType.ASSET)
        pump2 = KnowledgeEntity.create("pump p-101", EntityType.ASSET)

        # First document
        engine.merge([pump1], [], graph, "doc-1", "manual.pdf", 1.0)
        # Second document with same entity
        result2 = engine.merge([pump2], [], graph, "doc-2", "incident.pdf", 0.85)

        assert result2.entities_updated == 1
        assert result2.entities_created == 0

        # Check confidence increased event
        conf_events = [
            e for e in result2.events if e.event_type == KnowledgeEventType.CONFIDENCE_INCREASED
        ]
        assert len(conf_events) == 1
        assert conf_events[0].old_confidence is not None
        assert conf_events[0].new_confidence > conf_events[0].old_confidence

    def test_three_documents_give_high_confidence(
        self,
        engine: KnowledgeEvolutionEngine,
        graph: NetworkXGraphRepository,
    ) -> None:
        pump1 = KnowledgeEntity.create("Pump P-101", EntityType.ASSET)
        pump2 = KnowledgeEntity.create("Pump P-101", EntityType.ASSET)
        pump3 = KnowledgeEntity.create("Pump P-101", EntityType.ASSET)

        engine.merge([pump1], [], graph, "doc-1", "manual.pdf", 1.0)
        engine.merge([pump2], [], graph, "doc-2", "incident.pdf", 0.85)
        result3 = engine.merge([pump3], [], graph, "doc-3", "inspection.pdf", 0.9)

        conf_events = [
            e for e in result3.events if e.event_type == KnowledgeEventType.CONFIDENCE_INCREASED
        ]
        assert conf_events[0].new_confidence > 0.85

    def test_evidence_count_tracks_documents(
        self,
        engine: KnowledgeEvolutionEngine,
        graph: NetworkXGraphRepository,
    ) -> None:
        pump1 = KnowledgeEntity.create("Pump P-101", EntityType.ASSET)
        pump2 = KnowledgeEntity.create("Pump P-101", EntityType.ASSET)

        engine.merge([pump1], [], graph, "doc-1", "manual.pdf")
        engine.merge([pump2], [], graph, "doc-2", "incident.pdf")

        assert engine.get_evidence_count("pump_p_101", EntityType.ASSET) == 2


# ══════════════════════════════════════════════════════════════════
# Relationship Merging
# ══════════════════════════════════════════════════════════════════


class TestRelationshipMerging:
    """Verify relationships are correctly merged."""

    def test_new_relationship_is_created(
        self,
        engine: KnowledgeEvolutionEngine,
        graph: NetworkXGraphRepository,
        pump: KnowledgeEntity,
        bearing: KnowledgeEntity,
    ) -> None:
        rel = KnowledgeRelationship.create(
            pump.id,
            bearing.id,
            RelationType.HAS_COMPONENT,
        )
        result = engine.merge([pump, bearing], [rel], graph, "doc-1", "manual.pdf")

        assert result.relationships_created == 1
        assert graph.get_relationship_count() == 1

    def test_relationship_creation_produces_event(
        self,
        engine: KnowledgeEvolutionEngine,
        graph: NetworkXGraphRepository,
        pump: KnowledgeEntity,
        bearing: KnowledgeEntity,
    ) -> None:
        rel = KnowledgeRelationship.create(
            pump.id,
            bearing.id,
            RelationType.HAS_COMPONENT,
        )
        result = engine.merge([pump, bearing], [rel], graph, "doc-1", "manual.pdf")

        rel_events = [
            e for e in result.events if e.event_type == KnowledgeEventType.RELATIONSHIP_CREATED
        ]
        assert len(rel_events) == 1
        assert "has_component" in rel_events[0].entity_name

    def test_duplicate_relationship_is_strengthened(
        self,
        engine: KnowledgeEvolutionEngine,
        graph: NetworkXGraphRepository,
    ) -> None:
        pump1 = KnowledgeEntity.create("Pump P-101", EntityType.ASSET)
        bearing1 = KnowledgeEntity.create("Bearing", EntityType.COMPONENT)
        rel1 = KnowledgeRelationship.create(
            pump1.id,
            bearing1.id,
            RelationType.HAS_COMPONENT,
        )

        pump2 = KnowledgeEntity.create("Pump P-101", EntityType.ASSET)
        bearing2 = KnowledgeEntity.create("Bearing", EntityType.COMPONENT)
        rel2 = KnowledgeRelationship.create(
            pump2.id,
            bearing2.id,
            RelationType.HAS_COMPONENT,
        )

        engine.merge([pump1, bearing1], [rel1], graph, "doc-1", "manual.pdf")
        result2 = engine.merge([pump2, bearing2], [rel2], graph, "doc-2", "incident.pdf")

        assert result2.relationships_strengthened == 1
        # Graph should still have only 1 edge
        assert graph.get_relationship_count() == 1


# ══════════════════════════════════════════════════════════════════
# Full Pipeline Integration
# ══════════════════════════════════════════════════════════════════


class TestFullPipeline:
    """Test the complete merge pipeline."""

    def test_merge_multiple_entities_and_relationships(
        self,
        engine: KnowledgeEvolutionEngine,
        graph: NetworkXGraphRepository,
    ) -> None:
        pump = KnowledgeEntity.create("Pump P-101", EntityType.ASSET)
        bearing = KnowledgeEntity.create("Bearing", EntityType.COMPONENT)
        vibration = KnowledgeEntity.create("Excessive Vibration", EntityType.SYMPTOM)

        rel1 = KnowledgeRelationship.create(
            pump.id,
            bearing.id,
            RelationType.HAS_COMPONENT,
        )
        rel2 = KnowledgeRelationship.create(
            bearing.id,
            vibration.id,
            RelationType.HAS_SYMPTOM,
        )

        result = engine.merge(
            [pump, bearing, vibration],
            [rel1, rel2],
            graph,
            "doc-1",
            "manual.pdf",
        )

        assert result.entities_created == 3
        assert result.relationships_created == 2
        assert graph.get_entity_count() == 3
        assert graph.get_relationship_count() == 2
        assert len(result.events) == 5  # 3 entity + 2 relationship events

    def test_empty_merge_produces_empty_result(
        self,
        engine: KnowledgeEvolutionEngine,
        graph: NetworkXGraphRepository,
    ) -> None:
        result = engine.merge([], [], graph, "doc-1", "empty.pdf")
        assert result.entities_created == 0
        assert result.events == []
