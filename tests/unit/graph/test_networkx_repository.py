"""Tests for the NetworkX-backed graph repository.

These tests verify:
  - Entity CRUD (add, get, search, query-by-type)
  - Merge-on-canonical-name (no duplicates)
  - Relationship CRUD (add, get, get-for-entity)
  - Graph traversal (neighbors, paths)
  - Visualization export (D3.js format)
  - Edge cases (missing entities, self-loops, empty graph)

Bounded Context: Graph
Test Layer: Unit
"""

from __future__ import annotations

import pytest

from forgemind.graph.adapters.networkx_repository import NetworkXGraphRepository
from forgemind.knowledge.domain.entities import (
    KnowledgeEntity,
    KnowledgeRelationship,
)
from forgemind.knowledge.domain.value_objects import EntityType, RelationType

# ── Fixtures ─────────────────────────────────────────────────────


@pytest.fixture()
def repo() -> NetworkXGraphRepository:
    """Fresh empty graph repository for each test."""
    return NetworkXGraphRepository()


@pytest.fixture()
def pump_entity() -> KnowledgeEntity:
    """A sample asset entity: Pump P-101."""
    return KnowledgeEntity.create(
        name="Pump P-101",
        entity_type=EntityType.ASSET,
        description="Single-stage centrifugal pump in Production Unit 3.",
    )


@pytest.fixture()
def bearing_entity() -> KnowledgeEntity:
    """A sample component entity: Bearing."""
    return KnowledgeEntity.create(
        name="Bearing",
        entity_type=EntityType.COMPONENT,
        description="SKF 6205-2RS deep groove ball bearing.",
    )


@pytest.fixture()
def vibration_entity() -> KnowledgeEntity:
    """A sample symptom entity: Excessive Vibration."""
    return KnowledgeEntity.create(
        name="Excessive Vibration",
        entity_type=EntityType.SYMPTOM,
        description="Vibration above 4.5 mm/s RMS on bearing housing.",
    )


@pytest.fixture()
def seal_entity() -> KnowledgeEntity:
    """A sample component entity: Mechanical Seal."""
    return KnowledgeEntity.create(
        name="Mechanical Seal",
        entity_type=EntityType.COMPONENT,
        description="John Crane Type 2100 cartridge seal.",
    )


# ══════════════════════════════════════════════════════════════════
# Entity CRUD
# ══════════════════════════════════════════════════════════════════


class TestAddEntity:
    """Tests for adding entities to the graph."""

    def test_add_entity_returns_id(
        self, repo: NetworkXGraphRepository, pump_entity: KnowledgeEntity
    ) -> None:
        entity_id = repo.add_entity(pump_entity)
        assert entity_id == pump_entity.id

    def test_add_entity_increases_count(
        self, repo: NetworkXGraphRepository, pump_entity: KnowledgeEntity
    ) -> None:
        assert repo.get_entity_count() == 0
        repo.add_entity(pump_entity)
        assert repo.get_entity_count() == 1

    def test_add_multiple_entities(
        self,
        repo: NetworkXGraphRepository,
        pump_entity: KnowledgeEntity,
        bearing_entity: KnowledgeEntity,
    ) -> None:
        repo.add_entity(pump_entity)
        repo.add_entity(bearing_entity)
        assert repo.get_entity_count() == 2


class TestGetEntity:
    """Tests for retrieving entities."""

    def test_get_existing_entity(
        self, repo: NetworkXGraphRepository, pump_entity: KnowledgeEntity
    ) -> None:
        repo.add_entity(pump_entity)
        retrieved = repo.get_entity(pump_entity.id)
        assert retrieved is not None
        assert retrieved.name == "Pump P-101"
        assert retrieved.entity_type == EntityType.ASSET

    def test_get_nonexistent_entity_returns_none(self, repo: NetworkXGraphRepository) -> None:
        from forgemind.shared.types import EntityId

        result = repo.get_entity(EntityId("nonexistent-id"))
        assert result is None

    def test_get_entity_preserves_description(
        self, repo: NetworkXGraphRepository, pump_entity: KnowledgeEntity
    ) -> None:
        repo.add_entity(pump_entity)
        retrieved = repo.get_entity(pump_entity.id)
        assert retrieved is not None
        assert "centrifugal pump" in retrieved.description


