# ADR-0002: Hexagonal Architecture (Ports & Adapters)

**Status**: Accepted

**Date**: 2026-06-26

**Deciders**: ForgeMind Engineering Team

## Context

ForgeMind must be technology-agnostic at its core. The knowledge graph might start with NetworkX and migrate to Neo4j. The vector store might start with ChromaDB and move to Pinecone. The LLM might be OpenAI today and a local model tomorrow. We need an architecture that isolates technology choices from business logic.

## Decision

Implement **hexagonal architecture** within each bounded context. Every external dependency is accessed through a **port** (`typing.Protocol`) with a concrete **adapter** implementation.

### Structure per Bounded Context

```
context_name/
├── domain/          # Pure business logic, no external dependencies
│   ├── entities.py  # Domain entities and value objects
│   ├── services.py  # Domain services (business rules)
│   └── events.py    # Domain events
├── ports/
│   ├── inbound.py   # How the outside world calls this module
│   └── outbound.py  # How this module calls external systems
└── adapters/        # Concrete implementations
```

## Alternatives Considered

| Alternative | Why Rejected |
| :--- | :--- |
| **Clean Architecture (Uncle Bob)** | More layers than needed at our scale. Hexagonal is equivalent but simpler in Python. |
| **Simple layered (Controller → Service → Repository)** | Technology bleeds into business logic. Difficult to swap implementations. |
| **No formal architecture** | Technical debt accumulates exponentially. |

## Consequences

### Positive
- Technology can change without touching business logic
- Every module is testable in isolation (mock the ports)
- Clear dependency direction (always inward toward domain)

### Negative
- More files than a flat structure
- Requires developers to understand the pattern
