"""Tests for Knowledge domain services."""

# pyrefly: ignore [missing-import]
import pytest

from forgemind.knowledge.domain.entities import KnowledgeEntity
from forgemind.knowledge.domain.services import (
    chunk_text,
    merge_entities,
    normalize_entity_name,
    validate_relationship,
)
from forgemind.knowledge.domain.value_objects import (
    EntityType,
    Provenance,
    RelationType,
)

pytestmark = pytest.mark.unit


class TestChunkText:
    """Text chunking with sentence boundaries and overlap."""

    def test_single_sentence(self):
        result = chunk_text("Hello world.", max_chunk_size=500)
        assert result == ["Hello world."]

    def test_short_text_returns_single_chunk(self):
        text = "First sentence. Second sentence. Third sentence."
        result = chunk_text(text, max_chunk_size=500)
        assert len(result) == 1
        assert result[0] == text

    def test_splits_at_sentence_boundaries(self):
        text = (
            "Pump P-101 is a centrifugal pump. "
            "It operates at 3000 RPM. "
            "The bearing temperature should not exceed 80°C. "
            "Regular maintenance is required every 6 months."
        )
        result = chunk_text(text, max_chunk_size=80, overlap_size=0)
        assert len(result) > 1
        # Each chunk should end at a sentence boundary
        for chunk in result:
            assert chunk.rstrip().endswith((".", "°C."))

    def test_overlap_between_chunks(self):
        text = (
            "First sentence here. Second sentence here. Third sentence here. Fourth sentence here."
        )
        result = chunk_text(text, max_chunk_size=50, overlap_size=25)
        assert len(result) >= 2

    def test_empty_text_raises(self):
        with pytest.raises(ValueError, match="must not be empty"):
            chunk_text("")

    def test_whitespace_text_raises(self):
        with pytest.raises(ValueError, match="must not be empty"):
            chunk_text("   ")

    def test_invalid_max_chunk_size_raises(self):
        with pytest.raises(ValueError, match="max_chunk_size must be > 0"):
            chunk_text("Hello.", max_chunk_size=0)

    def test_negative_overlap_raises(self):
        with pytest.raises(ValueError, match="overlap_size must be >= 0"):
            chunk_text("Hello.", overlap_size=-1)

    def test_overlap_exceeds_chunk_size_raises(self):
        with pytest.raises(ValueError, match="overlap_size.*must be < max_chunk_size"):
            chunk_text("Hello.", max_chunk_size=100, overlap_size=100)

    def test_zero_overlap(self):
        text = "First. Second. Third. Fourth."
        result = chunk_text(text, max_chunk_size=20, overlap_size=0)
        assert len(result) >= 2

    def test_no_content_lost(self):
        """All sentences from the original text appear in at least one chunk."""
        text = (
            "Pump P-101 experienced vibration. "
            "Bearing temperature reached 95 degrees. "
            "Operator initiated shutdown. "
            "Maintenance team was called."
        )
        result = chunk_text(text, max_chunk_size=80, overlap_size=0)
        combined = " ".join(result)
        assert "Pump P-101" in combined
        assert "Bearing temperature" in combined
        assert "Operator initiated" in combined
        assert "Maintenance team" in combined


class TestNormalizeEntityName:
    """Entity name normalization."""

    def test_basic_normalization(self):
        assert normalize_entity_name("Pump P-101") == "pump_p_101"

    def test_whitespace_handling(self):
        assert normalize_entity_name("  bearing FAILURE  ") == "bearing_failure"

    def test_special_characters(self):
        assert normalize_entity_name("SKF-6205 Bearing") == "skf_6205_bearing"

    def test_multiple_spaces(self):
        assert normalize_entity_name("heat   exchanger") == "heat_exchanger"

    def test_mixed_punctuation(self):
        assert normalize_entity_name("O-ring (seal)") == "o_ring_seal"

    def test_already_normalized(self):
        assert normalize_entity_name("pump_p_101") == "pump_p_101"

    def test_empty_name_raises(self):
        with pytest.raises(ValueError, match="must not be empty"):
            normalize_entity_name("")

    def test_whitespace_name_raises(self):
        with pytest.raises(ValueError, match="must not be empty"):
            normalize_entity_name("   ")

    def test_special_chars_only_raises(self):
        with pytest.raises(ValueError, match="normalizes to empty"):
            normalize_entity_name("---")


