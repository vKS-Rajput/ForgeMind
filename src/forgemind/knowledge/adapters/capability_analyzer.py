"""Document Capability Analyzer — evaluates document relevance and capabilities.

Analyzes parsed document text prior to full knowledge graph ingestion to:
  1. Classify the document type (Manual, Incident Report, Inspection Report, Work Order, SOP, P&ID, Spreadsheet, General).
  2. Compute an Industrial Relevance Score based on domain keyword density and terminology.
  3. Determine the Support Level ("full", "partial", "unsupported").
  4. Generate a feature matrix (parse, entity_extraction, relationship_extraction, graph_evolution, reasoning).
  5. Produce actionable recommendations and graceful warnings for low-relevance or non-industrial uploads.

Bounded Context: Knowledge
Layer: Adapters
Dependencies: domain.value_objects, shared
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any

from forgemind.knowledge.domain.value_objects import DocumentType
from forgemind.shared.logging import get_logger

logger = get_logger(__name__)

# ── Domain Term Lists for Relevance Scoring ───────────────────────

INDUSTRIAL_TERMS: set[str] = {
    # Assets & Equipment
    "pump", "compressor", "valve", "motor", "turbine", "gearbox", "bearing",
    "impeller", "coupling", "seal", "stator", "rotor", "actuator", "boiler",
    "chiller", "conveyor", "vessel", "heat exchanger", "piping", "flange",
    # Symptoms & Conditions
    "vibration", "overheating", "cavitation", "leak", "leakage", "pressure",
    "temperature", "noise", "alignment", "misalignment", "wear", "corrosion",
    "friction", "discharge", "flow rate", "rpm", "current", "voltage",
    # Failure Modes & Maintenance
    "failure", "fault", "breakdown", "tripped", "seized", "damaged", "repair",
    "replaced", "inspected", "maintenance", "overhaul", "lubrication",
    "tolerance", "vibration analysis", "root cause", "corrective",
}

NON_INDUSTRIAL_INDICATORS: set[str] = {
    "invoice", "financial report", "tax return", "balance sheet", "recipe",
    "menu", "novel", "poetry", "statement of account", "resume", "curriculum vitae",
    "purchase order", "shipping manifest", "marketing brochure", "newsletter",
}


@dataclass(frozen=True, slots=True)
class DocumentCapability:
    """Capability analysis result for a document.

    Attributes:
        document_type: Detected classification of the document.
        confidence: Confidence score of the classification [0.0, 1.0].
        relevance_score: Industrial relevance score [0.0, 1.0].
        support_level: Level of system support ("full", "partial", "unsupported").
        available_features: Dictionary of boolean feature flags.
        warnings: List of warning strings if document is only partially supported or unsupported.
        recommendations: Actionable suggestions for the user.
    """

    document_type: DocumentType
    confidence: float
    relevance_score: float
    support_level: str  # "full", "partial", "unsupported"
    available_features: dict[str, bool] = field(default_factory=dict)
    warnings: list[str] = field(default_factory=list)
    recommendations: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        """Convert capability result to a serializable dictionary."""
        return {
            "document_type": self.document_type.value,
            "confidence": round(self.confidence, 2),
            "relevance_score": round(self.relevance_score, 2),
            "support_level": self.support_level,
            "available_features": self.available_features,
            "warnings": self.warnings,
            "recommendations": self.recommendations,
        }


class DocumentCapabilityAnalyzer:
    """Evaluates documents for industrial relevance and capability support."""

    def analyze(self, title: str, text: str, page_count: int = 1) -> DocumentCapability:
        """Analyze document title and text content to determine capabilities.

        Args:
            title: Title or filename of the document.
            text: Full text extracted from the document.
            page_count: Total page count.

        Returns:
            A DocumentCapability instance containing relevance and support metrics.
        """
        combined = f"{title} {text[:5000]}".lower()

        # 1. Compute Industrial Relevance Score
        words = re.findall(r"\b[a-z]{3,}\b", combined)
        total_word_count = len(words)

        if total_word_count == 0:
            return DocumentCapability(
                document_type=DocumentType.UNKNOWN,
                confidence=0.0,
                relevance_score=0.0,
                support_level="unsupported",
                available_features={
                    "parse": False,
                    "entity_extraction": False,
                    "relationship_extraction": False,
                    "graph_evolution": False,
                    "reasoning": False,
                },
                warnings=["The uploaded document contains no extractable text."],
                recommendations=["Please upload a readable PDF containing text or OCR-processed content."],
            )

        match_count = sum(1 for w in words if w in INDUSTRIAL_TERMS)
        non_ind_match = sum(1 for w in words if w in NON_INDUSTRIAL_INDICATORS)

        # Base relevance: ratio of industrial terms to sample length
        raw_relevance = min(1.0, (match_count * 8.0) / max(total_word_count, 50))
        if non_ind_match > 0:
            raw_relevance = max(0.0, raw_relevance - (non_ind_match * 0.2))

        relevance_score = min(1.0, max(0.05, raw_relevance))

        # 2. Document Type Classification
        doc_type, type_confidence = self._classify_document(title, text, combined)

        # 3. Determine Support Level & Feature Availability
        support_level, available_features, warnings, recommendations = self._determine_support(
            doc_type=doc_type,
            relevance_score=relevance_score,
            title=title,
        )

        logger.info(
            "capability_analyzed",
            title=title,
            doc_type=doc_type.value,
            confidence=round(type_confidence, 2),
            relevance=round(relevance_score, 2),
            support_level=support_level,
        )

        return DocumentCapability(
            document_type=doc_type,
            confidence=type_confidence,
            relevance_score=relevance_score,
            support_level=support_level,
            available_features=available_features,
            warnings=warnings,
            recommendations=recommendations,
        )

    def _classify_document(
        self, title: str, text: str, combined: str
    ) -> tuple[DocumentType, float]:
        """Classify document type and return confidence."""
        if any(kw in combined for kw in ["p&id", "piping and instrumentation", "schematic"]):
            return DocumentType.P_AND_ID, 0.90
        if any(kw in combined for kw in ["spreadsheet", "excel log", ".xlsx", "csv export"]):
            return DocumentType.SPREADSHEET, 0.85
        if any(kw in combined for kw in ["standard operating procedure", "sop ", "safety procedure"]):
            return DocumentType.SOP, 0.85
        if any(kw in combined for kw in ["manual", "operating manual", "user manual", "specification"]):
            return DocumentType.MANUAL, 0.90
        if any(kw in combined for kw in ["incident report", "failure report", "root cause", "breakdown"]):
            return DocumentType.INCIDENT_REPORT, 0.90
        if any(kw in combined for kw in ["inspection report", "inspection date", "inspector", "findings"]):
            return DocumentType.INSPECTION_REPORT, 0.90
        if any(kw in combined for kw in ["work order", "service order", "repair order", "cmms"]):
            return DocumentType.WORK_ORDER, 0.80

        # Check for non-industrial indicator match
        if any(kw in combined for kw in NON_INDUSTRIAL_INDICATORS):
            return DocumentType.GENERAL, 0.85

        return DocumentType.UNKNOWN, 0.50

    def _determine_support(
        self,
        doc_type: DocumentType,
        relevance_score: float,
        title: str,
    ) -> tuple[str, dict[str, bool], list[str], list[str]]:
        """Determine system support level, available features, warnings, and recommendations."""
        warnings: list[str] = []
        recommendations: list[str] = []

        if relevance_score < 0.25 or doc_type in (DocumentType.GENERAL, DocumentType.P_AND_ID):
            support_level = "unsupported"
            available_features = {
                "parse": True,
                "entity_extraction": False,
                "relationship_extraction": False,
                "graph_evolution": False,
                "reasoning": False,
            }
            warnings.append(
                f"'{title}' does not appear to contain industrial maintenance knowledge (Relevance: {round(relevance_score*100)}%)."
            )
            recommendations.extend([
                "Upload an OEM Equipment Manual (e.g. Pump, Valve, Compressor)",
                "Upload an Incident Report or Failure Analysis",
                "Upload an Inspection Checklist or Maintenance Work Order",
            ])
            return support_level, available_features, warnings, recommendations

        if doc_type in (DocumentType.WORK_ORDER, DocumentType.SOP, DocumentType.SPREADSHEET) or relevance_score < 0.55:
            support_level = "partial"
            available_features = {
                "parse": True,
                "entity_extraction": True,
                "relationship_extraction": True,
                "graph_evolution": True,
                "reasoning": False,
            }
            warnings.append(
                f"'{title}' is classified as {doc_type.value.upper()} (Partial Support). Basic entities extracted, but maintenance reasoning is limited."
            )
            recommendations.append(
                "For full root-cause decision intelligence, upload complementary OEM manuals and incident reports."
            )
            return support_level, available_features, warnings, recommendations

        # Full support
        support_level = "full"
        available_features = {
            "parse": True,
            "entity_extraction": True,
            "relationship_extraction": True,
            "graph_evolution": True,
            "reasoning": True,
        }
        return support_level, available_features, warnings, recommendations
