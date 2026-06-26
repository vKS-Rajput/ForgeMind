# ADR-0005: Hybrid Retrieval Architecture

**Status**: Accepted

**Date**: 2026-06-26

**Deciders**: ForgeMind Engineering Team

## Context

ForgeMind must answer questions requiring both semantic understanding (finding relevant text) and structural understanding (traversing entity relationships). Neither vector search alone nor graph search alone is sufficient.

## Decision

Implement **hybrid retrieval** combining vector similarity search and knowledge graph traversal, fused using **Reciprocal Rank Fusion (RRF)**.

### Architecture

```
User Query
    ├── Vector Search → Embed query → ChromaDB → Top-K chunks
    ├── Graph Search  → Extract entities → N-hop traversal → Related entities
    └── Fusion (RRF)  → Merge rankings → Unified context → LLM Reasoning
```

## Alternatives Considered

| Alternative | Why Rejected |
| :--- | :--- |
| **Vector search only (standard RAG)** | Misses relationships. Not a differentiator. |
| **Graph search only** | Can't handle natural language queries |
| **LLM-driven query routing** | Too complex for V1, adds latency |
| **Knowledge graph embeddings (TransE)** | Research-heavy, overkill for V1 scale |

## Consequences

### Positive
- Clear advantage over vanilla RAG (the key differentiator)
- Explainable: "found via text similarity" vs "found via graph traversal"
- RRF is parameter-light and well-understood

### Negative
- Two retrieval paths = two things to debug
- Entity extraction from user query must work for graph search to be effective
