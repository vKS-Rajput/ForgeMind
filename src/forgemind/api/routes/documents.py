"""Document API routes — upload, list, and inspect documents.

These routes expose the document ingestion pipeline via HTTP.
Users can upload PDF files, list all ingested documents, and
inspect the chunks produced from any document.

Routes:
  POST   /api/v1/documents/upload    — Upload and ingest a PDF file.
  POST   /api/v1/documents/text      — Ingest raw text directly.
  GET    /api/v1/documents           — List all ingested documents.
  GET    /api/v1/documents/{id}      — Get a single document by ID.
  GET    /api/v1/documents/{id}/chunks — Get all chunks for a document.
"""

from __future__ import annotations

import shutil
import tempfile
from pathlib import Path
from typing import Any

from fastapi import APIRouter, HTTPException, Request, UploadFile
from pydantic import BaseModel

from forgemind.api.state import AppState
from forgemind.shared.errors import IngestionError, UnsupportedFormatError
from forgemind.shared.logging import get_logger

logger = get_logger(__name__)

router = APIRouter(tags=["Documents"])


# ── Response Models ──────────────────────────────────────────────
# Pydantic models for API responses. These control what the API
# returns to the client and provide automatic OpenAPI documentation.


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


class IngestionResponse(BaseModel):
    """API response after successful ingestion."""

    message: str
    document_id: str
    title: str
    page_count: int
    chunk_count: int


class TextIngestionRequest(BaseModel):
    """Request body for direct text ingestion."""

    text: str
    title: str


class StatsResponse(BaseModel):
    """API response for system statistics."""

    total_documents: int
    total_chunks: int


# ── Helper ───────────────────────────────────────────────────────


def _get_state(request: Request) -> AppState:
    """Extract the AppState from the FastAPI request.

    This is how routes access the wired-up adapters. The AppState
    is set during application startup in the lifespan handler.
    """
    return request.app.state.forgemind  # type: ignore[no-any-return]


# ── Routes ───────────────────────────────────────────────────────


@router.post(
    "/documents/upload",
    response_model=IngestionResponse,
    status_code=201,
    summary="Upload and ingest a PDF document",
)
async def upload_document(request: Request, file: UploadFile) -> dict[str, Any]:
    """Upload a PDF file and run it through the ingestion pipeline.

    The file is saved to a temporary location, parsed with pdfplumber,
    chunked at sentence boundaries, and stored in the repositories.

    Args:
        request: The FastAPI request (provides access to app state).
        file: The uploaded PDF file.

    Returns:
        Ingestion result with document ID, title, and chunk count.

    Raises:
        400: If the file format is not supported or content is duplicate.
        422: If the file is corrupt or cannot be parsed.
    """
    state = _get_state(request)

    # Validate the file was actually uploaded
    if not file.filename:
        raise HTTPException(status_code=400, detail="No file provided.")

    logger.info(
        "api_upload_received",
        filename=file.filename,
        content_type=file.content_type,
    )

    # Save the uploaded file to a temporary location so pdfplumber
    # can read it from disk (pdfplumber requires a file path).
    temp_dir = tempfile.mkdtemp(prefix="forgemind_upload_")
    temp_path = Path(temp_dir) / file.filename

    try:
        # Write the uploaded bytes to the temp file
        with open(temp_path, "wb") as temp_file:
            shutil.copyfileobj(file.file, temp_file)

        # Run the full ingestion pipeline
        result = state.ingestion_service.ingest_document(str(temp_path))

        return {
            "message": f"Successfully ingested '{result.document.title}'",
            "document_id": str(result.document.id),
            "title": result.document.title,
            "page_count": result.document.page_count,
            "chunk_count": len(result.chunks),
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
        # Clean up the temporary file
        shutil.rmtree(temp_dir, ignore_errors=True)


@router.post(
    "/documents/text",
    response_model=IngestionResponse,
    status_code=201,
    summary="Ingest raw text content",
)
async def ingest_text(request: Request, body: TextIngestionRequest) -> dict[str, Any]:
    """Ingest raw text content directly, without uploading a file.

    Useful for pasting text from manuals, reports, or other sources.
    """
    state = _get_state(request)

    try:
        result = state.ingestion_service.ingest_text(
            text=body.text,
            title=body.title,
        )

        return {
            "message": f"Successfully ingested '{result.document.title}'",
            "document_id": str(result.document.id),
            "title": result.document.title,
            "page_count": result.document.page_count,
            "chunk_count": len(result.chunks),
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
    """Get aggregate statistics about the ingested documents."""
    state = _get_state(request)
    return {
        "total_documents": state.document_repository.count(),
        "total_chunks": state.chunk_repository.count(),
    }


@router.get(
    "/documents/{document_id}",
    response_model=DocumentResponse,
    summary="Get a document by ID",
)
async def get_document(request: Request, document_id: str) -> dict[str, Any]:
    """Get a single document by its unique ID."""
    state = _get_state(request)
    document = state.document_repository.get(document_id)

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
    """Get all chunks belonging to a document, sorted by index.

    This shows exactly how the document was split into chunks,
    including the page number and character offsets for each chunk.
    """
    state = _get_state(request)

    # Verify the document exists first
    document = state.document_repository.get(document_id)
    if document is None:
        raise HTTPException(
            status_code=404,
            detail=f"Document with ID '{document_id}' not found.",
        )

    chunks = state.chunk_repository.get_chunks_for_document(document_id)

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
