"""Document API routes — upload, analyze, list, and inspect documents.

These routes expose the document ingestion pipeline via HTTP.
Users can upload PDF files, get AI-powered analysis, list all
ingested documents, and inspect the chunks produced.

Every uploaded document automatically:
  1. Gets parsed and chunked (existing pipeline).
  2. Gets analyzed for entities (equipment, parts, symptoms, etc.).
  3. Gets its entities normalized into typed KnowledgeEntity objects.
  4. Gets relationships extracted from chunk co-occurrence patterns.
  5. Gets merged into the organizational knowledge graph.
  6. Produces a KnowledgeEvent audit trail.

This is what transforms ForgeMind from "document search" into
"organizational memory that learns with every upload."

Routes:
  POST   /api/v1/documents/upload       - Upload and ingest a PDF file.
  POST   /api/v1/documents/text         - Ingest raw text directly.
  GET    /api/v1/documents              - List all ingested documents.
  GET    /api/v1/documents/stats        - Get system statistics.
  GET    /api/v1/documents/{id}         - Get a single document by ID.
  GET    /api/v1/documents/{id}/chunks  - Get all chunks for a document.
  GET    /api/v1/documents/{id}/analyze - Analyze a document for insights.
"""

from __future__ import annotations

import shutil
import tempfile
from pathlib import Path
from typing import Any

from fastapi import APIRouter, HTTPException, Request, UploadFile

# pyrefly: ignore [missing-import]
from pydantic import BaseModel

from forgemind.api.state import AppState
from forgemind.knowledge.adapters.analysis_service import DocumentAnalyzer
from forgemind.knowledge.adapters.entity_normalizer import SOURCE_RELIABILITY
from forgemind.knowledge.domain.value_objects import DocumentType
from forgemind.shared.errors import IngestionError, UnsupportedFormatError
from forgemind.shared.logging import get_logger
from forgemind.shared.types import DocumentId

logger = get_logger(__name__)

router = APIRouter(tags=["Documents"])

# ── Shared analyzer instance (stateless, thread-safe) ────────────
_analyzer = DocumentAnalyzer()


# ── Response Models ──────────────────────────────────────────────


class DocumentResponse(BaseModel):
    """API response for a single document."""

    id: str
    title: str
    source_path: str
    document_type: str
    content_hash: str
    page_count: int
    ingested_at: str


class ChunkResponse(BaseModel):
    """API response for a single chunk."""

    id: str
    document_id: str
    content: str
    chunk_index: int
    page_number: int | None
    char_start: int
    char_end: int


class KnowledgeGraphStats(BaseModel):
    """Statistics about what the upload contributed to the knowledge graph."""

    entities_created: int
    entities_updated: int
    relationships_created: int
    relationships_strengthened: int
    total_entities: int
    total_relationships: int


class KnowledgeEventResponse(BaseModel):
    """A single knowledge evolution event for the timeline."""

    event_type: str
    entity_name: str
    old_confidence: float | None
    new_confidence: float
    evidence_count: int
    details: str
    timestamp: str


class IngestionResponse(BaseModel):
    """API response after successful ingestion with analysis and graph stats."""

    message: str
    document_id: str
    title: str
    page_count: int
    chunk_count: int
    analysis: dict[str, Any]
    knowledge_graph: KnowledgeGraphStats
    knowledge_events: list[KnowledgeEventResponse]


class TextIngestionRequest(BaseModel):
    """Request body for direct text ingestion."""

    text: str
    title: str


class StatsResponse(BaseModel):
    """API response for system statistics."""

    total_documents: int
    total_chunks: int
    total_entities: int
    total_relationships: int


class AnalysisResponse(BaseModel):
    """API response for document analysis results."""

    document_id: str
    title: str
    equipment: list[str]
    parts: list[str]
    materials: list[str]
    instruments: list[str]
    parameters: list[str]
    symptoms: list[str]
    actions: list[str]
    key_sentences: list[str]
    summary_stats: dict[str, Any]


# ── Helper ───────────────────────────────────────────────────────