class TestMergeOnCanonicalName:
    """Tests for the merge-on-canonical-name behavior."""

    def test_same_canonical_name_returns_existing_id(self, repo: NetworkXGraphRepository) -> None:
        """Adding 'Pump P-101' twice should return the same ID."""
        entity1 = KnowledgeEntity.create("Pump P-101", EntityType.ASSET)
        entity2 = KnowledgeEntity.create("pump p-101", EntityType.ASSET)

        id1 = repo.add_entity(entity1)
        id2 = repo.add_entity(entity2)

        assert id1 == id2
        assert repo.get_entity_count() == 1

    def test_different_types_are_not_merged(self, repo: NetworkXGraphRepository) -> None:
        """'Bearing' as COMPONENT and 'Bearing' as PART should be separate."""
        component = KnowledgeEntity.create("Bearing", EntityType.COMPONENT)
        part = KnowledgeEntity.create("Bearing", EntityType.PART)

        id1 = repo.add_entity(component)
        id2 = repo.add_entity(part)

        assert id1 != id2
        assert repo.get_entity_count() == 2

    def test_case_insensitive_merge(self, repo: NetworkXGraphRepository) -> None:
        e1 = KnowledgeEntity.create("Mechanical Seal", EntityType.COMPONENT)
        e2 = KnowledgeEntity.create("MECHANICAL SEAL", EntityType.COMPONENT)

        id1 = repo.add_entity(e1)
        id2 = repo.add_entity(e2)

        assert id1 == id2
        assert repo.get_entity_count() == 1


class TestFindByCanonicalName:
    """Tests for canonical name lookup."""

    def test_find_existing(
        self, repo: NetworkXGraphRepository, pump_entity: KnowledgeEntity
    ) -> None:
        repo.add_entity(pump_entity)
        found = repo.find_entity_by_canonical_name(pump_entity.canonical_name, EntityType.ASSET)
        assert found is not None
        assert found.name == "Pump P-101"

    def test_find_nonexistent_returns_none(self, repo: NetworkXGraphRepository) -> None:
        found = repo.find_entity_by_canonical_name("nonexistent", EntityType.ASSET)
        assert found is None

    def test_find_wrong_type_returns_none(
        self, repo: NetworkXGraphRepository, pump_entity: KnowledgeEntity
    ) -> None:
        repo.add_entity(pump_entity)
        found = repo.find_entity_by_canonical_name(
            pump_entity.canonical_name, EntityType.COMPONENT
        )
        assert found is None


class TestUpdateEntity:
    """Tests for updating entity data."""

    def test_update_description(
        self, repo: NetworkXGraphRepository, pump_entity: KnowledgeEntity
    ) -> None:
        repo.add_entity(pump_entity)
        updated = KnowledgeEntity(
            id=pump_entity.id,
            name=pump_entity.name,
            canonical_name=pump_entity.canonical_name,
            entity_type=pump_entity.entity_type,
            description="Updated description with new evidence.",
            provenance=pump_entity.provenance,
            attributes={"evidence_count": "3"},
        )
        repo.update_entity(updated)
        retrieved = repo.get_entity(pump_entity.id)
        assert retrieved is not None
        assert retrieved.description == "Updated description with new evidence."
        assert retrieved.attributes["evidence_count"] == "3"

    def test_update_nonexistent_raises(
        self, repo: NetworkXGraphRepository, pump_entity: KnowledgeEntity
    ) -> None:
        with pytest.raises(KeyError, match="not found"):
            repo.update_entity(pump_entity)


# ══════════════════════════════════════════════════════════════════
# Relationship CRUD
# ══════════════════════════════════════════════════════════════════


