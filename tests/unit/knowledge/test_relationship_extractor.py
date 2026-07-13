"""Tests for the relationship extractor.

Verifies that rule-based extraction creates the correct
relationship types between entities based on chunk content.

Bounded Context: Knowledge
Test Layer: Unit
"""

from __future__ import annotations

import pytest

from forgemind.knowledge.adapters.relationship_extractor import RelationshipExtractor
from forgemind.knowledge.domain.entities import KnowledgeEntity
from forgemind.knowledge.domain.value_objects import EntityType, RelationType

# ── Fixtures ─────────────────────────────────────────────────────


@pytest.fixture()
def extractor() -> RelationshipExtractor:
    """Fresh relationship extractor."""
    return RelationshipExtractor()


@pytest.fixture()
def pump() -> KnowledgeEntity:
    return KnowledgeEntity.create("Pump P-101", EntityType.ASSET)


@pytest.fixture()
def bearing() -> KnowledgeEntity:
    return KnowledgeEntity.create("Bearing", EntityType.COMPONENT)


@pytest.fixture()
def seal() -> KnowledgeEntity:
    return KnowledgeEntity.create("Mechanical Seal", EntityType.COMPONENT)


@pytest.fixture()
def vibration() -> KnowledgeEntity:
    return KnowledgeEntity.create("Excessive Vibration", EntityType.SYMPTOM)


@pytest.fixture()
def high_temp() -> KnowledgeEntity:
    return KnowledgeEntity.create("High Bearing Temperature", EntityType.SYMPTOM)


@pytest.fixture()
def replace_bearing() -> KnowledgeEntity:
    return KnowledgeEntity.create("Replace bearing", EntityType.ACTION)


# ══════════════════════════════════════════════════════════════════
# Rule 1: HAS_COMPONENT
# ══════════════════════════════════════════════════════════════════


class TestHasComponent:
    """Rule 1: Asset + component in same chunk → HAS_COMPONENT."""

    def test_asset_and_component_in_same_chunk(
        self,
        extractor: RelationshipExtractor,
        pump: KnowledgeEntity,
        bearing: KnowledgeEntity,
    ) -> None:
        chunks = ["Pump P-101 has a bearing housing with deep groove ball bearings."]
        entities = [pump, bearing]
        rels = extractor.extract(entities, chunks, "doc-1")

        has_comp = [r for r in rels if r.relation_type == RelationType.HAS_COMPONENT]
        assert len(has_comp) >= 1
        assert has_comp[0].source_entity_id == pump.id
        assert has_comp[0].target_entity_id == bearing.id

    def test_multiple_components_in_same_chunk(
        self,
        extractor: RelationshipExtractor,
        pump: KnowledgeEntity,
        bearing: KnowledgeEntity,
        seal: KnowledgeEntity,
    ) -> None:
        chunks = ["Pump P-101 includes the bearing and the mechanical seal assembly."]
        entities = [pump, bearing, seal]
        rels = extractor.extract(entities, chunks, "doc-1")

        has_comp = [r for r in rels if r.relation_type == RelationType.HAS_COMPONENT]
        target_ids = {r.target_entity_id for r in has_comp}
        assert bearing.id in target_ids
        assert seal.id in target_ids

    def test_no_component_no_relationship(
        self,
        extractor: RelationshipExtractor,
        pump: KnowledgeEntity,
    ) -> None:
        chunks = ["Pump P-101 is installed in Production Unit 3."]
        entities = [pump]
        rels = extractor.extract(entities, chunks, "doc-1")

        has_comp = [r for r in rels if r.relation_type == RelationType.HAS_COMPONENT]
        assert has_comp == []

    def test_asset_in_different_chunk_than_component(
        self,
        extractor: RelationshipExtractor,
        pump: KnowledgeEntity,
        bearing: KnowledgeEntity,
    ) -> None:
        """Document-level rule still connects asset to component."""
        chunks = [
            "Pump P-101 is a centrifugal pump.",
            "The bearing is a deep groove ball bearing.",
        ]
        entities = [pump, bearing]
        rels = extractor.extract(entities, chunks, "doc-1")

        # Document-level rule connects primary asset to all components
        has_comp = [r for r in rels if r.relation_type == RelationType.HAS_COMPONENT]
        assert len(has_comp) >= 1


# ══════════════════════════════════════════════════════════════════
# Rule 2: CAUSED_BY
# ══════════════════════════════════════════════════════════════════


class TestCausedBy:
    """Rule 2: Symptom + causation phrase + cause → CAUSED_BY."""

    def test_symptom_caused_by_component(
        self,
        extractor: RelationshipExtractor,
        vibration: KnowledgeEntity,
        bearing: KnowledgeEntity,
    ) -> None:
        chunks = ["Excessive vibration is caused by bearing failure or degradation."]
        entities = [vibration, bearing]
        rels = extractor.extract(entities, chunks, "doc-1")

        caused = [r for r in rels if r.relation_type == RelationType.CAUSED_BY]
        assert len(caused) >= 1
        assert caused[0].source_entity_id == vibration.id

    def test_due_to_phrase(
        self,
        extractor: RelationshipExtractor,
        high_temp: KnowledgeEntity,
        bearing: KnowledgeEntity,
    ) -> None:
        chunks = ["High bearing temperature due to insufficient lubrication and bearing overload."]
        entities = [high_temp, bearing]
        rels = extractor.extract(entities, chunks, "doc-1")

        caused = [r for r in rels if r.relation_type == RelationType.CAUSED_BY]
        assert len(caused) >= 1

    def test_no_causation_phrase_no_relationship(
        self,
        extractor: RelationshipExtractor,
        vibration: KnowledgeEntity,
        bearing: KnowledgeEntity,
    ) -> None:
        chunks = ["Check excessive vibration and bearing temperature daily."]
        entities = [vibration, bearing]
        rels = extractor.extract(entities, chunks, "doc-1")

        caused = [r for r in rels if r.relation_type == RelationType.CAUSED_BY]
        assert caused == []


