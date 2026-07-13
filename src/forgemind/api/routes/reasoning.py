"""Reasoning API route -- explainable intelligence endpoint.

This route exposes the graph-based reasoning engine via HTTP.
Users can ask questions and get structured, explainable answers
backed by knowledge graph evidence.

Routes:
  POST /api/v1/reason  -- Ask a question, get a structured answer.
"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Request
from pydantic import BaseModel

from forgemind.api.state import AppState
from forgemind.reasoning.reasoning_service import ReasoningService
from forgemind.shared.logging import get_logger

logger = get_logger(__name__)

router = APIRouter(tags=["Reasoning"])

# ── Shared service instance (stateless, thread-safe) ─────────────
_reasoning = ReasoningService()


# ── Request/Response Models ──────────────────────────────────────


class ReasoningRequest(BaseModel):
    """Request body for reasoning queries."""

    query: str


class EvidenceLinkResponse(BaseModel):
    """A single evidence link in the reasoning chain."""

    source_name: str
    source_type: str
    relation: str
    target_name: str
    target_type: str
    confidence: float
    sentence: str


class ReasoningStepResponse(BaseModel):
    """One step in the reasoning chain."""

    step_number: int
    description: str
    evidence: list[EvidenceLinkResponse]
    entities_found: int


class ReasoningResponse(BaseModel):
    """Full reasoning output with evidence chain."""

    query: str
    entity_name: str
    entity_type: str
    timestamp: str
    observations: list[str]
    reasoning_chain: list[ReasoningStepResponse]
    possible_causes: list[dict[str, Any]]
    recommendations: list[dict[str, Any]]
    confidence: float
    confidence_explanation: str
    graph_traversals: int
    evidence_count: int


# ── Helper ───────────────────────────────────────────────────────


def _get_state(request: Request) -> AppState:
    """Extract the AppState from the FastAPI request."""
    return request.app.state.forgemind  # type: ignore[no-any-return]


# ── Routes ───────────────────────────────────────────────────────


@router.post(
    "/reason",
    response_model=ReasoningResponse,
    summary="Ask a question and get an explainable answer",
    description=(
        "Submit a natural language question about your assets, "
        "components, or maintenance procedures. ForgeMind traverses "
        "the knowledge graph to produce a structured answer with "
        "full evidence chains, possible causes, and recommended actions. "
        "All reasoning is deterministic and auditable — no LLM required."
    ),
)
async def reason(request: Request, body: ReasoningRequest) -> dict[str, Any]:
    """Answer a question using graph-based reasoning."""
    state = _get_state(request)

    result = _reasoning.reason(
        query=body.query,
        graph=state.graph_repository,
    )

    # Serialize the reasoning chain
    chain = []
    for step in result.reasoning_chain:
        chain.append(
            {
                "step_number": step.step_number,
                "description": step.description,
                "evidence": [
                    {
                        "source_name": e.source_name,
                        "source_type": e.source_type,
                        "relation": e.relation,
                        "target_name": e.target_name,
                        "target_type": e.target_type,
                        "confidence": round(e.confidence, 4),
                        "sentence": e.as_sentence(),
                    }
                    for e in step.evidence
                ],
                "entities_found": step.entities_found,
            }
        )

    return {
        "query": result.query,
        "entity_name": result.entity_name,
        "entity_type": result.entity_type,
        "timestamp": result.timestamp,
        "observations": result.observations,
        "reasoning_chain": chain,
        "possible_causes": result.possible_causes,
        "recommendations": result.recommendations,
        "confidence": round(result.confidence, 4),
        "confidence_explanation": result.confidence_explanation,
        "graph_traversals": result.graph_traversals,
        "evidence_count": result.evidence_count,
    }
