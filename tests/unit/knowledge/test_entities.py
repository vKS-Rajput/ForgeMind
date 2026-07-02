"""Tests for Knowledge domain entities."""

from dataclasses import FrozenInstanceError

# pyrefly: ignore [missing-import]
import pytest

from forgemind.knowledge.domain.entities import (
    Chunk,
    Document,
    KnowledgeEntity,
    KnowledgeRelationship,
)
from forgemind.knowledge.domain.value_objects import (
    ChunkMetadata,
    DocumentType,
    EntityType,
    Provenance,
    RelationType,
)
from forgemind.shared.types import DocumentId, EntityId

pytestmark = pytest.mark.unit


class TestDocument:
    """Document entity construction and validation."""

    def test_create_with_minimal_args(self):
        doc = Document.create(
            title="Pump Manual",
            source_path="/data/pump.pdf",
            content="Some content",
        )
        assert doc.title == "Pump Manual"
        assert doc.source_path == "/data/pump.pdf"
        assert doc.document_type is DocumentType.UNKNOWN
        assert doc.page_count == 0
        assert len(doc.id) > 0
        assert len(doc.content_hash) == 64  # SHA-256 hex

    def test_create_with_all_args(self):
        doc = Document.create(
            title="Compressor Manual",
            source_path="/data/comp.pdf",
            content="Content here",
            document_type=DocumentType.MANUAL,
            page_count=42,
            metadata={"author": "John"},
        )
        assert doc.document_type is DocumentType.MANUAL
        assert doc.page_count == 42
        assert doc.metadata == {"author": "John"}

    def test_create_generates_unique_ids(self):
        d1 = Document.create(title="A", source_path="/a", content="x")
        d2 = Document.create(title="B", source_path="/b", content="y")
        assert d1.id != d2.id

    def test_create_generates_deterministic_hash(self):
        d1 = Document.create(title="A", source_path="/a", content="same content")
        d2 = Document.create(title="B", source_path="/b", content="same content")
        assert d1.content_hash == d2.content_hash

    def test_create_strips_whitespace(self):
        doc = Document.create(
            title="  Pump Manual  ",
            source_path="  /data/pump.pdf  ",
            content="x",
        )
        assert doc.title == "Pump Manual"
        assert doc.source_path == "/data/pump.pdf"

    def test_create_empty_title_raises(self):
        with pytest.raises(ValueError, match="title must not be empty"):
            Document.create(title="", source_path="/a", content="x")

    def test_create_whitespace_title_raises(self):
        with pytest.raises(ValueError, match="title must not be empty"):
            Document.create(title="   ", source_path="/a", content="x")

    def test_create_empty_source_path_raises(self):
        with pytest.raises(ValueError, match="source_path must not be empty"):
            Document.create(title="A", source_path="", content="x")

    def test_document_is_frozen(self):
        doc = Document.create(title="A", source_path="/a", content="x")
        with pytest.raises(FrozenInstanceError):
            doc.title = "Changed"  # type: ignore[misc]


class TestChunk:
    """Chunk entity construction and validation."""

    def test_create_with_minimal_args(self):
        chunk = Chunk.create(
            document_id=DocumentId("doc-001"),
            content="Some text content.",
        )
        assert chunk.content == "Some text content."
        assert chunk.document_id == "doc-001"
        assert chunk.chunk_index == 0
        assert chunk.embedding is None
        assert len(chunk.id) > 0

    def test_create_with_metadata(self):
        meta = ChunkMetadata(page_number=2, position_in_document=3)
        chunk = Chunk.create(
            document_id=DocumentId("doc-001"),
            content="Content",
            chunk_index=5,
            metadata=meta,
        )
        assert chunk.chunk_index == 5
        assert chunk.metadata.page_number == 2
        assert chunk.metadata.position_in_document == 3

    def test_create_empty_content_raises(self):
        with pytest.raises(ValueError, match="content must not be empty"):
            Chunk.create(document_id=DocumentId("doc-001"), content="")

    def test_create_whitespace_content_raises(self):
        with pytest.raises(ValueError, match="content must not be empty"):
            Chunk.create(document_id=DocumentId("doc-001"), content="   ")

    def test_chunk_is_frozen(self):
        chunk = Chunk.create(document_id=DocumentId("doc-001"), content="text")
        with pytest.raises(FrozenInstanceError):
            chunk.content = "Changed"  # type: ignore[misc]


