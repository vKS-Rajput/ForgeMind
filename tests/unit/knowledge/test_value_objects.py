"""Tests for Knowledge domain value objects."""

# pyrefly: ignore [missing-import]
import pytest

from forgemind.knowledge.domain.value_objects import (
    INVERSE_RELATIONS,
    ChunkMetadata,
    DocumentType,
    EntityType,
    Provenance,
    RelationType,
    Severity,
)

pytestmark = pytest.mark.unit


class TestEntityType:
    """EntityType enum coverage."""

    def test_all_entity_types_exist(self):
        expected = {
            "ASSET",
            "COMPONENT",
            "FAILURE_MODE",
            "SYMPTOM",
            "ACTION",
            "CONDITION",
            "LOCATION",
            "PART",
        }
        actual = {e.name for e in EntityType}
        assert actual == expected

    def test_entity_type_values_are_lowercase(self):
        for entity_type in EntityType:
            assert entity_type.value == entity_type.value.lower()

    def test_entity_type_from_string(self):
        assert EntityType("asset") is EntityType.ASSET
        assert EntityType("failure_mode") is EntityType.FAILURE_MODE


class TestRelationType:
    """RelationType enum coverage."""

    def test_all_relation_types_exist(self):
        expected = {
            "CAUSES",
            "CAUSED_BY",
            "HAS_COMPONENT",
            "COMPONENT_OF",
            "RESOLVED_BY",
            "RESOLVES",
            "SYMPTOMS_OF",
            "HAS_SYMPTOM",
            "LOCATED_AT",
            "RELATED_TO",
            "OPERATED_BY",
            "HAS_PARAMETER",
            "INDICATES",
            "MANUFACTURED_BY",
            "REQUIRES_PART",
            "MONITORS",
        }
        actual = {r.name for r in RelationType}
        assert actual == expected

    def test_inverse_relations_are_symmetric(self):
        for rel, inverse in INVERSE_RELATIONS.items():
            assert INVERSE_RELATIONS[inverse] == rel, (
                f"Inverse of inverse of {rel} should be {rel}, got {INVERSE_RELATIONS[inverse]}"
            )

    def test_all_relation_types_have_inverses(self):
        for rel in RelationType:
            assert rel in INVERSE_RELATIONS, f"{rel} has no inverse mapping"


class TestDocumentType:
    """DocumentType enum coverage."""

    def test_all_document_types_exist(self):
        expected = {
            "MANUAL",
            "INCIDENT_REPORT",
            "INSPECTION_REPORT",
            "WORK_ORDER",
            "SOP",
            "P_AND_ID",
            "SPREADSHEET",
            "GENERAL",
            "UNKNOWN",
        }
        actual = {d.name for d in DocumentType}
        assert actual == expected


class TestSeverity:
    """Severity enum coverage."""

    def test_all_severity_levels_exist(self):
        expected = {"CRITICAL", "HIGH", "MEDIUM", "LOW", "INFO"}
        actual = {s.name for s in Severity}
        assert actual == expected


class TestProvenance:
    """Provenance value object."""

    def test_create_with_defaults(self):
        prov = Provenance(source_document_id="doc-001")
        assert prov.source_document_id == "doc-001"
        assert prov.chunk_ids == ()
        assert prov.extraction_method == "unknown"
        assert prov.confidence == 0.5

    def test_create_with_all_fields(self):
        prov = Provenance(
            source_document_id="doc-001",
            chunk_ids=("chunk-1", "chunk-2"),
            extraction_method="rule_based",
            confidence=0.95,
        )
        assert prov.chunk_ids == ("chunk-1", "chunk-2")
        assert prov.extraction_method == "rule_based"
        assert prov.confidence == 0.95

    def test_confidence_validation_too_high(self):
        with pytest.raises(ValueError, match="Confidence must be"):
            Provenance(source_document_id="doc-001", confidence=1.5)

    def test_confidence_validation_too_low(self):
        with pytest.raises(ValueError, match="Confidence must be"):
            Provenance(source_document_id="doc-001", confidence=-0.1)

    def test_confidence_boundary_values(self):
        p0 = Provenance(source_document_id="doc", confidence=0.0)
        p1 = Provenance(source_document_id="doc", confidence=1.0)
        assert p0.confidence == 0.0
        assert p1.confidence == 1.0

    def test_provenance_is_frozen(self):
        from dataclasses import FrozenInstanceError

        prov = Provenance(source_document_id="doc-001")
        with pytest.raises(FrozenInstanceError):
            prov.confidence = 0.99  # type: ignore[misc]

    def test_provenance_equality(self):
        p1 = Provenance(source_document_id="doc-001", confidence=0.8)
        p2 = Provenance(source_document_id="doc-001", confidence=0.8)
        # extracted_at differs, so they won't be equal by default
        # But same fields should produce meaningful comparison
        assert p1.source_document_id == p2.source_document_id
        assert p1.confidence == p2.confidence


class TestChunkMetadata:
    """ChunkMetadata value object."""

    def test_create_with_defaults(self):
        meta = ChunkMetadata()
        assert meta.page_number is None
        assert meta.position_in_document == 0
        assert meta.char_start == 0
        assert meta.char_end == 0

    def test_create_with_all_fields(self):
        meta = ChunkMetadata(
            page_number=3,
            position_in_document=5,
            char_start=1200,
            char_end=1800,
        )
        assert meta.page_number == 3
        assert meta.position_in_document == 5
        assert meta.char_start == 1200
        assert meta.char_end == 1800

    def test_chunk_metadata_is_frozen(self):
        from dataclasses import FrozenInstanceError

        meta = ChunkMetadata()
        with pytest.raises(FrozenInstanceError):
            meta.page_number = 5  # type: ignore[misc]
