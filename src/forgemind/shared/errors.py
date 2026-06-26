"""ForgeMind error hierarchy.

All custom exceptions inherit from ForgeMindError. This allows callers
to catch domain errors separately from unexpected system errors.

Every exception carries:
- message: Human-readable description
- code: Machine-readable error code (for API responses)
- context: Optional dict with debug data (logged, not exposed to users)

Bounded Context: Shared
Layer: Error Definitions
Dependencies: None
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class ForgeMindError(Exception):
    """Base exception for all ForgeMind domain errors.

    Args:
        message: Human-readable error description.
        code: Machine-readable error code (e.g., "INGESTION_PARSE_FAILED").
        context: Optional debug context (key-value pairs for structured logging).
    """

    message: str
    code: str = "FORGEMIND_ERROR"
    context: dict[str, object] = field(default_factory=dict)

    def __str__(self) -> str:
        """Return human-readable error message."""
        return f"[{self.code}] {self.message}"


# ── Ingestion Errors ─────────────────────────────────────────────


@dataclass(frozen=True)
class IngestionError(ForgeMindError):
    """Base error for document ingestion failures."""

    code: str = "INGESTION_ERROR"


@dataclass(frozen=True)
class DocumentParseError(IngestionError):
    """Failed to parse a document (e.g., corrupted PDF)."""

    code: str = "INGESTION_PARSE_FAILED"


@dataclass(frozen=True)
class ChunkingError(IngestionError):
    """Failed to chunk a document into segments."""

    code: str = "INGESTION_CHUNKING_FAILED"


@dataclass(frozen=True)
class UnsupportedFormatError(IngestionError):
    """Document format is not supported."""

    code: str = "INGESTION_UNSUPPORTED_FORMAT"


# ── Extraction Errors ────────────────────────────────────────────


@dataclass(frozen=True)
class ExtractionError(ForgeMindError):
    """Base error for entity/relationship extraction failures."""

    code: str = "EXTRACTION_ERROR"


@dataclass(frozen=True)
class EntityExtractionError(ExtractionError):
    """Failed to extract entities from text."""

    code: str = "EXTRACTION_ENTITY_FAILED"


@dataclass(frozen=True)
class RelationshipExtractionError(ExtractionError):
    """Failed to extract relationships between entities."""

    code: str = "EXTRACTION_RELATIONSHIP_FAILED"


# ── Graph Errors ─────────────────────────────────────────────────


@dataclass(frozen=True)
class GraphError(ForgeMindError):
    """Base error for knowledge graph operations."""

    code: str = "GRAPH_ERROR"


@dataclass(frozen=True)
class GraphConstructionError(GraphError):
    """Failed to construct or update the knowledge graph."""

    code: str = "GRAPH_CONSTRUCTION_FAILED"


@dataclass(frozen=True)
class GraphQueryError(GraphError):
    """Failed to query the knowledge graph."""

    code: str = "GRAPH_QUERY_FAILED"


@dataclass(frozen=True)
class EntityNotFoundError(GraphError):
    """Requested entity does not exist in the knowledge graph."""

    code: str = "GRAPH_ENTITY_NOT_FOUND"


# ── Retrieval Errors ─────────────────────────────────────────────


@dataclass(frozen=True)
class RetrievalError(ForgeMindError):
    """Base error for hybrid retrieval failures."""

    code: str = "RETRIEVAL_ERROR"


@dataclass(frozen=True)
class VectorSearchError(RetrievalError):
    """Failed to perform vector similarity search."""

    code: str = "RETRIEVAL_VECTOR_SEARCH_FAILED"


@dataclass(frozen=True)
class EmbeddingError(RetrievalError):
    """Failed to generate embeddings for text."""

    code: str = "RETRIEVAL_EMBEDDING_FAILED"


# ── Reasoning Errors ─────────────────────────────────────────────


@dataclass(frozen=True)
class ReasoningError(ForgeMindError):
    """Base error for LLM reasoning failures."""

    code: str = "REASONING_ERROR"


@dataclass(frozen=True)
class LLMProviderError(ReasoningError):
    """LLM provider (OpenAI, Ollama) returned an error or is unreachable."""

    code: str = "REASONING_LLM_PROVIDER_FAILED"


@dataclass(frozen=True)
class PromptConstructionError(ReasoningError):
    """Failed to construct the LLM prompt."""

    code: str = "REASONING_PROMPT_CONSTRUCTION_FAILED"


@dataclass(frozen=True)
class ResponseParseError(ReasoningError):
    """Failed to parse the LLM response into structured output."""

    code: str = "REASONING_RESPONSE_PARSE_FAILED"


# ── Configuration Errors ─────────────────────────────────────────


@dataclass(frozen=True)
class ConfigurationError(ForgeMindError):
    """Invalid or missing configuration."""

    code: str = "CONFIGURATION_ERROR"
