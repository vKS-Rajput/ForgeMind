"""Knowledge domain value objects.

Immutable, identity-less types that define the vocabulary of the
Knowledge bounded context. Compared by value, not by reference.

Bounded Context: Knowledge
Layer: Domain (Value Objects)
Dependencies: None (pure Python + shared types)
"""

from __future__ import annotations

import enum
from dataclasses import dataclass, field
from datetime import UTC, datetime

# ── Entity Type Taxonomy ─────────────────────────────────────────


class EntityType(enum.Enum):
    """Classification of knowledge entities extracted from documents.

    Each type corresponds to a distinct concept in the industrial
    maintenance domain. New types may be added as the domain grows.
    """

    ASSET = "asset"
    """A physical piece of equipment (e.g., Pump P-101, Compressor C-201)."""

    COMPONENT = "component"
    """A sub-part of an asset (e.g., bearing, seal, impeller, coupling)."""

    FAILURE_MODE = "failure_mode"
    """A way in which equipment can fail (e.g., overheating, cavitation)."""

    SYMPTOM = "symptom"
    """An observable sign of a problem (e.g., excessive vibration, high temperature)."""

    ACTION = "action"
    """A maintenance or corrective action (e.g., replaced bearing, realigned coupling)."""

    CONDITION = "condition"
    """An operating condition or parameter (e.g., flow rate, pressure, temperature)."""

    LOCATION = "location"
    """A physical location within a facility (e.g., Production Line 1, Unit 3)."""

    PART = "part"
    """A replacement part or consumable (e.g., SKF 6205 bearing, O-ring seal)."""


# ── Relationship Type Taxonomy ───────────────────────────────────


class RelationType(enum.Enum):
    """Classification of relationships between knowledge entities.

    Relationships are directed: source → relation → target.
    Inverse relationships are provided for bidirectional traversal.
    """

    CAUSES = "causes"
    """Source entity causes the target entity (e.g., misalignment causes vibration)."""

    CAUSED_BY = "caused_by"
    """Source entity is caused by the target entity (inverse of CAUSES)."""

    HAS_COMPONENT = "has_component"
    """Source asset has the target as a component (e.g., Pump has Bearing)."""

    COMPONENT_OF = "component_of"
    """Source component belongs to the target asset (inverse of HAS_COMPONENT)."""

    RESOLVED_BY = "resolved_by"
    """Source failure/symptom was resolved by the target action."""

    RESOLVES = "resolves"
    """Source action resolves the target failure/symptom (inverse of RESOLVED_BY)."""

    SYMPTOMS_OF = "symptoms_of"
    """Source symptom is a symptom of the target failure mode."""

    HAS_SYMPTOM = "has_symptom"
    """Source failure mode has the target as a symptom (inverse of SYMPTOMS_OF)."""

    LOCATED_AT = "located_at"
    """Source entity is located at the target location."""

    RELATED_TO = "related_to"
    """General association between entities when specific type is unknown."""


# ── Inverse Relationship Mapping ─────────────────────────────────

INVERSE_RELATIONS: dict[RelationType, RelationType] = {
    RelationType.CAUSES: RelationType.CAUSED_BY,
    RelationType.CAUSED_BY: RelationType.CAUSES,
    RelationType.HAS_COMPONENT: RelationType.COMPONENT_OF,
    RelationType.COMPONENT_OF: RelationType.HAS_COMPONENT,
    RelationType.RESOLVED_BY: RelationType.RESOLVES,
    RelationType.RESOLVES: RelationType.RESOLVED_BY,
    RelationType.SYMPTOMS_OF: RelationType.HAS_SYMPTOM,
    RelationType.HAS_SYMPTOM: RelationType.SYMPTOMS_OF,
    RelationType.LOCATED_AT: RelationType.LOCATED_AT,
    RelationType.RELATED_TO: RelationType.RELATED_TO,
}


# ── Document Classification ──────────────────────────────────────


class DocumentType(enum.Enum):
    """Classification of source documents."""

    MANUAL = "manual"
    """Equipment maintenance or operating manual."""

    INCIDENT_REPORT = "incident_report"
    """Record of a failure, incident, or abnormal event."""

    WORK_ORDER = "work_order"
    """Maintenance work order or service request."""

    UNKNOWN = "unknown"
    """Document type could not be determined."""


# ── Severity Levels ──────────────────────────────────────────────


class Severity(enum.Enum):
    """Severity classification for incidents and failures."""

    CRITICAL = "critical"
    """System failure, safety risk, or production shutdown."""

    HIGH = "high"
    """Significant impact, immediate attention required."""

    MEDIUM = "medium"
    """Moderate impact, resolution needed within days."""

    LOW = "low"
    """Minor impact, can be scheduled for routine maintenance."""

    INFO = "info"
    """Informational, no immediate action required."""


# ── Provenance ───────────────────────────────────────────────────


@dataclass(frozen=True, slots=True)
class Provenance:
    """Tracks where a piece of knowledge came from.

    Every extracted entity and relationship carries provenance
    so that answers can be traced back to source documents.

    Args:
        source_document_id: ID of the document this knowledge was extracted from.
        chunk_ids: IDs of the specific chunks that contributed to this extraction.
        extraction_method: How the extraction was performed (e.g., "rule_based", "llm").
        extracted_at: When the extraction occurred.
        confidence: Confidence score in [0.0, 1.0].
    """

    source_document_id: str
    chunk_ids: tuple[str, ...] = ()
    extraction_method: str = "unknown"
    extracted_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    confidence: float = 0.5

    def __post_init__(self) -> None:
        """Validate confidence is within bounds."""
        if not 0.0 <= self.confidence <= 1.0:
            msg = f"Confidence must be in [0.0, 1.0], got {self.confidence}"
            raise ValueError(msg)


# ── Chunk Metadata ───────────────────────────────────────────────


@dataclass(frozen=True, slots=True)
class ChunkMetadata:
    """Positional and structural metadata for a document chunk.

    Args:
        page_number: The page this chunk appears on (1-indexed, None if unknown).
        position_in_document: Sequential position of this chunk (0-indexed).
        char_start: Character offset where this chunk starts in the full text.
        char_end: Character offset where this chunk ends in the full text.
    """

    page_number: int | None = None
    position_in_document: int = 0
    char_start: int = 0
    char_end: int = 0
