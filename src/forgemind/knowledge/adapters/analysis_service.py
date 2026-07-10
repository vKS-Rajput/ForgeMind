"""Document analysis service — extracts insights from ingested documents.

This service provides pattern-based analysis of document content,
extracting meaningful entities like equipment names, operating parameters,
failure symptoms, and maintenance actions.

Architecture:
  - READ-ONLY service — does not modify stored documents.
  - Normalizes raw PDF text (removes line-break artifacts) before analysis.
  - Patterns are deterministic, fast, and explainable.
  - No external API calls or dependencies required.

Bounded Context: Knowledge
Layer: Adapters (Application Service)
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

# ══════════════════════════════════════════════════════════════════
# Text Normalization
# ══════════════════════════════════════════════════════════════════
# PDF extractors (pdfplumber, PyMuPDF) insert newlines at visual
# line breaks within a paragraph. These mid-sentence newlines
# corrupt regex matches (e.g. "valve\nPSV-101" instead of
# "valve PSV-101"). We normalize BEFORE running any patterns.


def _normalize_text(text: str) -> str:
    """Normalize PDF-extracted text for reliable pattern matching.

    Applies these transformations in order:
      1. Replace mid-sentence newlines with spaces.
         A mid-sentence newline is one NOT followed by a blank line
         or a section heading (uppercase word / numbered heading).
      2. Collapse multiple spaces into one.
      3. Strip leading/trailing whitespace.

    Args:
        text: Raw text from PDF extraction, may contain line-break artifacts.

    Returns:
        Cleaned text with single-space word separators.
    """
    # Step 1: Replace single newlines (mid-paragraph breaks) with spaces.
    # Preserve paragraph boundaries (double newlines).
    result = re.sub(r"(?<!\n)\n(?!\n)", " ", text)

    # Step 2: Collapse multiple spaces into one.
    result = re.sub(r" {2,}", " ", result)

    return result.strip()


# ══════════════════════════════════════════════════════════════════
# Regex Patterns
# ══════════════════════════════════════════════════════════════════
# Each pattern targets a specific type of industrial knowledge.
# Patterns are designed to be precise enough to avoid noise while
# being broad enough to catch common variants.

# Equipment: "Pump P-101", "Motor M-205", "Valve V-300"
# Captures the type name + alphanumeric tag. The tag must start
# with a letter and contain at least one digit.
_EQUIPMENT_PATTERN = re.compile(
    r"\b((?:Pump|Motor|Valve|Compressor|Fan|Blower|Turbine|Generator|"
    r"Heat Exchanger|Bearing|Impeller|Seal|Coupling|Shaft|Filter|"
    r"Strainer|Tank|Vessel|Reactor|Column|Conveyor|Gearbox)"
    r"\s+[A-Z][\w]*-\d+[A-Za-z0-9]*)\b",
    re.IGNORECASE,
)

# Part/model numbers: "SKF 6205-2RS", "John Crane Type 2100",
# "AISI 4140", "Grade 25". Captures manufacturer + model only,
# stopping at sentence-ending punctuation or common stop words.
_PART_NUMBER_PATTERN = re.compile(
    r"\b((?:SKF|NSK|FAG|NTN|Timken|John Crane|Flowserve|"
    r"Grundfos|KSB|Sulzer|ABB|Siemens|WEG|Shell)"
    r"\s+[\w][\w./-]*(?:\s+[\w./-]+)?)\b",
    re.IGNORECASE,
)

# Material/standard designations: "AISI 4140", "ASTM A105", "Grade 25",
# "316L stainless steel", "API 610"
_MATERIAL_PATTERN = re.compile(
    r"\b((?:AISI|ASTM|API|Grade|Type)\s+[\w]+(?:\s+[\w]+)?)\b",
    re.IGNORECASE,
)

# Safety instrument tags: "PSV-101", "FS-101", "PT-205"
# Must be 2-4 uppercase letters, dash, 2-4 digits.
_INSTRUMENT_TAG_PATTERN = re.compile(r"\b([A-Z]{2,4}-\d{2,4}[A-Za-z]?)\b")

# Numeric parameters with units: "3000 RPM", "80 degrees Celsius",
# "4.5 mm/s", "150 cubic meters per hour"
_PARAMETER_PATTERN = re.compile(
    r"\b(\d+(?:\.\d+)?\s*(?:RPM|bar|psi|kW|MW|HP|"
    r"degrees?\s+(?:Celsius|Fahrenheit|C|F)|"
    r"cubic\s+meters?\s+per\s+hour|m3/h|l/min|"
    r"mm/s|m/s|Hz|kHz|"
    r"percent|%|ml\b))\b",
    re.IGNORECASE,
)

# Dimension parameters: "0.05 mm", "45 meters", "0.5 mm"
_DIMENSION_PATTERN = re.compile(
    r"\b(\d+(?:\.\d+)?\s*(?:mm|cm|meters?|m|kg|hours?|minutes?|seconds?))\b",
    re.IGNORECASE,
)

# Symptom phrases
_SYMPTOM_KEYWORDS: list[str] = [
    "excessive vibration",
    "high bearing temperature",
    "high temperature",
    "reduced flow rate",
    "low flow",
    "seal leakage",
    "mechanical seal leakage",
    "abnormal noise",
    "cavitation",
    "overheating",
    "shaft misalignment",
    "bearing failure",
    "bearing degradation",
    "impeller wear",
    "erosion damage",
    "corrosion",
    "fatigue crack",
    "oil leak",
    "pressure drop",
    "flow instability",
]

# Action verbs for identifying corrective action sentences
_ACTION_VERBS: list[str] = [
    "replace",
    "inspect",
    "check",
    "verify",
    "lubricate",
    "re-lubricate",
    "clean",
    "tighten",
    "align",
    "calibrate",
    "shut down",
    "reduce speed",
    "schedule",
    "measure",
    "perform",
    "disassemble",
    "overhaul",
]


# ══════════════════════════════════════════════════════════════════
# Data Structures
# ══════════════════════════════════════════════════════════════════


@dataclass(frozen=True, slots=True)
class DocumentInsights:
    """Extracted insights from a document's content.

    Each field contains a deduplicated, sorted list of extracted items.
    All text is cleaned — no newlines, no trailing noise.
    """

    equipment: list[str] = field(default_factory=list)
    parts: list[str] = field(default_factory=list)
    materials: list[str] = field(default_factory=list)
    instruments: list[str] = field(default_factory=list)
    parameters: list[str] = field(default_factory=list)
    symptoms: list[str] = field(default_factory=list)
    actions: list[str] = field(default_factory=list)
    key_sentences: list[str] = field(default_factory=list)
    summary_stats: dict[str, int | str] = field(default_factory=dict)


# ══════════════════════════════════════════════════════════════════
# Analyzer
# ══════════════════════════════════════════════════════════════════


class DocumentAnalyzer:
    """Extracts structured insights from document text using patterns.

    The analyzer first normalizes raw PDF text (removes line-break
    artifacts), then applies regex patterns and keyword matching
    to extract equipment, parts, parameters, symptoms, and actions.

    Thread Safety:
        Stateless and thread-safe. No mutable state.

    Example:
        >>> analyzer = DocumentAnalyzer()
        >>> insights = analyzer.analyze_text("Pump P-101 operates at 3000 RPM.")
        >>> insights.equipment
        ['Pump P-101']
        >>> insights.parameters
        ['3000 RPM']
    """

    def analyze_text(self, text: str) -> DocumentInsights:
        """Extract insights from a block of text.

        The text is normalized first (newlines removed, whitespace
        collapsed), then scanned for entities. Results are
        deduplicated and sorted.

        Args:
            text: Raw text to analyze (typically from PDF extraction).

        Returns:
            DocumentInsights with all extracted entities.
        """
        if not text.strip():
            return DocumentInsights()

        # ── Normalize text before pattern matching ───────────────
        clean_text = _normalize_text(text)

        # ── Extract entities ─────────────────────────────────────
        equipment = _deduplicate_matches(_EQUIPMENT_PATTERN.findall(clean_text))
        parts = _deduplicate_matches(_PART_NUMBER_PATTERN.findall(clean_text))
        materials = _deduplicate_matches(_MATERIAL_PATTERN.findall(clean_text))
        instruments = _deduplicate_matches(_INSTRUMENT_TAG_PATTERN.findall(clean_text))
        parameters = _deduplicate_matches(
            _PARAMETER_PATTERN.findall(clean_text) + _DIMENSION_PATTERN.findall(clean_text)
        )

        # ── Find symptoms ────────────────────────────────────────
        text_lower = clean_text.lower()
        symptoms = [keyword.title() for keyword in _SYMPTOM_KEYWORDS if keyword in text_lower]

        # ── Find action sentences ────────────────────────────────
        sentences = _split_into_sentences(clean_text)
        action_sentences = _extract_action_sentences(sentences)

        # ── Find key sentences ───────────────────────────────────
        key_sentences = _find_key_sentences(sentences, max_count=5)

        # ── Compute statistics ───────────────────────────────────
        word_count = len(clean_text.split())
        summary_stats: dict[str, int | str] = {
            "total_characters": len(clean_text),
            "total_words": word_count,
            "total_sentences": len(sentences),
            "equipment_found": len(equipment),
            "parts_found": len(parts),
            "materials_found": len(materials),
            "instruments_found": len(instruments),
            "parameters_found": len(parameters),
            "symptoms_found": len(symptoms),
            "actions_found": len(action_sentences),
        }

        return DocumentInsights(
            equipment=equipment,
            parts=parts,
            materials=materials,
            instruments=instruments,
            parameters=parameters,
            symptoms=symptoms,
            actions=action_sentences,
            key_sentences=key_sentences,
            summary_stats=summary_stats,
        )


# ══════════════════════════════════════════════════════════════════
# Private Helpers
# ══════════════════════════════════════════════════════════════════


def _deduplicate_matches(matches: list[str]) -> list[str]:
    """Remove duplicates, clean whitespace, filter noise, sort.

    Args:
        matches: Raw regex matches, possibly with duplicates.

    Returns:
        Sorted, deduplicated, cleaned list of matches.
    """
    seen: set[str] = set()
    unique: list[str] = []

    for match in matches:
        # Clean: collapse whitespace, strip, remove trailing punctuation
        cleaned = re.sub(r"\s+", " ", match).strip().rstrip(".,;:")
        if len(cleaned) < 3:
            continue
        key = cleaned.lower()
        if key not in seen:
            seen.add(key)
            unique.append(cleaned)

    return sorted(unique)


def _split_into_sentences(text: str) -> list[str]:
    """Split text into sentences using punctuation boundaries.

    Args:
        text: Normalized text (no mid-sentence newlines).

    Returns:
        List of non-empty sentences with at least 10 characters.
    """
    raw_sentences = re.split(r"(?<=[.!?])\s+", text)
    return [s.strip() for s in raw_sentences if len(s.strip()) > 10]


def _extract_action_sentences(sentences: list[str]) -> list[str]:
    """Find sentences describing corrective or maintenance actions.

    Returns full sentences for context, truncated to 200 chars.
    Limited to top 10 most relevant.

    Args:
        sentences: List of sentences to scan.

    Returns:
        List of action-containing sentences.
    """
    results: list[str] = []

    for sentence in sentences:
        sentence_lower = sentence.lower()
        for verb in _ACTION_VERBS:
            if verb in sentence_lower and sentence not in results:
                truncated = sentence[:200] + "..." if len(sentence) > 200 else sentence
                results.append(truncated)
                break

    return results[:10]


def _find_key_sentences(sentences: list[str], max_count: int = 5) -> list[str]:
    """Find the most information-dense sentences.

    Scores each sentence by the number of entities it contains.
    Returns the top-scoring sentences in original document order.

    Args:
        sentences: All sentences from the document.
        max_count: Maximum number of key sentences to return.

    Returns:
        Top-scoring sentences, truncated to 250 chars.
    """

    def _score(sentence: str) -> int:
        score = 0
        score += len(_EQUIPMENT_PATTERN.findall(sentence)) * 3
        score += len(_PART_NUMBER_PATTERN.findall(sentence)) * 2
        score += len(_PARAMETER_PATTERN.findall(sentence)) * 2
        score += len(_INSTRUMENT_TAG_PATTERN.findall(sentence))
        s_lower = sentence.lower()
        score += sum(2 for k in _SYMPTOM_KEYWORDS if k in s_lower)
        score += sum(1 for v in _ACTION_VERBS if v in s_lower)
        return score

    scored = [(i, s, _score(s)) for i, s in enumerate(sentences)]
    scored.sort(key=lambda x: x[2], reverse=True)
    top = scored[:max_count]
    top.sort(key=lambda x: x[0])

    return [s[:250] + "..." if len(s) > 250 else s for _, s, score in top if score > 0]
