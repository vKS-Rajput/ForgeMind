"""NetworkX-backed knowledge graph repository.

Implements the GraphRepository protocol using NetworkX DiGraph.
This is the V1 storage engine — zero infrastructure, in-process,
perfect for hackathon speed and offline operation.

Key Design Decisions:
  - Merge-on-canonical-name: adding an entity whose canonical_name
    already exists updates the existing node instead of duplicating.
    This is critical for Knowledge Evolution — the same concept
    mentioned across multiple documents converges to a single node.
  - Thread-safe: all mutations protected by threading.Lock, matching
    the pattern established in memory_document_repository.py.
  - Rich node/edge attributes: all entity and relationship metadata
    is stored as NetworkX node/edge attributes, enabling rich queries.
  - export_for_visualization() produces a D3.js-ready JSON structure.

Bounded Context: Graph
Layer: Adapters
Dependencies: networkx, knowledge.domain.entities, knowledge.domain.value_objects
"""

from __future__ import annotations

import threading
from typing import Any

import networkx as nx

from forgemind.knowledge.domain.entities import (
    KnowledgeEntity,
    KnowledgeRelationship,
)
from forgemind.knowledge.domain.value_objects import EntityType, RelationType
from forgemind.shared.logging import get_logger
from forgemind.shared.types import EntityId, RelationshipId

logger = get_logger(__name__)


