# ADR-0007: Knowledge-First Domain Model

**Status**: Accepted

**Date**: 2026-06-26

**Deciders**: ForgeMind Engineering Team

## Context

ForgeMind could be modeled around many concepts: documents, assets, incidents, users, workflows. We need to decide the primary entity — the one around which all others orbit.

## Decision

The primary domain concept is **Knowledge** — extracted entities and their relationships forming a graph. All other concepts (documents, assets, incidents) are either *sources of knowledge* or *consumers of knowledge*.

### Model Hierarchy

```
Knowledge (core)
├── Entities (the nodes)
├── Relationships (the edges)
└── Provenance (where knowledge came from)
    ├── Documents (sources)
    └── Extractions (how knowledge was derived)
```

## Alternatives Considered

| Alternative | Why Rejected |
| :--- | :--- |
| **Document-first** | Documents are input, not value. Users want answers, not documents. |
| **Asset-first** | Too narrow. Limits system to asset-centric queries. |
| **Event-first** | Events are one type of knowledge, not all knowledge. |

## Consequences

### Positive
- The knowledge graph is the system's primary artifact, not a side effect
- Every feature is evaluated by: "Does this add knowledge to the graph?"
- Clean separation: documents are sources, the graph is knowledge, answers are products

### Negative
- Requires discipline to keep domain entities pure and not model them as "document containers"
