# ADR-0003: Python as Primary Language

**Status**: Accepted

**Date**: 2026-06-26

**Deciders**: ForgeMind Engineering Team

## Context

ForgeMind is an AI-heavy system requiring NLP, embedding generation, graph manipulation, and LLM integration. The team needs a language with strong ecosystem support for all of these.

## Decision

Use **Python 3.12+** as the primary and sole language for V1.

## Alternatives Considered

| Alternative | Why Rejected |
| :--- | :--- |
| **TypeScript/Node.js** | Weak ML/NLP ecosystem, graph libraries immature |
| **Rust** | Small ML ecosystem, steep learning curve, slow development velocity |
| **Java/Kotlin** | Verbose, ML ecosystem requires JNI bridges |
| **Go** | Minimal ML ecosystem |

## Consequences

### Positive
- Direct access to spaCy, sentence-transformers, NetworkX, ChromaDB, and every major AI library
- Fast development iteration
- Large talent pool

### Negative
- Performance bottlenecks possible (mitigated by profiling and compiled libraries)
- Type safety is opt-in (mitigated by `mypy --strict`)
- GIL limits true parallelism (mitigated by async I/O for LLM calls)

### Migration Strategy
If performance-critical components emerge:
1. Rewrite as Rust extensions using PyO3/maturin
2. Extract to a separate service (the port already exists)
3. Replace with C-extension libraries (e.g., igraph instead of NetworkX)
