"""Reasoning engine -- graph-based, deterministic, explainable intelligence.

This is ForgeMind's core differentiator. Instead of calling an LLM,
the reasoning engine traverses the knowledge graph to produce
structured, explainable answers.

The output follows the Decision Intelligence pattern:

    Observation -> Evidence -> Possible Causes -> Recommendation -> Confidence

Every step in the reasoning chain is backed by a graph traversal
that can be audited. The engine answers questions like:

  "Why does Pump P-101 have excessive vibration?"

By traversing:

  Pump P-101 -> HAS_SYMPTOM -> Excessive Vibration
  Excessive Vibration -> CAUSED_BY -> [Bearing Failure, Misalignment, ...]
  Bearing Failure -> RESOLVED_BY -> [Replace Bearing, ...]

And producing a structured response with evidence and confidence scores.

Bounded Context: Reasoning
Layer: Adapters (Application Service)
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

from forgemind.graph.adapters.networkx_repository import NetworkXGraphRepository
from forgemind.knowledge.domain.entities import KnowledgeEntity
from forgemind.knowledge.domain.value_objects import EntityType, RelationType
from forgemind.shared.logging import get_logger

logger = get_logger(__name__)


# ── Data Models ──────────────────────────────────────────────────


@dataclass(frozen=True, slots=True)
class EvidenceLink:
    """A single piece of evidence from the knowledge graph.

    Represents one edge traversal that contributed to the reasoning.
    """

    source_name: str
    source_type: str
    relation: str
    target_name: str
    target_type: str
    confidence: float

    def as_sentence(self) -> str:
        """Render as human-readable sentence."""
        verb = _RELATION_VERBS.get(self.relation, self.relation)
        return f"{self.source_name} {verb} {self.target_name}"


@dataclass(frozen=True, slots=True)
class ReasoningStep:
    """One step in the reasoning chain."""

    step_number: int
    description: str
    evidence: list[EvidenceLink]
    entities_found: int


@dataclass
class ReasoningResult:
    """The full structured output of a reasoning query.

    This is what makes ForgeMind explainable. Every recommendation
    comes with the full chain of evidence.
    """

    query: str
    entity_name: str
    entity_type: str
    timestamp: str = field(
        default_factory=lambda: datetime.now(UTC).isoformat(),
    )
    observations: list[str] = field(default_factory=list)
    reasoning_chain: list[ReasoningStep] = field(default_factory=list)
    possible_causes: list[dict[str, Any]] = field(default_factory=list)
    recommendations: list[dict[str, Any]] = field(default_factory=list)
    confidence: float = 0.0
    confidence_explanation: str = ""
    graph_traversals: int = 0
    evidence_count: int = 0


# ── Relation verbs for human-readable output ─────────────────────

_RELATION_VERBS: dict[str, str] = {
    "has_component": "has component",
    "component_of": "is a component of",
    "has_symptom": "exhibits symptom",
    "symptoms_of": "is a symptom of",
    "caused_by": "is caused by",
    "causes": "causes",
    "resolved_by": "is resolved by",
    "resolves": "resolves",
    "operated_by": "is operated by",
    "has_parameter": "has parameter",
    "indicates": "indicates",
    "manufactured_by": "is manufactured by",
    "requires_part": "requires part",
    "monitors": "monitors",
    "related_to": "is related to",
    "located_at": "is located at",
}


class ReasoningService:
    """Graph-based reasoning engine.

    Traverses the knowledge graph to produce structured, explainable
    answers. No LLM required — all reasoning is deterministic and
    auditable.

    Thread Safety: Stateless, reads graph via thread-safe repository.
    """

    def reason(
        self,
        query: str,
        graph: NetworkXGraphRepository,
    ) -> ReasoningResult:
        """Answer a question using graph traversal.

        The engine:
          1. Finds the most relevant entity in the graph.
          2. Discovers symptoms, causes, and resolutions.
          3. Builds a reasoning chain with evidence.
          4. Computes an aggregate confidence score.

        Args:
            query: The question to answer (e.g., "Why does Pump P-101 vibrate?").
            graph: The knowledge graph repository.

        Returns:
            A structured ReasoningResult with full evidence chain.
        """
        # Step 1: Find the focal entity
        focal = self._find_focal_entity(query, graph)
        if focal is None:
            return ReasoningResult(
                query=query,
                entity_name="Unknown",
                entity_type="unknown",
                observations=["No matching entity found in the knowledge graph."],
                confidence=0.0,
                confidence_explanation="No entity matched the query.",
            )

        result = ReasoningResult(
            query=query,
            entity_name=focal.name,
            entity_type=focal.entity_type.value,
        )

        # Step 2: Gather observations (direct neighbors)
        step_num = 0
        all_evidence: list[EvidenceLink] = []

        # 2a: Components
        step_num, evidence = self._discover_components(focal, graph, step_num, result)
        all_evidence.extend(evidence)

        # 2b: Symptoms
        step_num, evidence = self._discover_symptoms(focal, graph, step_num, result)
        all_evidence.extend(evidence)

        # 2c: Causes (from symptoms)
        step_num, evidence = self._discover_causes(focal, graph, step_num, result)
        all_evidence.extend(evidence)

        # 2d: Resolutions
        step_num, evidence = self._discover_resolutions(focal, graph, step_num, result)
        all_evidence.extend(evidence)

        # 2e: Parameters
        step_num, evidence = self._discover_parameters(focal, graph, step_num, result)
        all_evidence.extend(evidence)

        # Step 3: Compute confidence
        result.graph_traversals = step_num
        result.evidence_count = len(all_evidence)
        result.confidence = self._compute_confidence(all_evidence)
        result.confidence_explanation = self._explain_confidence(all_evidence, result)

        logger.info(
            "reasoning_complete",
            query=query,
            entity=focal.name,
            steps=step_num,
            evidence=len(all_evidence),
            causes=len(result.possible_causes),
            recommendations=len(result.recommendations),
            confidence=round(result.confidence, 4),
        )

        return result

    # ══════════════════════════════════════════════════════════════
    # Entity Resolution
    # ══════════════════════════════════════════════════════════════

    def _find_focal_entity(
        self,
        query: str,
        graph: NetworkXGraphRepository,
    ) -> KnowledgeEntity | None:
        """Find the most relevant entity for the query.

        Uses substring matching on entity names, prioritizing assets
        and components over conditions and actions.
        """
        query_lower = query.lower()

        # Search for matching entities
        all_entities: list[KnowledgeEntity] = []
        for entity_type in EntityType:
            all_entities.extend(graph.query_by_type(entity_type))

        # Score each entity
        best: KnowledgeEntity | None = None
        best_score = -1

        # Priority weights for entity types
        type_priority = {
            EntityType.ASSET: 10,
            EntityType.COMPONENT: 8,
            EntityType.SYMPTOM: 6,
            EntityType.FAILURE_MODE: 6,
            EntityType.PART: 4,
            EntityType.ACTION: 3,
            EntityType.CONDITION: 2,
            EntityType.LOCATION: 1,
        }

        for entity in all_entities:
            name_lower = entity.name.lower()
            if name_lower in query_lower or query_lower in name_lower:
                # Exact or near-exact match
                score = 100 + type_priority.get(entity.entity_type, 0)
            elif any(word in query_lower for word in name_lower.split() if len(word) > 3):
                # Partial word match
                matching_words = sum(
                    1 for word in name_lower.split() if len(word) > 3 and word in query_lower
                )
                score = matching_words * 10 + type_priority.get(entity.entity_type, 0)
            else:
                continue

            if score > best_score:
                best_score = score
                best = entity

        return best

    # ══════════════════════════════════════════════════════════════
    # Discovery Steps
    # ══════════════════════════════════════════════════════════════

    def _discover_components(
        self,
        focal: KnowledgeEntity,
        graph: NetworkXGraphRepository,
        step_num: int,
        result: ReasoningResult,
    ) -> tuple[int, list[EvidenceLink]]:
        """Discover components of the focal entity."""
        neighbors = graph.get_neighbors(
            str(focal.id),
            relation_filter=RelationType.HAS_COMPONENT,
        )
        if not neighbors:
            return step_num, []

        step_num += 1
        evidence: list[EvidenceLink] = []
        component_names: list[str] = []

        for neighbor in neighbors:
            link = EvidenceLink(
                source_name=focal.name,
                source_type=focal.entity_type.value,
                relation="has_component",
                target_name=neighbor.name,
                target_type=neighbor.entity_type.value,
                confidence=0.85,
            )
            evidence.append(link)
            component_names.append(neighbor.name)

        result.observations.append(
            f"{focal.name} has {len(component_names)} known components: "
            f"{', '.join(component_names[:8])}"
            + (f" (+{len(component_names) - 8} more)" if len(component_names) > 8 else "")
        )
        result.reasoning_chain.append(
            ReasoningStep(
                step_number=step_num,
                description=f"Discovered {len(component_names)} components of {focal.name}",
                evidence=evidence,
                entities_found=len(component_names),
            )
        )
        return step_num, evidence

    def _discover_symptoms(
        self,
        focal: KnowledgeEntity,
        graph: NetworkXGraphRepository,
        step_num: int,
        result: ReasoningResult,
    ) -> tuple[int, list[EvidenceLink]]:
        """Discover symptoms associated with the focal entity."""
        neighbors = graph.get_neighbors(
            str(focal.id),
            relation_filter=RelationType.HAS_SYMPTOM,
        )
        if not neighbors:
            return step_num, []

        step_num += 1
        evidence: list[EvidenceLink] = []
        symptom_names: list[str] = []

        for neighbor in neighbors:
            link = EvidenceLink(
                source_name=focal.name,
                source_type=focal.entity_type.value,
                relation="has_symptom",
                target_name=neighbor.name,
                target_type=neighbor.entity_type.value,
                confidence=0.8,
            )
            evidence.append(link)
            symptom_names.append(neighbor.name)

        result.observations.append(
            f"{focal.name} has {len(symptom_names)} documented symptoms: "
            f"{', '.join(symptom_names[:6])}"
            + (f" (+{len(symptom_names) - 6} more)" if len(symptom_names) > 6 else "")
        )
        result.reasoning_chain.append(
            ReasoningStep(
                step_number=step_num,
                description=f"Found {len(symptom_names)} symptoms linked to {focal.name}",
                evidence=evidence,
                entities_found=len(symptom_names),
            )
        )
        return step_num, evidence

    def _discover_causes(
        self,
        focal: KnowledgeEntity,
        graph: NetworkXGraphRepository,
        step_num: int,
        result: ReasoningResult,
    ) -> tuple[int, list[EvidenceLink]]:
        """Discover causes by traversing symptom -> CAUSED_BY edges."""
        # First find symptoms
        symptoms = graph.get_neighbors(
            str(focal.id),
            relation_filter=RelationType.HAS_SYMPTOM,
        )

        all_evidence: list[EvidenceLink] = []
        seen_causes: set[str] = set()

        for symptom in symptoms:
            causes = graph.get_neighbors(
                str(symptom.id),
                relation_filter=RelationType.CAUSED_BY,
            )
            for cause in causes:
                if cause.name in seen_causes:
                    continue
                seen_causes.add(cause.name)

                link = EvidenceLink(
                    source_name=symptom.name,
                    source_type=symptom.entity_type.value,
                    relation="caused_by",
                    target_name=cause.name,
                    target_type=cause.entity_type.value,
                    confidence=0.7,
                )
                all_evidence.append(link)

                result.possible_causes.append(
                    {
                        "cause": cause.name,
                        "type": cause.entity_type.value,
                        "symptom": symptom.name,
                        "evidence": link.as_sentence(),
                        "confidence": round(link.confidence, 4),
                    }
                )

        if all_evidence:
            step_num += 1
            result.reasoning_chain.append(
                ReasoningStep(
                    step_number=step_num,
                    description=(
                        f"Traced {len(seen_causes)} possible causes from {len(symptoms)} symptoms"
                    ),
                    evidence=all_evidence,
                    entities_found=len(seen_causes),
                )
            )

        return step_num, all_evidence

    def _discover_resolutions(
        self,
        focal: KnowledgeEntity,
        graph: NetworkXGraphRepository,
        step_num: int,
        result: ReasoningResult,
    ) -> tuple[int, list[EvidenceLink]]:
        """Discover resolution actions from symptoms and causes."""
        # Look for actions that RESOLVE symptoms
        symptoms = graph.get_neighbors(
            str(focal.id),
            relation_filter=RelationType.HAS_SYMPTOM,
        )

        all_evidence: list[EvidenceLink] = []
        seen_actions: set[str] = set()

        # Also check all entities for RESOLVES edges
        for entity_type in [EntityType.ACTION]:
            for action in graph.query_by_type(entity_type):
                targets = graph.get_neighbors(
                    str(action.id),
                    relation_filter=RelationType.RESOLVES,
                )
                for target in targets:
                    # Check if this action resolves any of the symptoms
                    symptom_names = {s.name for s in symptoms}
                    if target.name in symptom_names and action.name not in seen_actions:
                        seen_actions.add(action.name)

                        link = EvidenceLink(
                            source_name=action.name,
                            source_type=action.entity_type.value,
                            relation="resolves",
                            target_name=target.name,
                            target_type=target.entity_type.value,
                            confidence=0.75,
                        )
                        all_evidence.append(link)

                        result.recommendations.append(
                            {
                                "action": action.name,
                                "description": action.description or "",
                                "resolves": target.name,
                                "evidence": link.as_sentence(),
                                "confidence": round(link.confidence, 4),
                            }
                        )

        if all_evidence:
            step_num += 1
            result.reasoning_chain.append(
                ReasoningStep(
                    step_number=step_num,
                    description=(f"Found {len(seen_actions)} recommended actions"),
                    evidence=all_evidence,
                    entities_found=len(seen_actions),
                )
            )

        return step_num, all_evidence

    def _discover_parameters(
        self,
        focal: KnowledgeEntity,
        graph: NetworkXGraphRepository,
        step_num: int,
        result: ReasoningResult,
    ) -> tuple[int, list[EvidenceLink]]:
        """Discover operating parameters linked to the focal entity."""
        neighbors = graph.get_neighbors(
            str(focal.id),
            relation_filter=RelationType.HAS_PARAMETER,
        )
        if not neighbors:
            return step_num, []

        step_num += 1
        evidence: list[EvidenceLink] = []
        param_names: list[str] = []

        for neighbor in neighbors:
            link = EvidenceLink(
                source_name=focal.name,
                source_type=focal.entity_type.value,
                relation="has_parameter",
                target_name=neighbor.name,
                target_type=neighbor.entity_type.value,
                confidence=0.9,
            )
            evidence.append(link)
            param_names.append(neighbor.name)

        result.observations.append(
            f"{focal.name} has {len(param_names)} operating parameters: "
            f"{', '.join(param_names[:6])}"
            + (f" (+{len(param_names) - 6} more)" if len(param_names) > 6 else "")
        )
        result.reasoning_chain.append(
            ReasoningStep(
                step_number=step_num,
                description=f"Found {len(param_names)} operating parameters",
                evidence=evidence,
                entities_found=len(param_names),
            )
        )
        return step_num, evidence

    # ══════════════════════════════════════════════════════════════
    # Confidence Computation
    # ══════════════════════════════════════════════════════════════

    def _compute_confidence(self, evidence: list[EvidenceLink]) -> float:
        """Compute overall confidence from evidence chain.

        Uses weighted average of individual evidence confidences,
        boosted by evidence count (more evidence = higher confidence).

        Args:
            evidence: All evidence links from the reasoning chain.

        Returns:
            Aggregate confidence in [0.0, 1.0].
        """
        if not evidence:
            return 0.0

        avg_confidence = sum(e.confidence for e in evidence) / len(evidence)

        # Evidence count boost: more evidence increases confidence
        # asymptotically toward 1.0
        count_factor = min(1.0, len(evidence) / 20.0)

        return min(1.0, avg_confidence * (0.6 + 0.4 * count_factor))

    def _explain_confidence(
        self,
        evidence: list[EvidenceLink],
        result: ReasoningResult,
    ) -> str:
        """Generate a human-readable confidence explanation."""
        if not evidence:
            return "No evidence found to support reasoning."

        parts = [
            f"Based on {len(evidence)} evidence links",
            f"across {result.graph_traversals} graph traversals.",
        ]

        if result.possible_causes:
            parts.append(f"Found {len(result.possible_causes)} possible causes.")
        if result.recommendations:
            parts.append(f"Found {len(result.recommendations)} recommended actions.")

        avg_conf = sum(e.confidence for e in evidence) / len(evidence)
        parts.append(f"Average evidence confidence: {avg_conf:.2f}.")

        return " ".join(parts)
