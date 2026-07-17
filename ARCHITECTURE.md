# ForgeMind Architecture Documentation

ForgeMind is designed as a production-ready **Modular Monolith** using **Domain-Driven Design (DDD)** and **Hexagonal Architecture** (Ports and Adapters). It prioritizes absolute predictability, deterministic reasoning, and auditability for high-reliability industrial operations.

---

## 1. System Overview

ForgeMind transforms raw, unstructured operational files (manuals, telemetry incidents, inspection logs) into an active, self-correcting **Industrial Knowledge Graph**. 

```
 ┌───────────────────┐      ┌────────────────────────┐      ┌─────────────────────────┐
 │ Ingest documents  │ ───> │ Extract semantic nodes │ ───> │ Compare & evolve graph  │
 │ (PDF / Raw text)  │      │ & relationships        │      │ (Confidence/Timeline)   │
 └───────────────────┘      └────────────────────────┘      └─────────────────────────┘
                                                                        │
 ┌───────────────────┐      ┌────────────────────────┐                  │
 │ Decision Output   │ <─── │ Multi-hop deterministic│ <────────────────┘
 │ (Severity/Impact) │      │ RCA Graph Traversal    │
 └───────────────────┘      └────────────────────────┘
```

---

## 2. Hexagonal Architecture (Ports & Adapters)

To prevent framework lock-in and database dependency creep, the codebase is strictly segregated into three architectural rings:

1. **Domain (Core Ring)**: Contains the pure business models, state rules, value objects, and domain events.
   - Zero external library dependencies (except standard typing).
   - Entirely side-effect free.
2. **Ports (Interface Ring)**: `typing.Protocol` declarations defining inbound contracts (what operations are possible) and outbound contracts (what external infrastructure resources are needed).
3. **Adapters (Infrastructure Ring)**: Implementation details that fulfill the port interfaces.
   - Examples: `PdfDocumentParser` using `pdfplumber`, `NetworkXGraphRepository` using in-memory NetworkX, and FastAPI routes serving standard REST.

### Directory Segregation
Each context follows this pattern:
```
src/forgemind/<bounded_context>/
├── domain/
│   ├── entities.py       # Entity classes (e.g. Document, KnowledgeEntity)
│   ├── value_objects.py  # Types (e.g. EntityType, RelationType)
│   └── services.py       # Domain logic (e.g. merge_entities)
├── ports/
│   ├── inbound.py        # Inbound Protocol interfaces
│   └── outbound.py       # Outbound Protocol interfaces
└── adapters/
    ├── memory_repo.py    # Local repositories
    └── services.py       # Implementation orchestrators
```

---

## 3. Bounded Contexts

ForgeMind is organized into four distinct domain contexts, communicating primarily via clean APIs or domain events:

### A. Knowledge Context
- **Responsibility**: Ingests document streams, splits them into sentence-boundary chunks, and runs pattern-based entity extraction.
- **Key Entities**:
  - `Document`: Represents the source text file, tracking content hash for deduplication.
  - `Chunk`: Text fragment mapped to specific pages and offsets.
  - `KnowledgeEntity`: Semantically typed extracted nodes (Asset, Component, Symptom, Action, etc.).

### B. Graph Context
- **Responsibility**: Maintains the semantic network of entities and relationships.
- **Key Adapters**:
  - `NetworkXGraphRepository`: Fulfills the graph storage contract, enabling thread-safe insertions and neighbor lookups.

### C. Ingestion & In-Memory Storage
- **Responsibility**: Manages high-efficiency in-memory storage indexes.
- **Key Repositories**:
  - `InMemoryDocumentRepository`: Thread-safe dictionary storing documents by ID and tracking duplicate content hashes.
  - `InMemoryChunkRepository`: Relational index pairing chunk IDs to their parent documents.

### D. Reasoning Context
- **Responsibility**: Runs deterministic multi-hop graph traversals. Answers user diagnostic queries by tracking causal chains:
  `Asset` ──[has_symptom]──> `Symptom` ──[caused_by]──> `Component` ──[resolves]──> `Action`

---

## 4. Evolving Knowledge Timeline & Contradiction Engine

A core differentiator of ForgeMind is its ability to handle **conflicting information** over time (e.g., a manual says *Pump operating limit is 80°C*, but a post-incident log reports *normal operating limit is 85°C*).

### Resolution Protocol:
1. **Contradiction Detection**: On new document ingestion, the engine checks for interval overlaps (e.g., operating temperatures) or parameter mismatches between new and existing entities.
2. **Provenance Weighting**: Normalizer uses reliability weights based on the source document type:
   - `INSPECTION_REPORT` > `INCIDENT_REPORT` > `MANUAL`
3. **Graph Evolution**: Updates the active confidence score of the parameter and logs a `contradiction_detected` event.

---

## 5. Explainable Reasoning Traversal

Unlike non-deterministic LLMs, ForgeMind's **Reasoning Engine** is 100% deterministic and auditable. Every decision intelligence recommendation is backed by a structured proof chain:

- **Evidence Links**: An explicit list of edges traversed in the graph.
- **Confidence Breakdown**: Calculated aggregate probability based on edge confidence and source document verification counts.
- **Business Impact**: Evaluates risk categories, priority triggers, and downtime metrics to output a high-fidelity decision card.

---

## 6. Architectural Decision Records (ADRs)
The system development history is governed by ADR files located in `docs/adr/`:
- **ADR-0001**: Modular Monolith for developer velocity and zero-dependency deployments.
- **ADR-0002**: Hexagonal isolation of the domain models.
- **ADR-0004**: NetworkX as the baseline in-memory graph repository.
- **ADR-0005**: Vector embeddings + Graph search hybrid retrieval setup.