class NetworkXGraphRepository:
    """In-memory knowledge graph backed by a NetworkX directed graph.

    Entities are stored as nodes, relationships as directed edges.
    The graph supports merge-on-canonical-name to prevent duplicate
    nodes when the same concept appears in multiple documents.

    Thread Safety:
        All public methods are protected by a reentrant lock.
        Safe for concurrent use from FastAPI async handlers.

    Example:
        >>> repo = NetworkXGraphRepository()
        >>> entity = KnowledgeEntity.create("Pump P-101", EntityType.ASSET)
        >>> entity_id = repo.add_entity(entity)
        >>> repo.get_entity(entity_id).name
        'Pump P-101'
    """

    def __init__(self) -> None:
        """Initialize an empty directed graph with lookup indices."""
        self._graph: nx.DiGraph = nx.DiGraph()
        self._lock = threading.Lock()

        # Index: canonical_name → EntityId for fast merge lookups.
        # Key is (canonical_name, entity_type) to allow "Bearing" as
        # both a COMPONENT and a PART if they have different types.
        self._canonical_index: dict[tuple[str, EntityType], EntityId] = {}

        # Index: RelationshipId → (source_id, target_id) for edge lookups.
        self._relationship_index: dict[RelationshipId, tuple[EntityId, EntityId]] = {}

    # ── Entity Operations ────────────────────────────────────────

    def add_entity(self, entity: KnowledgeEntity) -> EntityId:
        """Add an entity as a node, merging if canonical name already exists.

        If an entity with the same canonical_name and entity_type already
        exists, the existing node is returned unchanged. The Knowledge
        Evolution Engine (Sprint 4) handles confidence updates separately.

        Args:
            entity: The entity to add or merge.

        Returns:
            The entity's ID (existing ID if merged, new ID if created).
        """
        with self._lock:
            lookup_key = (entity.canonical_name, entity.entity_type)

            # Check if this entity already exists (merge-on-canonical-name)
            existing_id = self._canonical_index.get(lookup_key)
            if existing_id is not None:
                logger.debug(
                    "entity_merged",
                    canonical_name=entity.canonical_name,
                    entity_type=entity.entity_type.value,
                    existing_id=str(existing_id),
                )
                return existing_id

            # Add new node with all entity attributes
            self._graph.add_node(
                str(entity.id),
                name=entity.name,
                canonical_name=entity.canonical_name,
                entity_type=entity.entity_type.value,
                description=entity.description,
                provenance=entity.provenance,
                attributes=entity.attributes,
                _entity=entity,  # Store full entity for retrieval
            )

            # Update index
            self._canonical_index[lookup_key] = entity.id

            logger.debug(
                "entity_added",
                name=entity.name,
                entity_type=entity.entity_type.value,
                entity_id=str(entity.id),
            )
            return entity.id

    def get_entity(self, entity_id: EntityId) -> KnowledgeEntity | None:
        """Retrieve an entity by its unique ID.

        Args:
            entity_id: The entity's unique identifier.

        Returns:
            The entity, or None if not found.
        """
        with self._lock:
            if str(entity_id) not in self._graph:
                return None
            node_data = self._graph.nodes[str(entity_id)]
            result: KnowledgeEntity | None = node_data.get("_entity")
            return result

    def find_entity_by_canonical_name(
        self, canonical_name: str, entity_type: EntityType
    ) -> KnowledgeEntity | None:
        """Find an entity by its canonical name and type.

        This is used by the Knowledge Evolution Engine to check
        whether a concept already exists before deciding to merge
        or create.

        Args:
            canonical_name: The normalized entity name.
            entity_type: The entity's type classification.

        Returns:
            The matching entity, or None if not found.
        """
        with self._lock:
            entity_id = self._canonical_index.get((canonical_name, entity_type))
            if entity_id is None:
                return None
            node_data = self._graph.nodes[str(entity_id)]
            result: KnowledgeEntity | None = node_data.get("_entity")
            return result

    def update_entity(self, entity: KnowledgeEntity) -> None:
        """Replace an existing entity's data in the graph.

        Used by the Knowledge Evolution Engine when confidence
        changes or new evidence is added. The canonical name index
        is NOT updated — use this only for metadata changes.

        Args:
            entity: The updated entity (must have same ID as existing).

        Raises:
            KeyError: If the entity does not exist in the graph.
        """
        with self._lock:
            node_id = str(entity.id)
            if node_id not in self._graph:
                msg = f"Entity '{entity.id}' not found in graph"
                raise KeyError(msg)

            self._graph.nodes[node_id].update(
                {
                    "name": entity.name,
                    "canonical_name": entity.canonical_name,
                    "entity_type": entity.entity_type.value,
                    "description": entity.description,
                    "provenance": entity.provenance,
                    "attributes": entity.attributes,
                    "_entity": entity,
                }
            )

    # ── Relationship Operations ──────────────────────────────────

    def add_relationship(self, relationship: KnowledgeRelationship) -> RelationshipId:
        """Add a directed relationship as an edge between two entities.

        Both source and target entities must already exist in the graph.
        Duplicate edges (same source, target, and relation_type) are
        silently skipped to prevent redundant connections.

        Args:
            relationship: The relationship to add.

        Returns:
            The relationship's ID.

        Raises:
            KeyError: If source or target entity is not in the graph.
        """
        with self._lock:
            source_id = str(relationship.source_entity_id)
            target_id = str(relationship.target_entity_id)

            if source_id not in self._graph:
                msg = f"Source entity '{relationship.source_entity_id}' not in graph"
                raise KeyError(msg)
            if target_id not in self._graph:
                msg = f"Target entity '{relationship.target_entity_id}' not in graph"
                raise KeyError(msg)

            # Check for duplicate edge (same source, target, relation_type)
            if self._graph.has_edge(source_id, target_id):
                existing = self._graph.edges[source_id, target_id]
                if existing.get("relation_type") == relationship.relation_type.value:
                    return RelationshipId(existing.get("relationship_id", str(relationship.id)))

            # Add directed edge with relationship metadata
            self._graph.add_edge(
                source_id,
                target_id,
                relationship_id=str(relationship.id),
                relation_type=relationship.relation_type.value,
                provenance=relationship.provenance,
                attributes=relationship.attributes,
                _relationship=relationship,
            )

            # Update index
            self._relationship_index[relationship.id] = (
                relationship.source_entity_id,
                relationship.target_entity_id,
            )

            logger.debug(
                "relationship_added",
                source=source_id,
                target=target_id,
                relation_type=relationship.relation_type.value,
            )
            return relationship.id

    def get_relationship(self, relationship_id: RelationshipId) -> KnowledgeRelationship | None:
        """Retrieve a relationship by its unique ID.

        Args:
            relationship_id: The relationship's unique identifier.

        Returns:
            The relationship, or None if not found.
        """
        with self._lock:
            endpoints = self._relationship_index.get(relationship_id)
            if endpoints is None:
                return None
            source_id, target_id = endpoints
            edge_data = self._graph.edges.get((str(source_id), str(target_id)))
            if edge_data is None:
                return None
            result: KnowledgeRelationship | None = edge_data.get("_relationship")
            return result

    def get_relationships_for(self, entity_id: EntityId) -> list[KnowledgeRelationship]:
        """Get all relationships connected to an entity (in or out).

        Args:
            entity_id: The entity to find relationships for.

        Returns:
            All relationships where this entity is source or target.
        """
        with self._lock:
            node_id = str(entity_id)
            if node_id not in self._graph:
                return []

            relationships: list[KnowledgeRelationship] = []

            # Outgoing edges (this entity is the source)
            for _, _target, data in self._graph.out_edges(node_id, data=True):
                rel = data.get("_relationship")
                if rel is not None:
                    relationships.append(rel)

            # Incoming edges (this entity is the target)
            for _source, _, data in self._graph.in_edges(node_id, data=True):
                rel = data.get("_relationship")
                if rel is not None:
                    relationships.append(rel)

            return relationships

    # ── Traversal Operations ─────────────────────────────────────

    def _edge_matches_filter(
        self,
        node_a: str,
        node_b: str,
        allowed_types: set[str],
    ) -> bool:
        """Check if any edge between two nodes matches allowed types.

        Checks both directions (a→b and b→a) since we traverse
        an undirected view but edges are stored as directed.

        Args:
            node_a: First node ID.
            node_b: Second node ID.
            allowed_types: Set of relation_type values to accept.

        Returns:
            True if at least one edge matches the filter.
        """
        for src, tgt in [(node_a, node_b), (node_b, node_a)]:
            if self._graph.has_edge(src, tgt):
                edge_type = self._graph.edges[src, tgt].get("relation_type")
                if edge_type in allowed_types:
                    return True
        return False

    def get_neighbors(
        self,
        entity_id: EntityId,
        depth: int = 1,
        relation_types: list[RelationType] | None = None,
    ) -> list[KnowledgeEntity]:
        """Get entities connected within N hops via BFS.

        Traverses both incoming and outgoing edges. Optionally
        filters by relationship type.

        Args:
            entity_id: The starting entity.
            depth: Maximum traversal depth (1 = direct neighbors).
            relation_types: Optional filter — only traverse these types.

        Returns:
            Connected entities (excluding the starting entity).
        """
        with self._lock:
            node_id = str(entity_id)
            if node_id not in self._graph:
                return []

            allowed = {rt.value for rt in relation_types} if relation_types else None
            undirected = self._graph.to_undirected()
            visited: set[str] = set()
            queue: list[tuple[str, int]] = [(node_id, 0)]

            while queue:
                current, current_depth = queue.pop(0)
                if current_depth >= depth:
                    continue
                for neighbor in undirected.neighbors(current):
                    if neighbor in visited or neighbor == node_id:
                        continue
                    if allowed and not self._edge_matches_filter(current, neighbor, allowed):
                        continue
                    visited.add(neighbor)
                    queue.append((neighbor, current_depth + 1))

            # Convert node IDs back to entities
            entities: list[KnowledgeEntity] = []
            for nid in visited:
                entity = self._graph.nodes[nid].get("_entity")
                if entity is not None:
                    entities.append(entity)

            return entities

    def find_paths(
        self,
        source_id: EntityId,
        target_id: EntityId,
        max_depth: int = 5,
    ) -> list[list[EntityId]]:
        """Find all simple paths between two entities.

        Uses NetworkX's all_simple_paths with a cutoff. Returns
        paths as lists of EntityIds for the caller to resolve.

        Args:
            source_id: Starting entity ID.
            target_id: Target entity ID.
            max_depth: Maximum path length.

        Returns:
            List of paths (each path is a list of EntityIds).
            Empty if no path exists or entities are not in graph.
        """
        with self._lock:
            src = str(source_id)
            tgt = str(target_id)

            if src not in self._graph or tgt not in self._graph:
                return []

            # Search in undirected view to find paths in either direction
            undirected = self._graph.to_undirected()
            try:
                raw_paths = list(nx.all_simple_paths(undirected, src, tgt, cutoff=max_depth))
            except nx.NetworkXError:
                return []

            # pyrefly: ignore [bad-argument-type]
            return [[EntityId(node_id) for node_id in path] for path in raw_paths]

    # ── Query Operations ─────────────────────────────────────────

    def query_by_type(self, entity_type: EntityType) -> list[KnowledgeEntity]:
        """Get all entities of a given type.

        Args:
            entity_type: The entity type to filter by.

        Returns:
            All entities matching the type, sorted by name.
        """
        with self._lock:
            entities: list[KnowledgeEntity] = []
            type_value = entity_type.value
            for _, data in self._graph.nodes(data=True):
                if data.get("entity_type") == type_value:
                    entity = data.get("_entity")
                    if entity is not None:
                        entities.append(entity)
            return sorted(entities, key=lambda e: e.name)

    def search_entities(self, query: str) -> list[KnowledgeEntity]:
        """Search entities by name (case-insensitive substring match).

        Args:
            query: Search string to match against entity names.

        Returns:
            Matching entities, sorted by name.
        """
        with self._lock:
            query_lower = query.lower()
            matches: list[KnowledgeEntity] = []
            for _, data in self._graph.nodes(data=True):
                name = data.get("name", "")
                canonical = data.get("canonical_name", "")
                if query_lower in name.lower() or query_lower in canonical:
                    entity = data.get("_entity")
                    if entity is not None:
                        matches.append(entity)
            return sorted(matches, key=lambda e: e.name)

    # ── Statistics ───────────────────────────────────────────────

    def get_entity_count(self) -> int:
        """Get the total number of entities (nodes) in the graph.

        Returns:
            Total node count.
        """
        with self._lock:
            count: int = self._graph.number_of_nodes()
            return count

    def get_relationship_count(self) -> int:
        """Get the total number of relationships (edges) in the graph.

        Returns:
            Total edge count.
        """
        with self._lock:
            count: int = self._graph.number_of_edges()
            return count

    # ── Visualization Export ─────────────────────────────────────

    def export_for_visualization(self) -> dict[str, list[dict[str, Any]]]:
        """Export the graph as a D3.js-compatible JSON structure.

        Returns a dictionary with 'nodes' and 'edges' lists. Each
        node has id, name, type, and group (for color coding). Each
        edge has source, target, type, and label.

        Returns:
            D3.js-ready graph data: {nodes: [...], edges: [...]}.
        """
        with self._lock:
            # Map entity types to numeric groups for D3 color coding
            type_groups: dict[str, int] = {
                "asset": 0,
                "component": 1,
                "failure_mode": 2,
                "symptom": 3,
                "action": 4,
                "condition": 5,
                "location": 6,
                "part": 7,
            }

            nodes: list[dict[str, Any]] = []
            for node_id, data in self._graph.nodes(data=True):
                entity_type = data.get("entity_type", "unknown")
                nodes.append(
                    {
                        "id": node_id,
                        "name": data.get("name", "Unknown"),
                        "type": entity_type,
                        "group": type_groups.get(entity_type, 8),
                        "description": data.get("description", ""),
                        "confidence": float(data.get("confidence", 0.85)),
                    }
                )

            edges: list[dict[str, Any]] = []
            for source, target, data in self._graph.edges(data=True):
                relation_type = data.get("relation_type", "related_to")
                edges.append(
                    {
                        "source": source,
                        "target": target,
                        "type": relation_type,
                        "label": relation_type.replace("_", " ").title(),
                    }
                )

            return {"nodes": nodes, "edges": edges}
