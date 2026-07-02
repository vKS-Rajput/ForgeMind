"""Graph outbound ports — graph storage interface.

The GraphRepository protocol is the primary interface for knowledge
graph persistence. Designed for NetworkX V1 and Neo4j V2 compatibility.

Bounded Context: Graph
Layer: Ports (Outbound)
Dependencies: knowledge.domain.entities, knowledge.domain.value_objects
"""

from __future__ import annotations

from typing import Protocol

from forgemind.knowledge.domain.entities import (
    KnowledgeEntity,
    KnowledgeRelationship,
)
from forgemind.knowledge.domain.value_objects import EntityType, RelationType
from forgemind.shared.types import EntityId, RelationshipId


class GraphRepository(Protocol):
    """Persistence and query interface for the knowledge graph.

    All graph operations go through this protocol. V1 is implemented
    by a NetworkX adapter; V2 will add a Neo4j adapter. Both implement
    the same interface.
    """

    def add_entity(self, entity: KnowledgeEntity) -> EntityId:
        """Add an entity as a node in the graph.

        If an entity with the same canonical name and type already exists,
        the implementation should merge or update rather than duplicate.

        Args:
            entity: The entity to add.

        Returns:
            The entity's ID (may differ from input if merged).
        """
        ...

    def add_relationship(self, relationship: KnowledgeRelationship) -> RelationshipId:
        """Add a relationship as an edge in the graph.

        Both source and target entities must already exist in the graph.

        Args:
            relationship: The relationship to add.

        Returns:
            The relationship's ID.

        Raises:
            EntityNotFoundError: If source or target entity is not in the graph.
        """
        ...

    def get_entity(self, entity_id: EntityId) -> KnowledgeEntity | None:
        """Retrieve an entity by ID.

        Args:
            entity_id: The entity's unique identifier.

        Returns:
            The entity, or None if not found.
        """
        ...

    def get_neighbors(
        self,
        entity_id: EntityId,
        depth: int = 1,
        relation_types: list[RelationType] | None = None,
    ) -> list[KnowledgeEntity]:
        """Get entities connected to the given entity within N hops.

        Args:
            entity_id: The starting entity.
            depth: Maximum traversal depth (1 = direct neighbors).
            relation_types: Optional filter by relationship type.

        Returns:
            List of connected entities (excluding the starting entity).
        """
        ...

    def find_paths(
        self,
        source_id: EntityId,
        target_id: EntityId,
        max_depth: int = 5,
    ) -> list[list[KnowledgeEntity]]:
        """Find paths between two entities in the graph.

        Args:
            source_id: Starting entity ID.
            target_id: Target entity ID.
            max_depth: Maximum path length.

        Returns:
            List of paths, where each path is a list of entities
            from source to target. Empty list if no path exists.
        """
        ...

    def query_by_type(self, entity_type: EntityType) -> list[KnowledgeEntity]:
        """Get all entities of a given type.

        Args:
            entity_type: The entity type to filter by.

        Returns:
            All entities matching the type.
        """
        ...

    def search_entities(self, query: str) -> list[KnowledgeEntity]:
        """Search entities by name (substring match).

        Args:
            query: Search string to match against entity names.

        Returns:
            Matching entities, ordered by relevance.
        """
        ...

    def get_entity_count(self) -> int:
        """Get the total number of entities in the graph.

        Returns:
            Total node count.
        """
        ...

    def get_relationship_count(self) -> int:
        """Get the total number of relationships in the graph.

        Returns:
            Total edge count.
        """
        ...
