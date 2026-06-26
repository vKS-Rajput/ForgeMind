# ForgeMind Architecture Overview

## System Architecture

ForgeMind is a **modular monolith** using **hexagonal architecture** (ports & adapters), organized by **Domain-Driven Design** bounded contexts.

```
┌──────────────────────────────────────────────────────────────────┐
│                         API Layer                                │
│                    (FastAPI composition root)                     │
│    POST /documents    POST /query    GET /graph    GET /health   │
├──────────────┬──────────────┬──────────────┬────────────────────-┤
│  Knowledge   │    Graph     │  Retrieval   │     Reasoning       │
│   Context    │   Context    │   Context    │      Context        │
│              │              │              │                     │
│ ┌──────────┐ │ ┌──────────┐ │ ┌──────────┐ │ ┌──────────┐       │
│ │  domain  │ │ │  domain  │ │ │  domain  │ │ │  domain  │       │
│ │(entities,│ │ │(entities,│ │ │(entities,│ │ │(entities,│       │
│ │ services)│ │ │ services)│ │ │ services)│ │ │ services)│       │
│ ├──────────┤ │ ├──────────┤ │ ├──────────┤ │ ├──────────┤       │
│ │  ports   │ │ │  ports   │ │ │  ports   │ │ │  ports   │       │
│ │(Protocol)│ │ │(Protocol)│ │ │(Protocol)│ │ │(Protocol)│       │
│ ├──────────┤ │ ├──────────┤ │ ├──────────┤ │ ├──────────┤       │
│ │ adapters │ │ │ adapters │ │ │ adapters │ │ │ adapters │       │
│ │(pdfplumb)│ │ │(NetworkX)│ │ │(ChromaDB)│ │ │(OpenAI)  │       │
│ └──────────┘ │ └──────────┘ │ └──────────┘ │ └──────────┘       │
├──────────────┴──────────────┴──────────────┴────────────────────-┤
│                        Shared Module                             │
│               (types, errors, logging, config)                   │
└──────────────────────────────────────────────────────────────────┘
```

## Data Flow

```
Document (PDF)
     │
     ▼
[Document Parser] ──→ Raw Text
     │
     ▼
[Chunker] ──→ Chunks (with embeddings)
     │
     ├──→ [Vector Store (ChromaDB)] ──→ Stored embeddings
     │
     ▼
[Entity Extractor] ──→ Entities (Assets, Components, FailureModes...)
     │
     ▼
[Relationship Extractor] ──→ Relationships (causes, resolved_by...)
     │
     ▼
[Graph Constructor] ──→ Knowledge Graph (NetworkX)
     │
     ▼ (at query time)
[User Query]
     │
     ├──→ [Vector Search] ──→ Top-K similar chunks
     │
     ├──→ [Graph Search] ──→ Related entities & causal paths
     │
     ▼
[RRF Fusion] ──→ Unified context
     │
     ▼
[LLM Reasoning] ──→ Structured answer with citations & explanations
```

## Dependency Direction

Dependencies always point **inward** toward the domain:

- **Domain**: Depends on nothing (pure Python, no imports from adapters/frameworks)
- **Ports**: Depend only on domain types
- **Adapters**: Depend on ports and domain
- **API**: Depends on everything (it's the composition root)

This is enforced by architectural tests in `tests/architecture/test_boundaries.py`.

## Bounded Contexts

| Context | Responsibility | V1 Status |
| :--- | :--- | :--- |
| **Knowledge** | Document ingestion, chunking, entity & relationship extraction | Core |
| **Graph** | Knowledge graph construction, storage, querying | Core |
| **Retrieval** | Hybrid vector + graph search, RRF fusion | Core |
| **Reasoning** | LLM prompt construction, response parsing, explanation building | Core |
| **API** | REST endpoints, request/response schemas, dependency injection | Core |

## Key Decisions

See [ADRs](../adr/) for detailed rationale behind each architectural decision.
