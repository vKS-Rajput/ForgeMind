# ForgeMind Development Guide

Welcome! This guide outlines how to set up the development environment, execute tests, run the linter suite, and extend the ontology or reasoning engine of ForgeMind.

---

## 1. Setup & Tools

ForgeMind uses Python 3.12+ and **`uv`** as its single source of package management truth.

### Virtual Environment Setup
```bash
# Sync virtual environment and all dependencies (including dev tools)
uv sync --all-extras
```

### Git Pre-Commit Hooks
Ruff checks and formatting are run automatically before commits:
```bash
uv run pre-commit install
```

---

## 2. Code Quality & Formatting

The codebase enforces strict checks in continuous integration. Run these locally before making PRs:

### A. Formatting & Linting (Ruff)
Ruff replaces flake8, black, isort, and other checkers in a single extremely fast tool:
```bash
# Run the linter
uv run ruff check .

# Auto-fix linting violations where possible
uv run ruff check --fix .

# Format code files
uv run ruff format .
```

### B. Type Analysis (Mypy)
Mypy is configured in strict type-checking mode. `Any` variables or undocumented signatures will trigger errors:
```bash
uv run mypy src/
```

### C. Security Analysis (Bandit)
Bandit scans the source directory for common security issues (e.g. usage of temporary directories, parsing risks):
```bash
uv run bandit -r src/
```

---

## 3. Testing Suite

The project includes unit tests, integration tests, and architectural boundary tests:

```bash
# Run all tests
uv run pytest

# Run with coverage report
uv run pytest --cov=forgemind --cov-report=term-missing
```

### Writing New Tests
All test files must reside in the `tests/` directory:
- `tests/unit/`: Test pure functions, domain objects, and logic without disk/network overhead.
- `tests/integration/`: Verify files integration (e.g. PDF parsing pipeline output).
- `tests/architecture/`: Enforce hexagonal boundary conditions. Uses `pytest-archon` to check that domain files do not import adapters or ports.

---

## 4. Extending ForgeMind

### Adding a New Document Type
To support a new type of document (e.g., `REGULATORY_AUDIT`):
1. In `src/forgemind/knowledge/domain/value_objects.py`, add the enum case to `DocumentType`.
2. In `src/forgemind/knowledge/adapters/pdf_parser.py`, add classification rules inside `_classify_document()` to recognize the document based on header patterns or keywords.

### Extending the Ontology (Adding Entity or Relation Types)
1. Add new types to `EntityType` or `RelationType` in `src/forgemind/knowledge/domain/value_objects.py`.
2. Update pattern matchers in `src/forgemind/knowledge/adapters/relationship_extractor.py` to extract these relationships from text.

### Modifying the Reasoning Engine
All traversal decision pathways are located in `src/forgemind/reasoning/reasoning_service.py`.
- To adjust confidence weights, modify the `_compute_confidence()` private method.
- To modify the diagnostic response fields, alter `DecisionIntelligenceResult` and the orchestrating `decide()` method.
