# Contributing to ForgeMind

Thank you for your interest in contributing to ForgeMind! This document provides guidelines and instructions for contributing.

## Prerequisites

- **Python 3.12+**
- **[uv](https://docs.astral.sh/uv/)** — Python package manager
- **Git**

## Setup

```bash
# Clone the repository
git clone <repository-url>
cd ForgeMind

# Install all dependencies (including dev tools)
uv sync --all-extras

# Install pre-commit hooks
uv run pre-commit install

# Copy environment configuration
cp .env.example .env
```

## Development Workflow

### Branch Strategy

We use **trunk-based development**:

- `main` is always deployable
- Create short-lived feature branches (`feature/add-entity-extraction`, `fix/chunking-bug`)
- Branches should live for < 2 days. Break large tasks into smaller PRs.
- Squash-merge to `main` for clean linear history

### Commit Messages

We use **[Conventional Commits](https://www.conventionalcommits.org/)**:

```
<type>(<scope>): <description>

[optional body]
```

**Types**: `feat`, `fix`, `refactor`, `docs`, `test`, `chore`, `style`, `perf`

**Scopes**: `knowledge`, `graph`, `retrieval`, `reasoning`, `api`, `shared`, `tests`, `docs`, `infra`

**Examples**:
```
feat(knowledge): add PDF text extraction with pdfplumber
fix(graph): prevent duplicate edges during construction
docs(adr): add ADR-0008 for embedding model selection
test(knowledge): add property tests for chunking
```

### Running Tests

```bash
uv run pytest -m unit           # Fast unit tests
uv run pytest -m integration    # Integration tests
uv run pytest -m architecture   # Architectural boundary tests
uv run pytest                   # All tests
```

### Running Linters

```bash
uv run ruff check .             # Lint
uv run ruff format --check .    # Format check
uv run mypy src/                # Type check
```

## Coding Standards

See [docs/standards/python-engineering-standards.md](docs/standards/python-engineering-standards.md) for the full engineering standards.

Key rules:
- **Type hints** on all public functions (`mypy --strict`)
- **Docstrings** on all public functions (Google style)
- **Max 25 lines** of logic per function
- **Max 300 lines** per module
- **Domain code must be pure** — no I/O, no framework imports in `domain/` directories

## Pull Request Checklist

Before submitting a PR, verify:

- [ ] Tests added/updated for new functionality
- [ ] Type hints on all new public functions
- [ ] Docstrings on all new public functions
- [ ] No new `# type: ignore` without justification
- [ ] Architectural boundaries preserved (no forbidden imports)
- [ ] ADR created/updated if an architectural decision was made
- [ ] All CI checks pass locally (`uv run pytest && uv run ruff check . && uv run mypy src/`)

## Architecture

ForgeMind uses **hexagonal architecture** within each bounded context:

- **`domain/`** — Pure business logic. Depends on nothing external.
- **`ports/`** — Interface definitions (`Protocol`). Depends only on domain.
- **`adapters/`** — Concrete implementations. Depends on ports and domain.

**The golden rule**: Dependencies point inward. Domain never imports from adapters.

## Questions?

Open an issue or start a discussion. We're happy to help!
