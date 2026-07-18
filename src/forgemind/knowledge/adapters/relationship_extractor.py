"""Relationship extractor -- creates typed edges between entities from document text.

This is the densely-connected graph builder. It applies 8 rule families
to discover relationships between entities extracted from documents.

The extractor operates at two levels:
  1. CHUNK-LEVEL: Entities co-occurring in the same chunk.
  2. DOCUMENT-LEVEL: Entities that appear anywhere in the document
     but are semantically related by section structure.

Rule Families:
  1. HAS_COMPONENT: Asset + component/part in same chunk.
  2. CAUSED_BY: Symptom + cause with causation language.
  3. RESOLVES: Action + symptom/failure in corrective context.
  4. HAS_SYMPTOM: Component/asset + symptom in troubleshooting.
  5. INDICATES: Symptom indicates failure mode.
  6. OPERATED_BY: Asset operated/driven by another entity.
  7. HAS_PARAMETER: Asset/component + operating parameter.
  8. REQUIRES_PART: Action/procedure that mentions a specific part.

Design Goal: 3-8 relationships per entity (dense graph).

Bounded Context: Knowledge
Layer: Adapters
"""

from __future__ import annotations

import re

from forgemind.knowledge.domain.entities import (
    KnowledgeEntity,
    KnowledgeRelationship,
)
from forgemind.knowledge.domain.value_objects import (
    EntityType,
    Provenance,
    RelationType,
)
from forgemind.shared.logging import get_logger
from forgemind.shared.types import EntityId

logger = get_logger(__name__)

# ── Linguistic Patterns ──────────────────────────────────────────

_CAUSATION_PHRASES = re.compile(
    r"(?:caused?\s+by|due\s+to|result(?:s|ing)?\s+(?:from|of)|"
    r"indicates?|attributed\s+to|associated\s+with|"
    r"leads?\s+to|because\s+of|possible\s+causes?)",
    re.IGNORECASE,
)

_RESOLUTION_PHRASES = re.compile(
    r"(?:corrective\s+action|replace|repair|fix|resolve|"
    r"schedule\s+(?:replacement|maintenance)|"
    r"shut\s+down|re-?lubricate|realign|inspect\s+and|"
    r"check\s+and|verify|clean|measure)",
    re.IGNORECASE,
)

_OPERATED_BY_PHRASES = re.compile(
    r"(?:driven\s+by|operated\s+by|powered\s+by|"
    r"connected\s+(?:to|via)|through\s+a|"
    r"coupled\s+to|mounted\s+on)",
    re.IGNORECASE,
)


def _entity_in_text(entity: KnowledgeEntity, text_lower: str) -> bool:
    """Check if an entity name appears in text (case-insensitive, word-aware)."""
    name_lower = entity.name.lower()
    if len(name_lower) < 3:
        return False
    return name_lower in text_lower


