"""Application state — holds all wired-up adapters for dependency injection.

This module is the composition root for ForgeMind's adapter layer.
It creates concrete adapter instances and wires them together so that
FastAPI routes can access them via `request.app.state.forgemind`.

Why a separate module?
  - Keeps the app factory (app.py) clean and focused on FastAPI config.
  - Makes it easy to swap adapters (e.g., in-memory -> PostgreSQL) by
    changing only this file.
  - Testable: tests can create their own AppState with mock adapters.
"""

from __future__ import annotations

from dataclasses import dataclass

from forgemind.graph.adapters.networkx_repository import NetworkXGraphRepository
from forgemind.knowledge.adapters.entity_normalizer import EntityNormalizer
from forgemind.knowledge.adapters.ingestion_service import (
    IngestionApplicationService,
)
from forgemind.knowledge.adapters.knowledge_evolution import (
    KnowledgeEvolutionEngine,
)
from forgemind.knowledge.adapters.memory_chunk_repository import (
    InMemoryChunkRepository,
)
from forgemind.knowledge.adapters.memory_document_repository import (
    InMemoryDocumentRepository,
)
from forgemind.knowledge.adapters.pdf_parser import PdfDocumentParser
from forgemind.knowledge.adapters.relationship_extractor import (
    RelationshipExtractor,
)


@dataclass
class AppState:
    """Holds all application-level adapter instances.

    This object is stored in FastAPI's app.state and accessed by
    route handlers via dependency injection.

    Attributes:
        parser: The document parser (currently PDF-only).
        document_repository: Where Document entities are stored.
        chunk_repository: Where Chunk entities are stored.
        ingestion_service: The pipeline orchestrator.
        graph_repository: The knowledge graph (NetworkX).
        entity_normalizer: Converts raw strings to typed entities.
        relationship_extractor: Discovers edges from entities + chunks.
        knowledge_evolution: Merges new knowledge into the graph.
    """

    parser: PdfDocumentParser
    document_repository: InMemoryDocumentRepository
    chunk_repository: InMemoryChunkRepository
    ingestion_service: IngestionApplicationService
    graph_repository: NetworkXGraphRepository
    entity_normalizer: EntityNormalizer
    relationship_extractor: RelationshipExtractor
    knowledge_evolution: KnowledgeEvolutionEngine


def create_app_state() -> AppState:
    """Create the application state with all adapters wired up.

    This is where dependency injection happens. Each adapter is
    created once and shared across all requests.

    Returns:
        A fully wired AppState ready for use.
    """
    parser = PdfDocumentParser()
    document_repository = InMemoryDocumentRepository()
    chunk_repository = InMemoryChunkRepository()

    ingestion_service = IngestionApplicationService(
        parser=parser,
        document_repository=document_repository,
        chunk_repository=chunk_repository,
    )

    graph_repository = NetworkXGraphRepository()
    entity_normalizer = EntityNormalizer()
    relationship_extractor = RelationshipExtractor()
    knowledge_evolution = KnowledgeEvolutionEngine()

    return AppState(
        parser=parser,
        document_repository=document_repository,
        chunk_repository=chunk_repository,
        ingestion_service=ingestion_service,
        graph_repository=graph_repository,
        entity_normalizer=entity_normalizer,
        relationship_extractor=relationship_extractor,
        knowledge_evolution=knowledge_evolution,
    )
