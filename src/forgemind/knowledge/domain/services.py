"""Knowledge domain services.

Pure business logic for text processing and entity management.
No I/O, no framework imports, no side effects. All functions
are deterministic given the same inputs.

Bounded Context: Knowledge
Layer: Domain (Services)
Dependencies: knowledge.domain.entities, knowledge.domain.value_objects
"""

from __future__ import annotations

import re

from forgemind.knowledge.domain.entities import KnowledgeEntity
from forgemind.knowledge.domain.value_objects import (
    EntityType,
    RelationType,
)

# ── Text Chunking ────────────────────────────────────────────────

# Simple sentence-ending pattern: period/question/exclamation followed by
# whitespace and an uppercase letter (or end of string).
_SENTENCE_BOUNDARY = re.compile(r"(?<=[.!?])\s+(?=[A-Z])")


def chunk_text(
    text: str,
    max_chunk_size: int = 500,
    overlap_size: int = 50,
) -> list[str]:
    """Split text into chunks at sentence boundaries with overlap.

    Splits at sentence boundaries, accumulating sentences until the
    chunk reaches max_chunk_size characters. Adjacent chunks overlap
    by overlap_size characters to preserve context at boundaries.

    Args:
        text: The source text to chunk. Must not be empty.
        max_chunk_size: Maximum characters per chunk. Must be > 0.
        overlap_size: Characters of overlap between adjacent chunks.
            Must be >= 0 and < max_chunk_size.

    Returns:
        A list of chunk content strings. Never empty if text is non-empty.

    Raises:
        ValueError: If text is empty, max_chunk_size <= 0,
            or overlap_size >= max_chunk_size.
    """
    if not text.strip():
        msg = "Text must not be empty"
        raise ValueError(msg)
    if max_chunk_size <= 0:
        msg = f"max_chunk_size must be > 0, got {max_chunk_size}"
        raise ValueError(msg)
    if overlap_size < 0:
        msg = f"overlap_size must be >= 0, got {overlap_size}"
        raise ValueError(msg)
    if overlap_size >= max_chunk_size:
        msg = f"overlap_size ({overlap_size}) must be < max_chunk_size ({max_chunk_size})"
        raise ValueError(msg)

    # Split into sentences
    sentences = _SENTENCE_BOUNDARY.split(text.strip())
    sentences = [s.strip() for s in sentences if s.strip()]

    if not sentences:
        return [text.strip()]

    # If the whole text fits in one chunk, return it as-is
    if len(text.strip()) <= max_chunk_size:
        return [text.strip()]

    chunks: list[str] = []
    current_chunk: list[str] = []
    current_length = 0

    for sentence in sentences:
        sentence_length = len(sentence)

        # If a single sentence exceeds max_chunk_size, include it as its own chunk
        if sentence_length > max_chunk_size:
            if current_chunk:
                chunks.append(" ".join(current_chunk))
                current_chunk = []
                current_length = 0
            chunks.append(sentence)
            continue

        # If adding this sentence would exceed the limit, finalize current chunk
        if current_length + sentence_length + (1 if current_chunk else 0) > max_chunk_size:
            chunks.append(" ".join(current_chunk))

            # Start new chunk with overlap from previous sentences
            overlap_sentences = _build_overlap(current_chunk, overlap_size)
            current_chunk = [*overlap_sentences, sentence]
            current_length = sum(len(s) for s in current_chunk) + len(current_chunk) - 1
        else:
            current_chunk.append(sentence)
            current_length += sentence_length + (1 if len(current_chunk) > 1 else 0)

    # Don't forget the last chunk
    if current_chunk:
        chunks.append(" ".join(current_chunk))

    return chunks


def _build_overlap(sentences: list[str], overlap_size: int) -> list[str]:
    """Select trailing sentences from a chunk to create overlap.

    Args:
        sentences: The sentences of the current chunk.
        overlap_size: Target overlap in characters.

    Returns:
        A list of sentences that fit within the overlap budget.
    """
    if overlap_size == 0:
        return []

    overlap: list[str] = []
    total = 0
    for sentence in reversed(sentences):
        if total + len(sentence) > overlap_size:
            break
        overlap.insert(0, sentence)
        total += len(sentence)
    return overlap


# ── Entity Name Normalization ────────────────────────────────────