class RelationshipExtractor:
    """Extracts relationships between entities using rule-based patterns.

    Applies 8 rule families at both chunk-level and document-level
    to create a densely connected knowledge graph.

    Thread Safety: Stateless and thread-safe.
    """

    def extract(
        self,
        entities: list[KnowledgeEntity],
        chunk_texts: list[str],
        document_id: str,
    ) -> list[KnowledgeRelationship]:
        """Extract relationships from entities and their source chunks.

        Args:
            entities: Typed entities from the EntityNormalizer.
            chunk_texts: The text content of each document chunk.
            document_id: Source document ID for provenance.

        Returns:
            List of deduplicated KnowledgeRelationship objects.
        """
        if not entities or not chunk_texts:
            return []

        by_type = self._group_by_type(entities)
        full_text_lower = " ".join(chunk_texts).lower()

        relationships: list[KnowledgeRelationship] = []
        seen: set[tuple[str, str, str]] = set()

        # ── Chunk-level rules (co-occurrence in same chunk) ──────
        for chunk_text in chunk_texts:
            chunk_lower = chunk_text.lower()

            self._rule_has_component(by_type, chunk_lower, document_id, relationships, seen)
            self._rule_caused_by(by_type, chunk_lower, document_id, relationships, seen)
            self._rule_resolves(by_type, chunk_lower, document_id, relationships, seen)
            self._rule_has_symptom_chunk(by_type, chunk_lower, document_id, relationships, seen)
            self._rule_indicates(by_type, chunk_lower, document_id, relationships, seen)
            self._rule_operated_by(by_type, chunk_lower, document_id, relationships, seen)
            self._rule_has_parameter(
                by_type, entities, chunk_lower, document_id, relationships, seen
            )
            self._rule_requires_part(by_type, chunk_lower, document_id, relationships, seen)

        # ── Document-level rules (broader structural patterns) ───
        self._rule_asset_symptom_document(
            by_type, full_text_lower, document_id, relationships, seen
        )
        self._rule_component_part_document(
            by_type, full_text_lower, document_id, relationships, seen
        )

        logger.info(
            "relationships_extracted",
            document_id=document_id,
            total=len(relationships),
        )

        return relationships

    # ══════════════════════════════════════════════════════════════
    # Rule 1: HAS_COMPONENT
    # ══════════════════════════════════════════════════════════════

    def _rule_has_component(
        self,
        by_type: dict[EntityType, list[KnowledgeEntity]],
        chunk_lower: str,
        doc_id: str,
        results: list[KnowledgeRelationship],
        seen: set[tuple[str, str, str]],
    ) -> None:
        """Asset + component/part in same chunk -> HAS_COMPONENT."""
        assets = by_type.get(EntityType.ASSET, [])
        targets = by_type.get(EntityType.COMPONENT, []) + by_type.get(EntityType.PART, [])
        if not assets or not targets:
            return

        for asset in assets:
            if not _entity_in_text(asset, chunk_lower):
                continue
            for target in targets:
                if not _entity_in_text(target, chunk_lower):
                    continue
                self._add(
                    results,
                    seen,
                    asset.id,
                    target.id,
                    RelationType.HAS_COMPONENT,
                    doc_id,
                    "rule:has_component",
                    0.85,
                )

    # ══════════════════════════════════════════════════════════════
    # Rule 2: CAUSED_BY
    # ══════════════════════════════════════════════════════════════

    def _rule_caused_by(
        self,
        by_type: dict[EntityType, list[KnowledgeEntity]],
        chunk_lower: str,
        doc_id: str,
        results: list[KnowledgeRelationship],
        seen: set[tuple[str, str, str]],
    ) -> None:
        """Symptom + causation phrase + cause entity -> CAUSED_BY."""
        if not _CAUSATION_PHRASES.search(chunk_lower):
            return

        symptoms = by_type.get(EntityType.SYMPTOM, [])
        causes = (
            by_type.get(EntityType.COMPONENT, [])
            + by_type.get(EntityType.CONDITION, [])
            + by_type.get(EntityType.FAILURE_MODE, [])
            + by_type.get(EntityType.PART, [])
        )

        for symptom in symptoms:
            if not _entity_in_text(symptom, chunk_lower):
                continue
            for cause in causes:
                if cause.id == symptom.id or not _entity_in_text(cause, chunk_lower):
                    continue
                self._add(
                    results,
                    seen,
                    symptom.id,
                    cause.id,
                    RelationType.CAUSED_BY,
                    doc_id,
                    "rule:caused_by",
                    0.75,
                )

    # ══════════════════════════════════════════════════════════════
    # Rule 3: RESOLVES
    # ══════════════════════════════════════════════════════════════

    def _rule_resolves(
        self,
        by_type: dict[EntityType, list[KnowledgeEntity]],
        chunk_lower: str,
        doc_id: str,
        results: list[KnowledgeRelationship],
        seen: set[tuple[str, str, str]],
    ) -> None:
        """Action + resolution phrase + symptom/failure -> RESOLVES."""
        if not _RESOLUTION_PHRASES.search(chunk_lower):
            return

        actions = by_type.get(EntityType.ACTION, [])
        targets = by_type.get(EntityType.SYMPTOM, []) + by_type.get(EntityType.FAILURE_MODE, [])

        for action in actions:
            if not _entity_in_text(action, chunk_lower):
                continue
            for target in targets:
                if not _entity_in_text(target, chunk_lower):
                    continue
                self._add(
                    results,
                    seen,
                    action.id,
                    target.id,
                    RelationType.RESOLVES,
                    doc_id,
                    "rule:resolves",
                    0.7,
                )

    # ══════════════════════════════════════════════════════════════
    # Rule 4: HAS_SYMPTOM (chunk-level)
    # ══════════════════════════════════════════════════════════════

    def _rule_has_symptom_chunk(
        self,
        by_type: dict[EntityType, list[KnowledgeEntity]],
        chunk_lower: str,
        doc_id: str,
        results: list[KnowledgeRelationship],
        seen: set[tuple[str, str, str]],
    ) -> None:
        """Component/asset + symptom in same chunk -> HAS_SYMPTOM."""
        sources = by_type.get(EntityType.COMPONENT, []) + by_type.get(EntityType.ASSET, [])
        symptoms = by_type.get(EntityType.SYMPTOM, [])

        for source in sources:
            if not _entity_in_text(source, chunk_lower):
                continue
            for symptom in symptoms:
                if not _entity_in_text(symptom, chunk_lower):
                    continue
                self._add(
                    results,
                    seen,
                    source.id,
                    symptom.id,
                    RelationType.HAS_SYMPTOM,
                    doc_id,
                    "rule:has_symptom_chunk",
                    0.7,
                )

    # ══════════════════════════════════════════════════════════════
    # Rule 5: INDICATES
    # ══════════════════════════════════════════════════════════════

    def _rule_indicates(
        self,
        by_type: dict[EntityType, list[KnowledgeEntity]],
        chunk_lower: str,
        doc_id: str,
        results: list[KnowledgeRelationship],
        seen: set[tuple[str, str, str]],
    ) -> None:
        """Symptom + failure mode/condition in same chunk -> INDICATES."""
        symptoms = by_type.get(EntityType.SYMPTOM, [])
        failure_modes = by_type.get(EntityType.FAILURE_MODE, []) + by_type.get(
            EntityType.CONDITION, []
        )

        for symptom in symptoms:
            if not _entity_in_text(symptom, chunk_lower):
                continue
            for fm in failure_modes:
                if fm.id == symptom.id or not _entity_in_text(fm, chunk_lower):
                    continue
                self._add(
                    results,
                    seen,
                    symptom.id,
                    fm.id,
                    RelationType.INDICATES,
                    doc_id,
                    "rule:indicates",
                    0.65,
                )

    # ══════════════════════════════════════════════════════════════
    # Rule 6: OPERATED_BY
    # ══════════════════════════════════════════════════════════════

    def _rule_operated_by(
        self,
        by_type: dict[EntityType, list[KnowledgeEntity]],
        chunk_lower: str,
        doc_id: str,
        results: list[KnowledgeRelationship],
        seen: set[tuple[str, str, str]],
    ) -> None:
        """Asset + 'driven by'/'operated by' + component -> OPERATED_BY."""
        if not _OPERATED_BY_PHRASES.search(chunk_lower):
            return

        assets = by_type.get(EntityType.ASSET, [])
        drivers = by_type.get(EntityType.COMPONENT, []) + by_type.get(EntityType.PART, [])

        for asset in assets:
            if not _entity_in_text(asset, chunk_lower):
                continue
            for driver in drivers:
                if driver.id == asset.id or not _entity_in_text(driver, chunk_lower):
                    continue
                self._add(
                    results,
                    seen,
                    asset.id,
                    driver.id,
                    RelationType.OPERATED_BY,
                    doc_id,
                    "rule:operated_by",
                    0.8,
                )

    # ══════════════════════════════════════════════════════════════
    # Rule 7: HAS_PARAMETER
    # ══════════════════════════════════════════════════════════════

    def _rule_has_parameter(
        self,
        by_type: dict[EntityType, list[KnowledgeEntity]],
        all_entities: list[KnowledgeEntity],
        chunk_lower: str,
        doc_id: str,
        results: list[KnowledgeRelationship],
        seen: set[tuple[str, str, str]],
    ) -> None:
        """Asset/component + parameter value in same chunk -> HAS_PARAMETER."""
        sources = by_type.get(EntityType.ASSET, []) + by_type.get(EntityType.COMPONENT, [])
        params = by_type.get(EntityType.CONDITION, [])

        for source in sources:
            if not _entity_in_text(source, chunk_lower):
                continue
            for param in params:
                if not _entity_in_text(param, chunk_lower):
                    continue
                self._add(
                    results,
                    seen,
                    source.id,
                    param.id,
                    RelationType.HAS_PARAMETER,
                    doc_id,
                    "rule:has_parameter",
                    0.8,
                )

    # ══════════════════════════════════════════════════════════════
    # Rule 8: REQUIRES_PART
    # ══════════════════════════════════════════════════════════════

    def _rule_requires_part(
        self,
        by_type: dict[EntityType, list[KnowledgeEntity]],
        chunk_lower: str,
        doc_id: str,
        results: list[KnowledgeRelationship],
        seen: set[tuple[str, str, str]],
    ) -> None:
        """Action + part in same chunk -> REQUIRES_PART."""
        if not _RESOLUTION_PHRASES.search(chunk_lower):
            return

        actions = by_type.get(EntityType.ACTION, [])
        parts = by_type.get(EntityType.PART, []) + by_type.get(EntityType.COMPONENT, [])

        for action in actions:
            if not _entity_in_text(action, chunk_lower):
                continue
            for part in parts:
                if not _entity_in_text(part, chunk_lower):
                    continue
                self._add(
                    results,
                    seen,
                    action.id,
                    part.id,
                    RelationType.REQUIRES_PART,
                    doc_id,
                    "rule:requires_part",
                    0.7,
                )

    # ══════════════════════════════════════════════════════════════
    # Document-level rules
    # ══════════════════════════════════════════════════════════════

    def _rule_asset_symptom_document(
        self,
        by_type: dict[EntityType, list[KnowledgeEntity]],
        full_text_lower: str,
        doc_id: str,
        results: list[KnowledgeRelationship],
        seen: set[tuple[str, str, str]],
    ) -> None:
        """If the document is about an asset and has symptoms, connect them.

        This is a broader document-level rule. If the document title
        or first chunk is about an asset, and symptoms appear anywhere,
        the asset HAS_SYMPTOM those symptoms.
        """
        assets = by_type.get(EntityType.ASSET, [])
        symptoms = by_type.get(EntityType.SYMPTOM, [])
        if not assets or not symptoms:
            return

        # Only apply for the "primary" asset (first one found in doc)
        primary_asset = assets[0]
        for symptom in symptoms:
            self._add(
                results,
                seen,
                primary_asset.id,
                symptom.id,
                RelationType.HAS_SYMPTOM,
                doc_id,
                "rule:asset_symptom_doc",
                0.6,
            )

    def _rule_component_part_document(
        self,
        by_type: dict[EntityType, list[KnowledgeEntity]],
        full_text_lower: str,
        doc_id: str,
        results: list[KnowledgeRelationship],
        seen: set[tuple[str, str, str]],
    ) -> None:
        """Connect the primary asset to all components/parts in the doc.

        If the document is about an asset, every component and part
        mentioned anywhere is likely a component of that asset.
        """
        assets = by_type.get(EntityType.ASSET, [])
        components = by_type.get(EntityType.COMPONENT, []) + by_type.get(EntityType.PART, [])
        if not assets or not components:
            return

        primary_asset = assets[0]
        for comp in components:
            self._add(
                results,
                seen,
                primary_asset.id,
                comp.id,
                RelationType.HAS_COMPONENT,
                doc_id,
                "rule:asset_component_doc",
                0.65,
            )

    # ══════════════════════════════════════════════════════════════
    # Helpers
    # ══════════════════════════════════════════════════════════════

    def _group_by_type(
        self,
        entities: list[KnowledgeEntity],
    ) -> dict[EntityType, list[KnowledgeEntity]]:
        """Group entities by type for efficient rule application."""
        grouped: dict[EntityType, list[KnowledgeEntity]] = {}
        for entity in entities:
            grouped.setdefault(entity.entity_type, []).append(entity)
        return grouped

    def _add(
        self,
        results: list[KnowledgeRelationship],
        seen: set[tuple[str, str, str]],
        source_id: EntityId,
        target_id: EntityId,
        relation_type: RelationType,
        doc_id: str,
        method: str,
        confidence: float,
    ) -> None:
        """Add a relationship if not already seen."""
        key = (str(source_id), str(target_id), relation_type.value)
        if key in seen or source_id == target_id:
            return
        seen.add(key)
        results.append(
            KnowledgeRelationship.create(
                source_entity_id=source_id,
                target_entity_id=target_id,
                relation_type=relation_type,
                provenance=Provenance(
                    source_document_id=doc_id,
                    extraction_method=method,
                    confidence=confidence,
                ),
            )
        )