def _get_state(request: Request) -> AppState:
    """Extract the AppState from the FastAPI request."""
    return request.app.state.forgemind  # type: ignore[no-any-return]


def _detect_document_type(title: str, text: str) -> DocumentType:
    """Auto-detect document type from title and content keywords.

    This ensures the correct source reliability is applied, which
    directly affects confidence scores in the knowledge graph.

    Args:
        title: The document title (often the filename).
        text: The full document text.

    Returns:
        The detected DocumentType.
    """
    combined = (title + " " + text[:2000]).lower()

    if any(
        kw in combined for kw in ["manual", "maintenance manual", "operating manual", "procedure"]
    ):
        return DocumentType.MANUAL
    if any(kw in combined for kw in ["incident", "failure report", "root cause", "accident"]):
        return DocumentType.INCIDENT_REPORT
    if any(kw in combined for kw in ["work order", "service request", "repair order"]):
        return DocumentType.WORK_ORDER
    return DocumentType.UNKNOWN


def _build_analysis_dict(text: str) -> dict[str, Any]:
    """Run the analyzer on text and return a serializable dict.

    This is used by both the upload endpoint (immediate analysis)
    and the dedicated /analyze endpoint (on-demand analysis).
    """
    insights = _analyzer.analyze_text(text)
    return {
        "equipment": insights.equipment,
        "parts": insights.parts,
        "materials": insights.materials,
        "instruments": insights.instruments,
        "parameters": insights.parameters,
        "symptoms": insights.symptoms,
        "actions": insights.actions,
        "key_sentences": insights.key_sentences,
        "summary_stats": insights.summary_stats,
    }


def _build_knowledge_graph(
    state: AppState,
    full_text: str,
    document_id: str,
    document_title: str,
    document_type: DocumentType,
    chunk_texts: list[str],
) -> dict[str, Any]:
    """Run the full knowledge pipeline and return graph stats + events.

    This is the core of ForgeMind's organizational memory. It:
      1. Analyzes the text for raw entity strings.
      2. Normalizes strings into typed KnowledgeEntity objects.
      3. Extracts relationships from entity co-occurrence in chunks.
      4. Merges everything into the graph via the Evolution Engine.
      5. Returns statistics and the audit trail.

    Args:
        state: Application state with all adapters.
        full_text: The complete document text.
        document_id: The document's unique ID.
        document_title: The document's title.
        document_type: Classification of the source document.
        chunk_texts: List of individual chunk texts.

    Returns:
        Dictionary with 'knowledge_graph' stats and 'knowledge_events' list.
    """
    # Step 1: Analyze text for raw entity strings
    insights = _analyzer.analyze_text(full_text)

    # Step 2: Normalize raw strings → typed KnowledgeEntity objects
    entities = state.entity_normalizer.normalize(
        insights=insights,
        document_id=document_id,
        document_title=document_title,
        document_type=document_type,
    )

    # Step 3: Extract relationships from entities + chunks
    relationships = state.relationship_extractor.extract(
        entities=entities,
        chunk_texts=chunk_texts,
        document_id=document_id,
    )

    # Step 4: Merge into the knowledge graph via Evolution Engine
    reliability = SOURCE_RELIABILITY.get(document_type, 0.7)
    merge_result = state.knowledge_evolution.merge(
        new_entities=entities,
        new_relationships=relationships,
        graph=state.graph_repository,
        source_document_id=document_id,
        source_document_title=document_title,
        source_reliability=reliability,
    )

    # Step 5: Build response
    graph_stats = {
        "entities_created": merge_result.entities_created,
        "entities_updated": merge_result.entities_updated,
        "relationships_created": merge_result.relationships_created,
        "relationships_strengthened": merge_result.relationships_strengthened,
        "total_entities": state.graph_repository.get_entity_count(),
        "total_relationships": state.graph_repository.get_relationship_count(),
    }

    events = [
        {
            "event_type": event.event_type.value,
            "entity_name": event.entity_name,
            "old_confidence": event.old_confidence,
            "new_confidence": round(event.new_confidence, 4),
            "evidence_count": event.evidence_count,
            "details": event.details,
            "timestamp": event.timestamp.isoformat(),
        }
        for event in merge_result.events
    ]

    return {"knowledge_graph": graph_stats, "knowledge_events": events}


