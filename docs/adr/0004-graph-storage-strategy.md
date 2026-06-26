# ADR-0004: Graph Storage Strategy (NetworkX → Neo4j)

**Status**: Accepted

**Date**: 2026-06-26

**Deciders**: ForgeMind Engineering Team

## Context

ForgeMind's knowledge graph is the system's core data structure. It must support entity storage, relationship traversal, path queries, and neighborhood exploration. V1 scale is small (hundreds to low thousands of nodes), but the architecture must support migration to a production graph database.

## Decision

Use **NetworkX** for V1 with a `GraphRepository` protocol that abstracts all graph operations. Design the protocol to be compatible with Neo4j's capabilities. Implement a **Neo4j adapter** in V2.

V1 persistence: NetworkX graph serialized to JSON on disk.

## Alternatives Considered

| Alternative | Why Rejected |
| :--- | :--- |
| **Neo4j from day one** | Requires Docker/server, adds operational complexity for V1 |
| **Memgraph** | Similar infrastructure burden as Neo4j |
| **SQLite + adjacency table** | Graph traversal in SQL is verbose and slow |
| **Pure dict/JSON structures** | No graph algorithms, no traversal helpers |

## Consequences

### Positive
- Zero infrastructure — runs on any machine with Python
- Full graph algorithm library available immediately
- Port interface designed for Neo4j compatibility

### Negative
- In-memory only — data loss without serialization (mitigated by periodic JSON export)
- Not suitable for concurrent multi-user access (acceptable for V1 single-user demo)
- Scales to ~100K nodes before memory pressure (far beyond V1 needs)

### Migration Strategy (V1 → V2)
1. Implement `Neo4jGraphRepository` adapter implementing `GraphRepository` protocol
2. Add Neo4j connection config to settings
3. Migration script: export NetworkX JSON → Neo4j Cypher CREATE statements
4. Switch dependency injection to use Neo4j adapter
5. No domain logic changes required