def normalize_entity_name(name: str) -> str:
    """Normalize an entity name to a canonical form for deduplication.

    Lowercases, strips whitespace, replaces non-alphanumeric characters
    with underscores, and collapses consecutive underscores.

    Args:
        name: The raw entity name.

    Returns:
        The canonical normalized name.

    Raises:
        ValueError: If name is empty or becomes empty after normalization.

    Examples:
        >>> normalize_entity_name("Pump P-101")
        'pump_p_101'
        >>> normalize_entity_name("  bearing FAILURE  ")
        'bearing_failure'
        >>> normalize_entity_name("SKF-6205 Bearing")
        'skf_6205_bearing'
    """
    if not name.strip():
        msg = "Entity name must not be empty"
        raise ValueError(msg)

    canonical = name.lower().strip()
    canonical = re.sub(r"[^a-z0-9]+", "_", canonical)
    canonical = canonical.strip("_")

    if not canonical:
        msg = f"Entity name '{name}' normalizes to empty string"
        raise ValueError(msg)

    return canonical


# ── Entity Merging / Deduplication ───────────────────────────────


def merge_entities(entities: list[KnowledgeEntity]) -> list[KnowledgeEntity]:
    """Deduplicate entities by canonical name and entity type.

    When duplicates are found (same canonical_name + entity_type):
    - Keep the entity with the highest confidence provenance.
    - If confidences are equal, keep the first encountered.

    This is a pure domain operation — no persistence side effects.

    Args:
        entities: List of entities, potentially with duplicates.

    Returns:
        Deduplicated list of entities, preserving order of first occurrence.
    """
    if not entities:
        return []

    seen: dict[tuple[str, EntityType], KnowledgeEntity] = {}

    for entity in entities:
        key = (entity.canonical_name, entity.entity_type)
        existing = seen.get(key)

        if existing is None:
            seen[key] = entity
        else:
            # Keep the one with higher confidence
            existing_conf = existing.provenance.confidence if existing.provenance else 0.0
            new_conf = entity.provenance.confidence if entity.provenance else 0.0
            if new_conf > existing_conf:
                seen[key] = entity

    return list(seen.values())


# ── Relationship Validation ──────────────────────────────────────

# Valid (source_type, relation_type, target_type) combinations.
# This constrains the graph schema to meaningful relationships.
VALID_RELATIONSHIP_PATTERNS: set[tuple[EntityType, RelationType, EntityType]] = {
    # Asset relationships
    (EntityType.ASSET, RelationType.HAS_COMPONENT, EntityType.COMPONENT),
    (EntityType.COMPONENT, RelationType.COMPONENT_OF, EntityType.ASSET),
    (EntityType.ASSET, RelationType.LOCATED_AT, EntityType.LOCATION),
    # Causal relationships
    (EntityType.FAILURE_MODE, RelationType.CAUSES, EntityType.SYMPTOM),
    (EntityType.SYMPTOM, RelationType.SYMPTOMS_OF, EntityType.FAILURE_MODE),
    (EntityType.FAILURE_MODE, RelationType.HAS_SYMPTOM, EntityType.SYMPTOM),
    (EntityType.CONDITION, RelationType.CAUSES, EntityType.FAILURE_MODE),
    (EntityType.CONDITION, RelationType.CAUSES, EntityType.SYMPTOM),
    # Resolution relationships
    (EntityType.ACTION, RelationType.RESOLVES, EntityType.FAILURE_MODE),
    (EntityType.ACTION, RelationType.RESOLVES, EntityType.SYMPTOM),
    (EntityType.FAILURE_MODE, RelationType.RESOLVED_BY, EntityType.ACTION),
    (EntityType.SYMPTOM, RelationType.RESOLVED_BY, EntityType.ACTION),
    # Part relationships
    (EntityType.COMPONENT, RelationType.HAS_COMPONENT, EntityType.PART),
    (EntityType.PART, RelationType.COMPONENT_OF, EntityType.COMPONENT),
    # General relationships (always valid as a fallback)
    (EntityType.ASSET, RelationType.RELATED_TO, EntityType.ASSET),
    (EntityType.COMPONENT, RelationType.RELATED_TO, EntityType.COMPONENT),
    (EntityType.FAILURE_MODE, RelationType.RELATED_TO, EntityType.FAILURE_MODE),
}


def validate_relationship(
    source_type: EntityType,
    relation_type: RelationType,
    target_type: EntityType,
    *,
    strict: bool = False,
) -> bool:
    """Check if a relationship pattern is semantically valid.

    In strict mode, only explicitly defined patterns are valid.
    In non-strict mode (default), RELATED_TO is always valid
    between any entity types.

    Args:
        source_type: Entity type of the source node.
        relation_type: Type of relationship.
        target_type: Entity type of the target node.
        strict: If True, only explicit patterns are valid.

    Returns:
        True if the relationship pattern is valid.
    """
    pattern = (source_type, relation_type, target_type)

    if pattern in VALID_RELATIONSHIP_PATTERNS:
        return True

    # In non-strict mode, RELATED_TO is always valid
    return not strict and relation_type == RelationType.RELATED_TO
