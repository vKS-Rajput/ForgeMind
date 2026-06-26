# ForgeMind

> **Industrial knowledge management through knowledge graphs, hybrid retrieval, and explainable AI reasoning.**

ForgeMind ingests industrial maintenance documents (manuals, incident reports, work orders), extracts entities and relationships into a knowledge graph, and answers diagnostic questions with graph-backed, explainable reasoning.

## What Problem Does ForgeMind Solve?

Industrial organizations lose critical maintenance knowledge when experienced engineers leave. Equipment manuals sit in filing cabinets. Incident reports are filed and forgotten. The same failures repeat because the organization has no memory.

ForgeMind captures this knowledge in a graph, connects it across documents and time, and makes it queryable through natural language — with every answer traceable back to its source.

## Quick Start

```bash
# Prerequisites: Python 3.12+, uv (https://docs.astral.sh/uv/)

# Clone and setup
git clone <repository-url>
cd ForgeMind
uv sync --all-extras

# Install git hooks
uv run pre-commit install

# Copy environment config
cp .env.example .env
# Edit .env to add your OpenAI API key (or configure Ollama)

# Run tests
uv run pytest -m unit           # Fast unit tests (~2s)
uv run pytest -m architecture   # Architectural boundary tests
uv run pytest                   # All tests

# Run the application (Phase 8+)
# uv run uvicorn forgemind.api.main:app --reload
```

## Architecture

ForgeMind is a **modular monolith** using **hexagonal architecture** (ports & adapters), organized by **bounded contexts**:

```
┌─────────────────────────────────────────────────────┐
│                    API Layer                         │
│              (FastAPI, composition root)             │
├──────────┬──────────┬───────────┬───────────────────┤
│Knowledge │  Graph   │ Retrieval │    Reasoning      │
│ Context  │ Context  │  Context  │     Context       │
│          │          │           │                   │
│ domain/  │ domain/  │ domain/   │ domain/           │
│ ports/   │ ports/   │ ports/    │ ports/            │
│ adapters/│ adapters/│ adapters/ │ adapters/         │
├──────────┴──────────┴───────────┴───────────────────┤
│                  Shared Module                       │
│         (types, errors, logging, config)             │
└─────────────────────────────────────────────────────┘
```

Each bounded context follows the hexagonal pattern:
- **Domain**: Pure business logic. No I/O, no framework imports.
- **Ports**: `Protocol` interfaces defining how the domain talks to the outside world.
- **Adapters**: Concrete implementations (NetworkX, ChromaDB, OpenAI, etc.)

## Project Structure

```
src/forgemind/
├── shared/         # Cross-cutting: types, errors, logging, config
├── knowledge/      # Document ingestion, entity & relationship extraction
├── graph/          # Knowledge graph construction & querying
├── retrieval/      # Hybrid vector + graph retrieval with RRF fusion
├── reasoning/      # LLM reasoning with graph-backed explanations
└── api/            # FastAPI routes, schemas, dependency injection
```

## Key Technologies

| Component | Technology | Why |
| :--- | :--- | :--- |
| Language | Python 3.12+ | AI/ML ecosystem, fast iteration |
| Package Manager | uv | 10-100x faster than pip, lockfile support |
| Web Framework | FastAPI | Async, type-safe, auto-generated OpenAPI docs |
| Graph Store | NetworkX (V1) → Neo4j (V2) | Zero-infrastructure MVP, production-grade migration path |
| Vector Store | ChromaDB | Embedded, persistent, zero-infrastructure |
| Embeddings | sentence-transformers | Fast, small, GPU-optional |
| LLM | OpenAI / Ollama | Cloud + offline fallback |
| Linting | ruff | Replaces black + isort + flake8 in one tool |
| Type Checking | mypy (strict) | Catch bugs before runtime |

## Architecture Decision Records

See [docs/adr/](docs/adr/) for all architectural decisions:

- [ADR-0001: Modular Monolith](docs/adr/0001-modular-monolith.md)
- [ADR-0002: Hexagonal Architecture](docs/adr/0002-hexagonal-architecture.md)
- [ADR-0003: Python as Primary Language](docs/adr/0003-python-primary-language.md)
- [ADR-0004: Graph Storage Strategy](docs/adr/0004-graph-storage-strategy.md)
- [ADR-0005: Hybrid Retrieval](docs/adr/0005-hybrid-retrieval.md)
- [ADR-0006: Vertical Slice Development](docs/adr/0006-vertical-slice-development.md)
- [ADR-0007: Knowledge-First Domain Model](docs/adr/0007-knowledge-first-domain-model.md)

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for setup instructions, coding standards, and PR guidelines.

## License

MIT — see [LICENSE](LICENSE).