# ══════════════════════════════════════════════════════════════════
# Rule 3: RESOLVES
# ══════════════════════════════════════════════════════════════════


class TestResolves:
    """Rule 3: Action + resolution phrase + symptom → RESOLVES."""

    def test_action_resolves_symptom(
        self,
        extractor: RelationshipExtractor,
        replace_bearing: KnowledgeEntity,
        vibration: KnowledgeEntity,
    ) -> None:
        chunks = ["Corrective Action: Replace bearing to resolve excessive vibration."]
        entities = [replace_bearing, vibration]
        rels = extractor.extract(entities, chunks, "doc-1")

        resolves = [r for r in rels if r.relation_type == RelationType.RESOLVES]
        assert len(resolves) >= 1
        assert resolves[0].source_entity_id == replace_bearing.id
        assert resolves[0].target_entity_id == vibration.id


# ══════════════════════════════════════════════════════════════════
# Rule 4: HAS_SYMPTOM
# ══════════════════════════════════════════════════════════════════


class TestHasSymptom:
    """Rule 4: Component + symptom in troubleshooting doc → HAS_SYMPTOM."""

    def test_component_and_symptom_in_same_chunk(
        self,
        extractor: RelationshipExtractor,
        bearing: KnowledgeEntity,
        vibration: KnowledgeEntity,
    ) -> None:
        chunks = [
            "Bearing shows excessive vibration above 4.5 mm/s.",
        ]
        entities = [bearing, vibration]
        rels = extractor.extract(entities, chunks, "doc-1")

        has_sym = [r for r in rels if r.relation_type == RelationType.HAS_SYMPTOM]
        assert len(has_sym) >= 1

    def test_no_co_occurrence_no_symptom_link(
        self,
        extractor: RelationshipExtractor,
        bearing: KnowledgeEntity,
        vibration: KnowledgeEntity,
    ) -> None:
        """Without co-occurrence in same chunk, chunk-level HAS_SYMPTOM is not created."""
        chunks = [
            "The bearing is a standard component.",
            "Excessive vibration is a concern.",
        ]
        entities = [bearing, vibration]
        rels = extractor.extract(entities, chunks, "doc-1")

        # No chunk-level HAS_SYMPTOM — entities are in separate chunks
        chunk_symptom = [
            r
            for r in rels
            if r.relation_type == RelationType.HAS_SYMPTOM
            and r.provenance is not None
            and "chunk" in r.provenance.extraction_method
        ]
        assert chunk_symptom == []


# ══════════════════════════════════════════════════════════════════
# Provenance
# ══════════════════════════════════════════════════════════════════


class TestRelationshipProvenance:
    """Verify every relationship carries correct provenance."""

    def test_provenance_has_document_id(
        self,
        extractor: RelationshipExtractor,
        pump: KnowledgeEntity,
        bearing: KnowledgeEntity,
    ) -> None:
        chunks = ["Pump P-101 includes a bearing assembly."]
        rels = extractor.extract([pump, bearing], chunks, "doc-42")
        for rel in rels:
            assert rel.provenance is not None
            assert rel.provenance.source_document_id == "doc-42"

    def test_provenance_has_extraction_rule(
        self,
        extractor: RelationshipExtractor,
        pump: KnowledgeEntity,
        bearing: KnowledgeEntity,
    ) -> None:
        chunks = ["Pump P-101 includes a bearing assembly."]
        rels = extractor.extract([pump, bearing], chunks, "doc-1")
        for rel in rels:
            assert rel.provenance is not None
            assert rel.provenance.extraction_method.startswith("rule:")


# ══════════════════════════════════════════════════════════════════
# Deduplication
# ══════════════════════════════════════════════════════════════════


class TestDeduplication:
    """Verify duplicate relationships are not created."""

    def test_same_pair_in_multiple_chunks_deduped(
        self,
        extractor: RelationshipExtractor,
        pump: KnowledgeEntity,
        bearing: KnowledgeEntity,
    ) -> None:
        chunks = [
            "Pump P-101 has a bearing.",
            "The Pump P-101 bearing is SKF type.",
        ]
        entities = [pump, bearing]
        rels = extractor.extract(entities, chunks, "doc-1")

        has_comp = [r for r in rels if r.relation_type == RelationType.HAS_COMPONENT]
        # Same source→target→type should appear only once
        assert len(has_comp) == 1


# ══════════════════════════════════════════════════════════════════
# Edge Cases
# ══════════════════════════════════════════════════════════════════


class TestEdgeCases:
    """Edge case handling."""

    def test_empty_entities_returns_empty(self, extractor: RelationshipExtractor) -> None:
        rels = extractor.extract([], ["Some text"], "doc-1")
        assert rels == []

    def test_empty_chunks_returns_empty(
        self, extractor: RelationshipExtractor, pump: KnowledgeEntity
    ) -> None:
        rels = extractor.extract([pump], [], "doc-1")
        assert rels == []