class TestAddRelationship:
    """Tests for adding relationships."""

    def test_add_relationship_returns_id(
        self,
        repo: NetworkXGraphRepository,
        pump_entity: KnowledgeEntity,
        bearing_entity: KnowledgeEntity,
    ) -> None:
        repo.add_entity(pump_entity)
        repo.add_entity(bearing_entity)

        rel = KnowledgeRelationship.create(
            source_entity_id=pump_entity.id,
            target_entity_id=bearing_entity.id,
            relation_type=RelationType.HAS_COMPONENT,
        )
        rel_id = repo.add_relationship(rel)
        assert rel_id == rel.id

    def test_add_relationship_increases_count(
        self,
        repo: NetworkXGraphRepository,
        pump_entity: KnowledgeEntity,
        bearing_entity: KnowledgeEntity,
    ) -> None:
        repo.add_entity(pump_entity)
        repo.add_entity(bearing_entity)

        assert repo.get_relationship_count() == 0
        rel = KnowledgeRelationship.create(
            source_entity_id=pump_entity.id,
            target_entity_id=bearing_entity.id,
            relation_type=RelationType.HAS_COMPONENT,
        )
        repo.add_relationship(rel)
        assert repo.get_relationship_count() == 1

    def test_add_relationship_missing_source_raises(
        self, repo: NetworkXGraphRepository, bearing_entity: KnowledgeEntity
    ) -> None:
        from forgemind.shared.types import EntityId

        repo.add_entity(bearing_entity)
        rel = KnowledgeRelationship.create(
            source_entity_id=EntityId("nonexistent"),
            target_entity_id=bearing_entity.id,
            relation_type=RelationType.HAS_COMPONENT,
        )
        with pytest.raises(KeyError, match="Source entity"):
            repo.add_relationship(rel)

    def test_add_relationship_missing_target_raises(
        self, repo: NetworkXGraphRepository, pump_entity: KnowledgeEntity
    ) -> None:
        from forgemind.shared.types import EntityId

        repo.add_entity(pump_entity)
        rel = KnowledgeRelationship.create(
            source_entity_id=pump_entity.id,
            target_entity_id=EntityId("nonexistent"),
            relation_type=RelationType.HAS_COMPONENT,
        )
        with pytest.raises(KeyError, match="Target entity"):
            repo.add_relationship(rel)

    def test_duplicate_relationship_is_skipped(
        self,
        repo: NetworkXGraphRepository,
        pump_entity: KnowledgeEntity,
        bearing_entity: KnowledgeEntity,
    ) -> None:
        repo.add_entity(pump_entity)
        repo.add_entity(bearing_entity)

        rel1 = KnowledgeRelationship.create(
            source_entity_id=pump_entity.id,
            target_entity_id=bearing_entity.id,
            relation_type=RelationType.HAS_COMPONENT,
        )
        rel2 = KnowledgeRelationship.create(
            source_entity_id=pump_entity.id,
            target_entity_id=bearing_entity.id,
            relation_type=RelationType.HAS_COMPONENT,
        )
        repo.add_relationship(rel1)
        repo.add_relationship(rel2)
        assert repo.get_relationship_count() == 1


class TestGetRelationship:
    """Tests for retrieving relationships."""

    def test_get_existing_relationship(
        self,
        repo: NetworkXGraphRepository,
        pump_entity: KnowledgeEntity,
        bearing_entity: KnowledgeEntity,
    ) -> None:
        repo.add_entity(pump_entity)
        repo.add_entity(bearing_entity)
        rel = KnowledgeRelationship.create(
            source_entity_id=pump_entity.id,
            target_entity_id=bearing_entity.id,
            relation_type=RelationType.HAS_COMPONENT,
        )
        repo.add_relationship(rel)

        retrieved = repo.get_relationship(rel.id)
        assert retrieved is not None
        assert retrieved.relation_type == RelationType.HAS_COMPONENT

    def test_get_nonexistent_relationship_returns_none(
        self, repo: NetworkXGraphRepository
    ) -> None:
        from forgemind.shared.types import RelationshipId

        result = repo.get_relationship(RelationshipId("nonexistent"))
        assert result is None


class TestGetRelationshipsFor:
    """Tests for getting all relationships of an entity."""

    def test_get_outgoing_and_incoming(
        self,
        repo: NetworkXGraphRepository,
        pump_entity: KnowledgeEntity,
        bearing_entity: KnowledgeEntity,
        vibration_entity: KnowledgeEntity,
    ) -> None:
        repo.add_entity(pump_entity)
        repo.add_entity(bearing_entity)
        repo.add_entity(vibration_entity)

        # Pump → Bearing (outgoing from pump)
        rel1 = KnowledgeRelationship.create(
            source_entity_id=pump_entity.id,
            target_entity_id=bearing_entity.id,
            relation_type=RelationType.HAS_COMPONENT,
        )
        # Bearing → Vibration (outgoing from bearing)
        rel2 = KnowledgeRelationship.create(
            source_entity_id=bearing_entity.id,
            target_entity_id=vibration_entity.id,
            relation_type=RelationType.HAS_SYMPTOM,
        )
        repo.add_relationship(rel1)
        repo.add_relationship(rel2)

        # Bearing should have 2 relationships (1 incoming, 1 outgoing)
        rels = repo.get_relationships_for(bearing_entity.id)
        assert len(rels) == 2


# ══════════════════════════════════════════════════════════════════
# Traversal
# ══════════════════════════════════════════════════════════════════


