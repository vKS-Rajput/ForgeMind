# Getting Started with ForgeMind

Welcome! This guide will get you from zero to contributor in one day.

## Hour 1: Environment Setup

```bash
# Install Python 3.12+ and uv
# See: https://docs.astral.sh/uv/getting-started/installation/

git clone <repository-url>
cd ForgeMind
uv sync --all-extras
uv run pre-commit install
cp .env.example .env

# Verify everything works
uv run pytest -m unit
```

## Hour 2: Understand the Architecture

Read these in order:
1. [Architecture Overview](../architecture/overview.md) — System diagram and data flow
2. The bounded contexts in `src/forgemind/` — Knowledge, Graph, Retrieval, Reasoning, API

## Hour 3: Understand the Decisions

Read the ADRs in `docs/adr/`:
1. [ADR-0001: Modular Monolith](../adr/0001-modular-monolith.md)
2. [ADR-0002: Hexagonal Architecture](../adr/0002-hexagonal-architecture.md)
3. [ADR-0003: Python](../adr/0003-python-primary-language.md)
4. [ADR-0004: Graph Storage](../adr/0004-graph-storage-strategy.md)
5. [ADR-0005: Hybrid Retrieval](../adr/0005-hybrid-retrieval.md)
6. [ADR-0006: Vertical Slices](../adr/0006-vertical-slice-development.md)
7. [ADR-0007: Knowledge-First](../adr/0007-knowledge-first-domain-model.md)

## Hour 4: Know the Standards

Read [Python Engineering Standards](../standards/python-engineering-standards.md).

Key rules:
- Type hints on all public functions
- Google-style docstrings
- Max 25 lines per function, max 300 lines per module
- Domain code is pure — no I/O, no framework imports

## Hours 5-6: Read One Bounded Context

Pick any bounded context (e.g., `knowledge/`) and read through:
1. `domain/entities.py` — What are the domain objects?
2. `domain/services.py` — What are the business rules?
3. `ports/inbound.py` — What use cases exist?
4. `ports/outbound.py` — What dependencies are needed?
5. `adapters/` — How are dependencies implemented?

## Hour 7: See It Run

```bash
# Run the demo (once the system is built beyond Phase 0)
# uv run python -m forgemind.api.main

# Run the full test suite
uv run pytest
```

## Hour 8: Your First Contribution

1. Check for issues labeled `good-first-issue`
2. Create a branch: `git checkout -b feature/your-change`
3. Make your change following the standards
4. Run: `uv run pytest && uv run ruff check . && uv run mypy src/`
5. Submit a PR using the template

Welcome aboard! 🚀
