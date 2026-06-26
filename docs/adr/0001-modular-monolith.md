# ADR-0001: Modular Monolith Architecture

**Status**: Accepted

**Date**: 2026-06-26

**Deciders**: ForgeMind Engineering Team

## Context

ForgeMind is a new system being built by a small team (1-3 developers). The system has multiple concerns (ingestion, extraction, graph construction, retrieval, reasoning) that could be implemented as microservices or as a monolith. We need to balance development velocity with architectural clarity.

## Decision

Implement ForgeMind as a **modular monolith**. The codebase is a single deployable unit, but internal modules are organized by bounded context with strict dependency rules. Each module exposes internal APIs (Python interfaces) and owns its data.

## Alternatives Considered

| Alternative | Pros | Cons | Why Rejected |
| :--- | :--- | :--- | :--- |
| **Microservices** | Independent scaling, technology diversity | Massive infrastructure overhead, network latency, distributed debugging | Team of 1-3 cannot absorb the operational cost |
| **Traditional Monolith** | Simple, familiar | Modules become coupled, difficult to test in isolation | Doesn't enforce boundaries needed for future extraction |
| **Serverless Functions** | Zero infrastructure, pay-per-use | Cold starts, state management complexity | Knowledge graph requires persistent state |

## Consequences

### Positive
- Single deployment unit — simple CI/CD, simple debugging
- Module boundaries enforced by import rules (pytest-archon)
- Any module can be extracted to a service later via its port interface

### Negative
- Requires discipline — no compile-time boundary enforcement in Python
- All modules scale together (acceptable at V1 scale)

### Migration Strategy
When a module needs independent scaling (likely: Reasoning engine due to LLM latency):
1. The port interface already exists
2. Create a new service implementing the same port
3. Replace the in-process adapter with an HTTP/gRPC adapter
4. Deploy independently