class TestGetNeighbors:
    """Tests for BFS neighbor traversal."""

    def test_direct_neighbors_depth_1(
        self,
        repo: NetworkXGraphRepository,
        pump_entity: KnowledgeEntity,
        bearing_entity: KnowledgeEntity,
        seal_entity: KnowledgeEntity,
    ) -> None:
        repo.add_entity(pump_entity)
        repo.add_entity(bearing_entity)
        repo.add_entity(seal_entity)

        repo.add_relationship(
            KnowledgeRelationship.create(
                pump_entity.id, bearing_entity.id, RelationType.HAS_COMPONENT
            )
        )
        repo.add_relationship(
            KnowledgeRelationship.create(
                pump_entity.id, seal_entity.id, RelationType.HAS_COMPONENT
            )
        )

        neighbors = repo.get_neighbors(pump_entity.id, depth=1)
        names = {n.name for n in neighbors}
        assert names == {"Bearing", "Mechanical Seal"}

    def test_depth_2_finds_indirect_neighbors(
        self,
        repo: NetworkXGraphRepository,
        pump_entity: KnowledgeEntity,
        bearing_entity: KnowledgeEntity,
        vibration_entity: KnowledgeEntity,
    ) -> None:
        repo.add_entity(pump_entity)
        repo.add_entity(bearing_entity)
        repo.add_entity(vibration_entity)

        repo.add_relationship(
            KnowledgeRelationship.create(
                pump_entity.id, bearing_entity.id, RelationType.HAS_COMPONENT
            )
        )
        repo.add_relationship(
            KnowledgeRelationship.create(
                bearing_entity.id, vibration_entity.id, RelationType.HAS_SYMPTOM
            )
        )

        # Depth 1 from pump should only find bearing
        depth_1 = repo.get_neighbors(pump_entity.id, depth=1)
        assert len(depth_1) == 1

        # Depth 2 from pump should find bearing AND vibration
        depth_2 = repo.get_neighbors(pump_entity.id, depth=2)
        assert len(depth_2) == 2

    def test_neighbors_of_missing_entity_returns_empty(
        self, repo: NetworkXGraphRepository
    ) -> None:
        from forgemind.shared.types import EntityId

        result = repo.get_neighbors(EntityId("nonexistent"))
        assert result == []

    def test_filter_by_relation_type(
        self,
        repo: NetworkXGraphRepository,
        pump_entity: KnowledgeEntity,
        bearing_entity: KnowledgeEntity,
        vibration_entity: KnowledgeEntity,
    ) -> None:
        repo.add_entity(pump_entity)
        repo.add_entity(bearing_entity)
        repo.add_entity(vibration_entity)

        repo.add_relationship(
            KnowledgeRelationship.create(
                pump_entity.id, bearing_entity.id, RelationType.HAS_COMPONENT
            )
        )
        repo.add_relationship(
            KnowledgeRelationship.create(
                pump_entity.id, vibration_entity.id, RelationType.HAS_SYMPTOM
            )
        )

        # Only HAS_COMPONENT neighbors
        components = repo.get_neighbors(
            pump_entity.id, depth=1, relation_types=[RelationType.HAS_COMPONENT]
        )
        assert len(components) == 1
        assert components[0].name == "Bearing"


class TestFindPaths:
    """Tests for path finding."""

    def test_find_direct_path(
        self,
        repo: NetworkXGraphRepository,
        pump_entity: KnowledgeEntity,
        bearing_entity: KnowledgeEntity,
    ) -> None:
        repo.add_entity(pump_entity)
        repo.add_entity(bearing_entity)
        repo.add_relationship(
            KnowledgeRelationship.create(
                pump_entity.id, bearing_entity.id, RelationType.HAS_COMPONENT
            )
        )

        paths = repo.find_paths(pump_entity.id, bearing_entity.id)
        assert len(paths) == 1
        assert len(paths[0]) == 2  # Two nodes in the path

    def test_find_path_through_intermediate(
        self,
        repo: NetworkXGraphRepository,
        pump_entity: KnowledgeEntity,
        bearing_entity: KnowledgeEntity,
        vibration_entity: KnowledgeEntity,
    ) -> None:
        repo.add_entity(pump_entity)
        repo.add_entity(bearing_entity)
        repo.add_entity(vibration_entity)

        repo.add_relationship(
            KnowledgeRelationship.create(
                pump_entity.id, bearing_entity.id, RelationType.HAS_COMPONENT
            )
        )
        repo.add_relationship(
            KnowledgeRelationship.create(
                bearing_entity.id, vibration_entity.id, RelationType.HAS_SYMPTOM
            )
        )

        paths = repo.find_paths(pump_entity.id, vibration_entity.id)
        assert len(paths) >= 1
        assert len(paths[0]) == 3  # Pump → Bearing → Vibration

    def test_no_path_returns_empty(
        self,
        repo: NetworkXGraphRepository,
        pump_entity: KnowledgeEntity,
        vibration_entity: KnowledgeEntity,
    ) -> None:
        repo.add_entity(pump_entity)
        repo.add_entity(vibration_entity)
        # No edge between them
        paths = repo.find_paths(pump_entity.id, vibration_entity.id)
        assert paths == []