# ── Routes ───────────────────────────────────────────────────────


@router.post(
    "/documents/upload",
    response_model=IngestionResponse,
    status_code=201,
    summary="Upload and ingest a PDF document",
    description=(
        "Upload a PDF file to run it through the full intelligence pipeline. "
        "The file is parsed, chunked, analyzed, and automatically merged "
        "into the organizational knowledge graph. Every upload evolves "
        "ForgeMind's understanding of your assets, failures, and procedures."
    ),
)
async def upload_document(request: Request, file: UploadFile) -> dict[str, Any]:
    """Upload a PDF file and run it through the full intelligence pipeline."""
    state = _get_state(request)

    if not file.filename:
        raise HTTPException(status_code=400, detail="No file provided.")

    logger.info(
        "api_upload_received",
        filename=file.filename,
        content_type=file.content_type,
    )

    # Save uploaded file to a temp location for pdfplumber
    temp_dir = tempfile.mkdtemp(prefix="forgemind_upload_")
    temp_path = Path(temp_dir) / file.filename

    try:
        with open(temp_path, "wb") as temp_file:
            shutil.copyfileobj(file.file, temp_file)

        # Phase 1: Ingest (parse + chunk + store)
        result = state.ingestion_service.ingest_document(str(temp_path))

        # Phase 2: Analyze (pattern extraction)
        chunk_texts = [chunk.content for chunk in result.chunks]
        full_text = " ".join(chunk_texts)
        analysis = _build_analysis_dict(full_text)

        # Phase 3: Build Knowledge Graph (normalize + extract + evolve)
        detected_type = _detect_document_type(result.document.title, full_text)
        knowledge = _build_knowledge_graph(
            state=state,
            full_text=full_text,
            document_id=str(result.document.id),
            document_title=result.document.title,
            document_type=detected_type,
            chunk_texts=chunk_texts,
        )

        return {
            "message": f"Successfully ingested '{result.document.title}'",
            "document_id": str(result.document.id),
            "title": result.document.title,
            "page_count": result.document.page_count,
            "chunk_count": len(result.chunks),
            "analysis": analysis,
            **knowledge,
        }

    except UnsupportedFormatError as error:
        raise HTTPException(status_code=400, detail=str(error.message)) from error
    except IngestionError as error:
        raise HTTPException(status_code=400, detail=str(error.message)) from error
    except Exception as error:
        logger.error(
            "api_upload_failed",
            filename=file.filename,
            error=str(error),
        )
        raise HTTPException(
            status_code=422,
            detail=f"Failed to process file: {error}",
        ) from error
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)


@router.post(
    "/documents/text",
    response_model=IngestionResponse,
    status_code=201,
    summary="Ingest raw text content",
    description="Paste raw text to ingest it directly without uploading a file.",
)
async def ingest_text(request: Request, body: TextIngestionRequest) -> dict[str, Any]:
    """Ingest raw text content with automatic analysis and knowledge graph update."""
    state = _get_state(request)

    try:
        result = state.ingestion_service.ingest_text(
            text=body.text,
            title=body.title,
        )

        chunk_texts = [chunk.content for chunk in result.chunks]
        full_text = " ".join(chunk_texts)
        analysis = _build_analysis_dict(full_text)

        knowledge = _build_knowledge_graph(
            state=state,
            full_text=full_text,
            document_id=str(result.document.id),
            document_title=result.document.title,
            document_type=_detect_document_type(result.document.title, full_text),
            chunk_texts=chunk_texts,
        )

        return {
            "message": f"Successfully ingested '{result.document.title}'",
            "document_id": str(result.document.id),
            "title": result.document.title,
            "page_count": result.document.page_count,
            "chunk_count": len(result.chunks),
            "analysis": analysis,
            **knowledge,
        }

    except IngestionError as error:
        raise HTTPException(status_code=400, detail=str(error.message)) from error
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error


