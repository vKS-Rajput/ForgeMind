# ADR-0006: Vertical Slice Development

**Status**: Accepted

**Date**: 2026-06-26

**Deciders**: ForgeMind Engineering Team

## Context

We need to decide whether to build ForgeMind by completing each architectural layer fully (horizontal) or by building one complete end-to-end path first (vertical).

## Decision

Use **vertical slice development**. Build one complete path (PDF → Chunking → Extraction → Graph → Retrieval → Reasoning → Answer) before widening to additional document types or entity types.

## Alternatives Considered

| Alternative | Why Rejected |
| :--- | :--- |
| **Horizontal (build all layers partially)** | No working demo until everything is done. Integration problems discovered late. Catastrophic for hackathon. |

## Consequences

### Positive
- Working demo available early
- Integration issues discovered immediately
- Each phase produces a testable, demonstrable increment

### Negative
- Some horizontal refactoring needed when widening (acceptable — this is informed refactoring)

### Planned Slices

1. **Slice 1 (Core)**: Pump maintenance manual → Entity extraction → Knowledge graph → "What causes P-101 to overheat?" → Explainable answer
2. **Slice 2 (Widening)**: Incident reports → Temporal patterns → "Most common root cause for compressor failures?"
3. **Slice 3 (Deepening)**: New symptom → Graph traversal → Proactive root-cause suggestions