# ══════════════════════════════════════════════════════════════════
# Query
# ══════════════════════════════════════════════════════════════════


class TestQueryByType:
    """Tests for type-based queries."""

    def test_query_returns_matching_type(
        self,
        repo: NetworkXGraphRepository,
        pump_entity: KnowledgeEntity,
        bearing_entity: KnowledgeEntity,
    ) -> None:
        repo.add_entity(pump_entity)
        repo.add_entity(bearing_entity)

        assets = repo.query_by_type(EntityType.ASSET)
        assert len(assets) == 1
        assert assets[0].name == "Pump P-101"

        components = repo.query_by_type(EntityType.COMPONENT)
        assert len(components) == 1
        assert components[0].name == "Bearing"

    def test_query_empty_type_returns_empty(
        self,
        repo: NetworkXGraphRepository,
        pump_entity: KnowledgeEntity,
    ) -> None:
        repo.add_entity(pump_entity)
        symptoms = repo.query_by_type(EntityType.SYMPTOM)
        assert symptoms == []


class TestSearchEntities:
    """Tests for name-based search."""

    def test_search_by_substring(
        self,
        repo: NetworkXGraphRepository,
        pump_entity: KnowledgeEntity,
        bearing_entity: KnowledgeEntity,
    ) -> None:
        repo.add_entity(pump_entity)
        repo.add_entity(bearing_entity)

        results = repo.search_entities("pump")
        assert len(results) == 1
        assert results[0].name == "Pump P-101"

    def test_search_case_insensitive(
        self,
        repo: NetworkXGraphRepository,
        pump_entity: KnowledgeEntity,
    ) -> None:
        repo.add_entity(pump_entity)

        results = repo.search_entities("PUMP")
        assert len(results) == 1

    def test_search_no_results(
        self, repo: NetworkXGraphRepository, pump_entity: KnowledgeEntity
    ) -> None:
        repo.add_entity(pump_entity)
        results = repo.search_entities("nonexistent")
        assert results == []


# ══════════════════════════════════════════════════════════════════
# Visualization Export
# ══════════════════════════════════════════════════════════════════


class TestExportForVisualization:
    """Tests for D3.js export."""

    def test_empty_graph_export(self, repo: NetworkXGraphRepository) -> None:
        data = repo.export_for_visualization()
        assert data == {"nodes": [], "edges": []}

    def test_export_includes_nodes_and_edges(
        self,
        repo: NetworkXGraphRepository,
        pump_entity: KnowledgeEntity,
        bearing_entity: KnowledgeEntity,
    ) -> None:
        repo.add_entity(pump_entity)
        repo.add_entity(bearing_entity)
        repo.add_relationship(
            KnowledgeRelationship.create(
                pump_entity.id, bearing_entity.id, RelationType.HAS_COMPONENT
            )
        )

        data = repo.export_for_visualization()
        assert len(data["nodes"]) == 2
        assert len(data["edges"]) == 1

    def test_export_node_has_required_fields(
        self,
        repo: NetworkXGraphRepository,
        pump_entity: KnowledgeEntity,
    ) -> None:
        repo.add_entity(pump_entity)
        data = repo.export_for_visualization()
        node = data["nodes"][0]

        assert "id" in node
        assert node["name"] == "Pump P-101"
        assert node["type"] == "asset"
        assert node["group"] == 0  # Assets are group 0

    def test_export_edge_has_required_fields(
        self,
        repo: NetworkXGraphRepository,
        pump_entity: KnowledgeEntity,
        bearing_entity: KnowledgeEntity,
    ) -> None:
        repo.add_entity(pump_entity)
        repo.add_entity(bearing_entity)
        repo.add_relationship(
            KnowledgeRelationship.create(
                pump_entity.id, bearing_entity.id, RelationType.HAS_COMPONENT
            )
        )

        data = repo.export_for_visualization()
        edge = data["edges"][0]

        assert edge["source"] == str(pump_entity.id)
        assert edge["target"] == str(bearing_entity.id)
        assert edge["type"] == "has_component"
        assert edge["label"] == "Has Component"