@router.get(
    "/documents",
    response_model=list[DocumentResponse],
    summary="List all ingested documents",
)
async def list_documents(request: Request) -> list[dict[str, Any]]:
    """List all documents that have been ingested, newest first."""
    state = _get_state(request)
    documents = state.document_repository.list_all()

    return [
        {
            "id": str(doc.id),
            "title": doc.title,
            "source_path": doc.source_path,
            "document_type": doc.document_type.value,
            "content_hash": doc.content_hash[:16] + "...",
            "page_count": doc.page_count,
            "ingested_at": doc.ingested_at.isoformat(),
        }
        for doc in documents
    ]


@router.get(
    "/documents/stats",
    response_model=StatsResponse,
    summary="Get system statistics",
)
async def get_stats(request: Request) -> dict[str, int]:
    """Get aggregate statistics about the system."""
    state = _get_state(request)
    return {
        "total_documents": state.document_repository.count(),
        "total_chunks": state.chunk_repository.count(),
        "total_entities": state.graph_repository.get_entity_count(),
        "total_relationships": state.graph_repository.get_relationship_count(),
    }


@router.get(
    "/documents/{document_id}",
    response_model=DocumentResponse,
    summary="Get a document by ID",
)
async def get_document(request: Request, document_id: str) -> dict[str, Any]:
    """Get a single document by its unique ID."""
    state = _get_state(request)
    document = state.document_repository.get(DocumentId(document_id))

    if document is None:
        raise HTTPException(
            status_code=404,
            detail=f"Document with ID '{document_id}' not found.",
        )

    return {
        "id": str(document.id),
        "title": document.title,
        "source_path": document.source_path,
        "document_type": document.document_type.value,
        "content_hash": document.content_hash[:16] + "...",
        "page_count": document.page_count,
        "ingested_at": document.ingested_at.isoformat(),
    }


@router.get(
    "/documents/{document_id}/chunks",
    response_model=list[ChunkResponse],
    summary="Get all chunks for a document",
)
async def get_document_chunks(request: Request, document_id: str) -> list[dict[str, Any]]:
    """Get all chunks belonging to a document, sorted by index."""
    state = _get_state(request)

    document = state.document_repository.get(DocumentId(document_id))
    if document is None:
        raise HTTPException(
            status_code=404,
            detail=f"Document with ID '{document_id}' not found.",
        )

    chunks = state.chunk_repository.get_chunks_for_document(DocumentId(document_id))

    return [
        {
            "id": str(chunk.id),
            "document_id": str(chunk.document_id),
            "content": chunk.content,
            "chunk_index": chunk.chunk_index,
            "page_number": chunk.metadata.page_number if chunk.metadata else None,
            "char_start": chunk.metadata.char_start if chunk.metadata else 0,
            "char_end": chunk.metadata.char_end if chunk.metadata else 0,
        }
        for chunk in chunks
    ]


@router.get(
    "/documents/{document_id}/analyze",
    response_model=AnalysisResponse,
    summary="Analyze a document for insights",
    description=(
        "Extract structured insights from an ingested document: "
        "equipment names, part numbers, operating parameters, "
        "failure symptoms, corrective actions, and key sentences. "
        "Analysis is pattern-based and runs entirely offline."
    ),
)
async def analyze_document(request: Request, document_id: str) -> dict[str, Any]:
    """Analyze a document and return extracted insights."""
    state = _get_state(request)

    document = state.document_repository.get(DocumentId(document_id))
    if document is None:
        raise HTTPException(
            status_code=404,
            detail=f"Document with ID '{document_id}' not found.",
        )

    chunks = state.chunk_repository.get_chunks_for_document(DocumentId(document_id))
    if not chunks:
        raise HTTPException(
            status_code=404,
            detail=f"No chunks found for document '{document_id}'.",
        )

    full_text = " ".join(chunk.content for chunk in chunks)
    analysis = _build_analysis_dict(full_text)

    return {
        "document_id": str(document.id),
        "title": document.title,
        **analysis,
    }
