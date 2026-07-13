"""Entity normalizer — converts raw analysis strings into typed KnowledgeEntity objects.

The normalizer sits between the DocumentAnalyzer (which extracts raw
strings like "Pump P-101", "SKF 6205-2RS") and the Knowledge Evolution
Engine (which merges entities into the graph). Its job:

  1. Take the raw strings from DocumentInsights
  2. Classify each into the correct EntityType
  3. Create KnowledgeEntity objects with Provenance (traceability)
  4. Assign source reliability based on DocumentType

Source Reliability:
  Different document types carry different weights. An OEM manual
  is more authoritative than an operator's note. Reliability affects
  confidence computation in the Knowledge Evolution Engine.

  | Source Type       | Reliability |
  |-------------------|-------------|
  | OEM Manual        | 1.0         |
  | Inspection Report | 0.9         |
  | Incident Report   | 0.85        |
  | Work Order        | 0.8         |
  | Unknown           | 0.7         |

Bounded Context: Knowledge
Layer: Adapters
Dependencies: knowledge.domain.entities, knowledge.domain.value_objects
"""

from __future__ import annotations

from typing import ClassVar

from forgemind.knowledge.adapters.analysis_service import DocumentInsights
from forgemind.knowledge.domain.entities import KnowledgeEntity
from forgemind.knowledge.domain.value_objects import (
    DocumentType,
    EntityType,
    Provenance,
)
from forgemind.shared.logging import get_logger

logger = get_logger(__name__)

# ── Source Reliability Weights ───────────────────────────────────
# Maps document types to reliability scores. Higher means the source
# is more authoritative and should contribute more to confidence.

SOURCE_RELIABILITY: dict[DocumentType, float] = {
    DocumentType.MANUAL: 1.0,
    DocumentType.INCIDENT_REPORT: 0.85,
    DocumentType.WORK_ORDER: 0.8,
    DocumentType.UNKNOWN: 0.7,
}


def _get_reliability(document_type: DocumentType) -> float:
    """Get the reliability weight for a document type.

    Args:
        document_type: The type of the source document.

    Returns:
        Reliability score between 0.0 and 1.0.
    """
    return SOURCE_RELIABILITY.get(document_type, 0.7)