class TestKnowledgeEntity:
    """KnowledgeEntity construction, canonical names, and validation."""

    def test_create_with_minimal_args(self):
        entity = KnowledgeEntity.create(
            name="Pump P-101",
            entity_type=EntityType.ASSET,
        )
        assert entity.name == "Pump P-101"
        assert entity.canonical_name == "pump_p_101"
        assert entity.entity_type is EntityType.ASSET
        assert entity.description == ""
        assert entity.provenance is None
        assert entity.attributes == {}

    def test_create_with_all_args(self):
        prov = Provenance(source_document_id="doc-001", confidence=0.9)
        entity = KnowledgeEntity.create(
            name="Bearing",
            entity_type=EntityType.COMPONENT,
            description="A rotating bearing",
            provenance=prov,
            attributes={"manufacturer": "SKF"},
        )
        assert entity.description == "A rotating bearing"
        assert entity.provenance is not None
        assert entity.provenance.confidence == 0.9
        assert entity.attributes == {"manufacturer": "SKF"}

    def test_canonical_name_normalization(self):
        """Verify various name forms normalize correctly."""
        cases = [
            ("Pump P-101", "pump_p_101"),
            ("  bearing FAILURE  ", "bearing_failure"),
            ("SKF-6205 Bearing", "skf_6205_bearing"),
            ("Heat Exchanger HX-301", "heat_exchanger_hx_301"),
            ("Production Line 1", "production_line_1"),
        ]
        for raw_name, expected_canonical in cases:
            entity = KnowledgeEntity.create(name=raw_name, entity_type=EntityType.ASSET)
            assert entity.canonical_name == expected_canonical, (
                f"'{raw_name}' should normalize to '{expected_canonical}', "
                f"got '{entity.canonical_name}'"
            )

    def test_create_empty_name_raises(self):
        with pytest.raises(ValueError, match="name must not be empty"):
            KnowledgeEntity.create(name="", entity_type=EntityType.ASSET)

    def test_create_generates_unique_ids(self):
        e1 = KnowledgeEntity.create(name="A", entity_type=EntityType.ASSET)
        e2 = KnowledgeEntity.create(name="B", entity_type=EntityType.ASSET)
        assert e1.id != e2.id

    def test_entity_is_frozen(self):
        entity = KnowledgeEntity.create(name="Pump", entity_type=EntityType.ASSET)
        with pytest.raises(FrozenInstanceError):
            entity.name = "Changed"  # type: ignore[misc]


class TestKnowledgeRelationship:
    """KnowledgeRelationship construction and validation."""

    def test_create_with_minimal_args(self):
        rel = KnowledgeRelationship.create(
            source_entity_id=EntityId("entity-001"),
            target_entity_id=EntityId("entity-002"),
            relation_type=RelationType.CAUSES,
        )
        assert rel.source_entity_id == "entity-001"
        assert rel.target_entity_id == "entity-002"
        assert rel.relation_type is RelationType.CAUSES
        assert rel.provenance is None
        assert len(rel.id) > 0

    def test_create_with_provenance(self):
        prov = Provenance(source_document_id="doc-001", confidence=0.85)
        rel = KnowledgeRelationship.create(
            source_entity_id=EntityId("e1"),
            target_entity_id=EntityId("e2"),
            relation_type=RelationType.HAS_COMPONENT,
            provenance=prov,
        )
        assert rel.provenance is not None
        assert rel.provenance.confidence == 0.85

    def test_create_self_loop_raises(self):
        with pytest.raises(ValueError, match="must be different entities"):
            KnowledgeRelationship.create(
                source_entity_id=EntityId("same-id"),
                target_entity_id=EntityId("same-id"),
                relation_type=RelationType.CAUSES,
            )

    def test_create_generates_unique_ids(self):
        r1 = KnowledgeRelationship.create(
            source_entity_id=EntityId("a"),
            target_entity_id=EntityId("b"),
            relation_type=RelationType.CAUSES,
        )
        r2 = KnowledgeRelationship.create(
            source_entity_id=EntityId("a"),
            target_entity_id=EntityId("b"),
            relation_type=RelationType.CAUSES,
        )
        assert r1.id != r2.id

    def test_relationship_is_frozen(self):
        rel = KnowledgeRelationship.create(
            source_entity_id=EntityId("a"),
            target_entity_id=EntityId("b"),
            relation_type=RelationType.CAUSES,
        )
        with pytest.raises(FrozenInstanceError):
            rel.relation_type = RelationType.RESOLVES  # type: ignore[misc]