class TestMergeEntities:
    """Entity deduplication by canonical name and type."""

    def test_no_duplicates(self):
        entities = [
            KnowledgeEntity.create(name="Pump P-101", entity_type=EntityType.ASSET),
            KnowledgeEntity.create(name="Bearing", entity_type=EntityType.COMPONENT),
        ]
        result = merge_entities(entities)
        assert len(result) == 2

    def test_exact_duplicates_keeps_first(self):
        entities = [
            KnowledgeEntity.create(name="Pump P-101", entity_type=EntityType.ASSET),
            KnowledgeEntity.create(name="Pump P-101", entity_type=EntityType.ASSET),
        ]
        result = merge_entities(entities)
        assert len(result) == 1
        assert result[0].name == "Pump P-101"

    def test_name_variant_duplicates(self):
        """Different surface forms that normalize to the same canonical name."""
        entities = [
            KnowledgeEntity.create(name="Pump P-101", entity_type=EntityType.ASSET),
            KnowledgeEntity.create(name="pump p 101", entity_type=EntityType.ASSET),
            KnowledgeEntity.create(name="PUMP-P-101", entity_type=EntityType.ASSET),
        ]
        result = merge_entities(entities)
        assert len(result) == 1

    def test_same_name_different_types_are_distinct(self):
        """Same name but different entity types should not merge."""
        entities = [
            KnowledgeEntity.create(name="Bearing", entity_type=EntityType.COMPONENT),
            KnowledgeEntity.create(name="Bearing", entity_type=EntityType.PART),
        ]
        result = merge_entities(entities)
        assert len(result) == 2

    def test_keeps_highest_confidence(self):
        low = KnowledgeEntity.create(
            name="Pump P-101",
            entity_type=EntityType.ASSET,
            provenance=Provenance(source_document_id="doc-1", confidence=0.5),
        )
        high = KnowledgeEntity.create(
            name="pump p-101",
            entity_type=EntityType.ASSET,
            provenance=Provenance(source_document_id="doc-2", confidence=0.95),
        )
        result = merge_entities([low, high])
        assert len(result) == 1
        assert result[0].provenance is not None
        assert result[0].provenance.confidence == 0.95

    def test_empty_list(self):
        assert merge_entities([]) == []

    def test_single_entity(self):
        entities = [KnowledgeEntity.create(name="X", entity_type=EntityType.ASSET)]
        result = merge_entities(entities)
        assert len(result) == 1


class TestValidateRelationship:
    """Relationship validation against typed schema."""

    def test_valid_asset_has_component(self):
        assert (
            validate_relationship(
                EntityType.ASSET, RelationType.HAS_COMPONENT, EntityType.COMPONENT
            )
            is True
        )

    def test_valid_failure_causes_symptom(self):
        assert (
            validate_relationship(EntityType.FAILURE_MODE, RelationType.CAUSES, EntityType.SYMPTOM)
            is True
        )

    def test_valid_action_resolves_failure(self):
        assert (
            validate_relationship(
                EntityType.ACTION, RelationType.RESOLVES, EntityType.FAILURE_MODE
            )
            is True
        )

    def test_invalid_in_strict_mode(self):
        # Asset CAUSES Component is not in the valid patterns
        assert (
            validate_relationship(
                EntityType.ASSET,
                RelationType.CAUSES,
                EntityType.COMPONENT,
                strict=True,
            )
            is False
        )

    def test_related_to_always_valid_in_non_strict(self):
        assert (
            validate_relationship(
                EntityType.ASSET,
                RelationType.RELATED_TO,
                EntityType.SYMPTOM,
                strict=False,
            )
            is True
        )

    def test_related_to_invalid_if_not_in_patterns_strict(self):
        # ASSET RELATED_TO SYMPTOM is not in explicit patterns
        assert (
            validate_relationship(
                EntityType.ASSET,
                RelationType.RELATED_TO,
                EntityType.SYMPTOM,
                strict=True,
            )
            is False
        )

    def test_related_to_valid_if_in_patterns_strict(self):
        # ASSET RELATED_TO ASSET IS in explicit patterns
        assert (
            validate_relationship(
                EntityType.ASSET,
                RelationType.RELATED_TO,
                EntityType.ASSET,
                strict=True,
            )
            is True
        )