class EntityNormalizer:
    """Converts raw extracted strings into typed KnowledgeEntity objects.

    Takes the output of DocumentAnalyzer (lists of raw strings) and
    produces KnowledgeEntity objects with:
      - Correct EntityType classification
      - Provenance linking back to the source document
      - Initial confidence based on source reliability

    Thread Safety:
        Stateless and thread-safe.

    Example:
        >>> normalizer = EntityNormalizer()
        >>> entities = normalizer.normalize(insights, "doc-123", "manual.pdf", DocumentType.MANUAL)
        >>> entities[0].entity_type
        EntityType.ASSET
        >>> entities[0].provenance.confidence
        1.0
    """

    def normalize(
        self,
        insights: DocumentInsights,
        document_id: str,
        document_title: str,
        document_type: DocumentType = DocumentType.UNKNOWN,
    ) -> list[KnowledgeEntity]:
        """Convert raw analysis insights into typed KnowledgeEntity objects.

        Each extracted string (equipment name, part number, symptom, etc.)
        becomes a KnowledgeEntity with the appropriate EntityType and
        Provenance that traces it back to the source document.

        Args:
            insights: The raw analysis output from DocumentAnalyzer.
            document_id: ID of the source document (for provenance).
            document_title: Title of the source document (for descriptions).
            document_type: Type of source document (affects reliability).

        Returns:
            List of KnowledgeEntity objects, deduplicated by canonical name.
        """
        reliability = _get_reliability(document_type)
        entities: list[KnowledgeEntity] = []
        seen_canonicals: set[str] = set()

        # ── Equipment → ASSET ────────────────────────────────────
        for name in insights.equipment:
            entity = self._create_entity(
                name=name,
                entity_type=EntityType.ASSET,
                description=f"Equipment extracted from '{document_title}'.",
                document_id=document_id,
                confidence=reliability,
                seen=seen_canonicals,
            )
            if entity is not None:
                entities.append(entity)

        # ── Parts → PART ─────────────────────────────────────────
        for name in insights.parts:
            entity = self._create_entity(
                name=name,
                entity_type=EntityType.PART,
                description=f"Part/model number from '{document_title}'.",
                document_id=document_id,
                confidence=reliability * 0.9,
                seen=seen_canonicals,
            )
            if entity is not None:
                entities.append(entity)

        # ── Materials → PART (sub-category) ──────────────────────
        for name in insights.materials:
            entity = self._create_entity(
                name=name,
                entity_type=EntityType.PART,
                description=f"Material specification from '{document_title}'.",
                document_id=document_id,
                confidence=reliability * 0.85,
                seen=seen_canonicals,
            )
            if entity is not None:
                entities.append(entity)

        # ── Symptoms → SYMPTOM ───────────────────────────────────
        for name in insights.symptoms:
            entity = self._create_entity(
                name=name,
                entity_type=EntityType.SYMPTOM,
                description=f"Failure symptom documented in '{document_title}'.",
                document_id=document_id,
                confidence=reliability * 0.95,
                seen=seen_canonicals,
            )
            if entity is not None:
                entities.append(entity)

        # ── Actions → ACTION ─────────────────────────────────────
        for sentence in insights.actions:
            short_name = self._extract_action_name(sentence)
            entity = self._create_entity(
                name=short_name,
                entity_type=EntityType.ACTION,
                description=sentence,
                document_id=document_id,
                confidence=reliability * 0.8,
                seen=seen_canonicals,
            )
            if entity is not None:
                entities.append(entity)

        # ── Parameters → CONDITION ───────────────────────────────
        # Operating parameters like "3000 RPM", "80 degrees Celsius"
        # become CONDITION entities so they can be linked to assets.
        for param in insights.parameters:
            entity = self._create_entity(
                name=param,
                entity_type=EntityType.CONDITION,
                description=f"Operating parameter from '{document_title}'.",
                document_id=document_id,
                confidence=reliability * 0.9,
                seen=seen_canonicals,
            )
            if entity is not None:
                entities.append(entity)

        # ── Instruments → COMPONENT ──────────────────────────────
        # Instruments (PSV-101, FS-101) are components of the system.
        for name in insights.instruments:
            entity = self._create_entity(
                name=name,
                entity_type=EntityType.COMPONENT,
                description=f"Instrument/safety device from '{document_title}'.",
                document_id=document_id,
                confidence=reliability * 0.85,
                seen=seen_canonicals,
            )
            if entity is not None:
                entities.append(entity)

        # ── Implicit components from text ─────────────────────────
        # Common industrial components often appear as nouns in the text
        # but aren't captured by the equipment pattern. We extract them
        # to make the graph richer.
        full_text = " ".join(insights.key_sentences) if insights.key_sentences else ""
        implicit_components = self._extract_implicit_components(full_text)
        for name in implicit_components:
            entity = self._create_entity(
                name=name,
                entity_type=EntityType.COMPONENT,
                description=f"Component identified in '{document_title}'.",
                document_id=document_id,
                confidence=reliability * 0.75,
                seen=seen_canonicals,
            )
            if entity is not None:
                entities.append(entity)

        logger.info(
            "entities_normalized",
            document_id=document_id,
            document_type=document_type.value,
            reliability=reliability,
            total_entities=len(entities),
            assets=sum(1 for e in entities if e.entity_type == EntityType.ASSET),
            components=sum(1 for e in entities if e.entity_type == EntityType.COMPONENT),
            parts=sum(1 for e in entities if e.entity_type == EntityType.PART),
            conditions=sum(1 for e in entities if e.entity_type == EntityType.CONDITION),
            symptoms=sum(1 for e in entities if e.entity_type == EntityType.SYMPTOM),
            actions=sum(1 for e in entities if e.entity_type == EntityType.ACTION),
        )

        return entities

    def _create_entity(
        self,
        name: str,
        entity_type: EntityType,
        description: str,
        document_id: str,
        confidence: float,
        seen: set[str],
    ) -> KnowledgeEntity | None:
        """Create a KnowledgeEntity if its canonical name is unique.

        Args:
            name: The raw entity name.
            entity_type: Classification for this entity.
            description: Contextual description.
            document_id: Source document for provenance.
            confidence: Initial confidence based on source reliability.
            seen: Set of already-seen canonical names (for dedup).

        Returns:
            A new KnowledgeEntity, or None if duplicate within this batch.
        """
        # Skip very short names (noise)
        if len(name.strip()) < 3:
            return None

        # Create entity to get its canonical_name
        entity = KnowledgeEntity.create(
            name=name.strip(),
            entity_type=entity_type,
            description=description,
            provenance=Provenance(
                source_document_id=document_id,
                extraction_method="pattern_based",
                confidence=min(confidence, 1.0),
            ),
        )

        # Deduplicate within this batch using canonical_name + type
        dedup_key = f"{entity.canonical_name}:{entity_type.value}"
        if dedup_key in seen:
            return None
        seen.add(dedup_key)

        return entity

    def _extract_action_name(self, sentence: str) -> str:
        """Extract a short action name from a full sentence.

        Takes the first meaningful words of an action sentence to
        create a concise graph node label.

        Examples:
            "Replace mechanical seal assembly." → "Replace mechanical seal assembly"
            "Check vibration levels with portable analyzer." → "Check vibration levels"
            "Verify inlet and outlet pressure readings..." → "Verify inlet and outlet pressure"

        Args:
            sentence: Full action sentence from the analyzer.

        Returns:
            Short action name (max 6 words).
        """
        # Remove trailing punctuation and ellipsis
        cleaned = sentence.rstrip(".!?,;:…")

        # Take first 6 words for a concise label
        words = cleaned.split()
        max_words = 6
        if len(words) > max_words:
            return " ".join(words[:max_words])
        return cleaned

    # ── Common industrial component names ────────────────────────
    # These appear as nouns in text but aren't captured by the
    # equipment tag pattern (which requires "Type-123" format).
    _COMPONENT_NAMES: ClassVar[list[str]] = [
        "impeller",
        "mechanical seal",
        "bearing",
        "coupling",
        "shaft",
        "volute casing",
        "wear ring",
        "motor",
        "suction strainer",
        "foundation",
        "bearing housing",
    ]

    def _extract_implicit_components(self, text: str) -> list[str]:
        """Extract common component names from document text.

        Scans for known industrial component names that appear
        as nouns in the document but aren't captured by the
        equipment regex pattern.

        Args:
            text: Full document text to scan.

        Returns:
            List of component names found in the text.
        """
        if not text:
            return []
        text_lower = text.lower()
        found: list[str] = []
        for name in self._COMPONENT_NAMES:
            if name in text_lower:
                # Capitalize for graph display
                found.append(name.title())
        return found
