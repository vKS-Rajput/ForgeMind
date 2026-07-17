"""Graph API routes — knowledge graph data, stats, and timeline.

These routes expose the knowledge graph for visualization and querying.

Routes:
  GET /api/v1/graph/data     - Full graph as D3.js-compatible JSON.
  GET /api/v1/graph/stats    - Entity and relationship counts by type.
  GET /api/v1/graph/search   - Search entities by name.
"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Request

from forgemind.api.state import AppState
from forgemind.knowledge.domain.value_objects import EntityType
from forgemind.shared.logging import get_logger

logger = get_logger(__name__)

router = APIRouter(tags=["Knowledge Graph"])


# ── Helper ───────────────────────────────────────────────────────


def _get_state(request: Request) -> AppState:
    """Extract the AppState from the FastAPI request."""
    return request.app.state.forgemind  # type: ignore[no-any-return]


# ── Routes ───────────────────────────────────────────────────────


@router.get(
    "/graph/data",
    summary="Get the full knowledge graph for visualization",
    description=(
        "Returns the entire knowledge graph as a D3.js-compatible JSON "
        "structure with nodes and edges. Each node has an id, name, "
        "type, and group for color coding."
    ),
)
async def get_graph_data(request: Request) -> dict[str, Any]:
    """Get the full graph as D3.js-compatible JSON."""
    state = _get_state(request)
    return state.graph_repository.export_for_visualization()


@router.get(
    "/graph/stats",
    summary="Get knowledge graph statistics",
)
async def get_graph_stats(request: Request) -> dict[str, Any]:
    """Get entity and relationship counts, broken down by type."""
    state = _get_state(request)
    graph = state.graph_repository

    # Count entities by type
    entity_counts: dict[str, int] = {}
    for entity_type in EntityType:
        count = len(graph.query_by_type(entity_type))
        if count > 0:
            entity_counts[entity_type.value] = count

    return {
        "total_entities": graph.get_entity_count(),
        "total_relationships": graph.get_relationship_count(),
        "entities_by_type": entity_counts,
    }


@router.get(
    "/graph/search",
    summary="Search entities in the knowledge graph",
)
async def search_graph(request: Request, q: str) -> list[dict[str, Any]]:
    """Search entities by name (case-insensitive substring match)."""
    state = _get_state(request)
    matches = state.graph_repository.search_entities(q)

    return [
        {
            "id": str(entity.id),
            "name": entity.name,
            "type": entity.entity_type.value,
            "description": entity.description,
            "attributes": entity.attributes,
        }
        for entity in matches
    ]


@router.get(
    "/graph/timeline",
    summary="Knowledge evolution timeline",
    description=(
        "Returns the full chronological timeline of knowledge evolution events. "
        "Each event records what changed, when, and which document triggered it."
    ),
)
async def knowledge_timeline(request: Request) -> dict[str, Any]:
    """Get the full organizational learning timeline."""
    state = _get_state(request)
    events = state.knowledge_evolution.get_timeline()

    return {
        "total_events": len(events),
        "timeline": [
            {
                "event_type": event.event_type.value,
                "entity_name": event.entity_name,
                "old_confidence": event.old_confidence,
                "new_confidence": round(event.new_confidence, 4),
                "evidence_count": event.evidence_count,
                "source_document": event.source_document_title,
                "details": event.details,
                "timestamp": event.timestamp.isoformat(),
            }
            for event in events
        ],
    }
