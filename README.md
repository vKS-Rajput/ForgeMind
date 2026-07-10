# ForgeMind

> **Industrial knowledge management through knowledge graphs, hybrid retrieval, and explainable AI reasoning.**

ForgeMind ingests industrial maintenance documents (manuals, incident reports, work orders), extracts entities and relationships into a knowledge graph, and answers diagnostic questions with graph-backed, explainable reasoning.

## What Problem Does ForgeMind Solve?

Industrial organizations lose critical maintenance knowledge when experienced engineers leave. Equipment manuals sit in filing cabinets. Incident reports are filed and forgotten. The same failures repeat because the organization has no memory.

ForgeMind captures this knowledge in a graph, connects it across documents and time, and makes it queryable through natural language — with every answer traceable back to its source.

---

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

# Run all 167 tests
uv run pytest                   # All tests
uv run pytest -m unit           # Fast unit tests (~2s)
uv run pytest -m architecture   # Architectural boundary tests
uv run pytest -m integration    # Integration tests (real I/O)

# Start the API server
uv run uvicorn forgemind.api.app:create_app --factory --reload --port 8000

# Open the interactive docs
# http://localhost:8000/docs
```

---

## Live API — What You Can Do Right Now

Once the server is running at `http://localhost:8000`, open **http://localhost:8000/docs** for the interactive Swagger UI.

### Upload & Analyze a Document

```bash
# Upload a PDF — returns ingestion results + analysis
curl -X POST http://localhost:8000/api/v1/documents/upload \
  -F "file=@your_manual.pdf"

# Or ingest raw text
curl -X POST http://localhost:8000/api/v1/documents/text \
  -H "Content-Type: application/json" \
  -d '{"text": "Pump P-101 operates at 3000 RPM...", "title": "Quick Note"}'
```

**Response includes automatic analysis:**

```json
{
  "document_id": "59db6bb2-...",
  "title": "pump_p101_manual",
  "page_count": 3,
  "chunk_count": 12,
  "analysis": {
    "equipment": ["Pump P-101"],
    "parts": ["John Crane Type 2100", "SKF 6205-2RS", "Shell Gadus S2"],
    "materials": ["AISI 4140", "Grade 25", "Type 2100"],
    "instruments": ["FS-101", "PSV-101"],
    "parameters": ["3000 RPM", "75 kW", "80 degrees Celsius", "150 cubic meters per hour"],
    "symptoms": ["Excessive Vibration", "High Bearing Temperature", "Seal Leakage"],
    "actions": ["Replace mechanical seal assembly.", "Check vibration levels..."],
    "key_sentences": ["...most information-dense sentences..."],
    "summary_stats": {
      "equipment_found": 1, "symptoms_found": 10, "parameters_found": 21
    }
  }
}
```

### All API Endpoints

| Method | Endpoint | Description |
| :--- | :--- | :--- |
| `POST` | `/api/v1/documents/upload` | Upload & ingest a PDF with automatic analysis |
| `POST` | `/api/v1/documents/text` | Ingest raw text with automatic analysis |
| `GET` | `/api/v1/documents` | List all ingested documents |
| `GET` | `/api/v1/documents/stats` | Total document and chunk counts |
| `GET` | `/api/v1/documents/{id}` | Get a single document by ID |
| `GET` | `/api/v1/documents/{id}/chunks` | Get all chunks with page numbers |
| `GET` | `/api/v1/documents/{id}/analyze` | Re-analyze a document for insights |

### Generate a Test PDF

```bash
uv run python data/demo/generate_test_pdf.py
# Creates: data/demo/pump_p101_manual.pdf (3 pages, realistic content)
```

---

## What Gets Extracted

ForgeMind's pattern-based analyzer extracts structured insights from any industrial/maintenance document:

| Category | What It Finds | Examples |
| :--- | :--- | :--- |
| **Equipment** | Named equipment with tag numbers | Pump P-101, Motor M-205, Valve V-300 |
| **Parts** | Manufacturer + model numbers | SKF 6205-2RS, John Crane Type 2100 |
| **Materials** | Standards and grades | AISI 4140, Grade 25, API 610 |
| **Instruments** | Safety instrument tags | PSV-101, FS-101, PT-205 |
| **Parameters** | Numeric values with units | 3000 RPM, 80 degrees Celsius, 4.5 mm/s |
| **Symptoms** | Failure symptom descriptions | Excessive vibration, bearing failure, seal leakage |
| **Actions** | Corrective maintenance actions | Replace bearings, check alignment, shut down |
| **Key Sentences** | Most information-dense sentences | Scored by entity density |

---

## Architecture

ForgeMind is a **modular monolith** using **hexagonal architecture** (ports & adapters), organized by **bounded contexts**:

```
┌─────────────────────────────────────────────────────┐
│                    API Layer                         │
│     FastAPI + Composition Root + Swagger Docs        │
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
- **Domain**: Pure business logic. No I/O, no framework imports. All entities are frozen and immutable.
- **Ports**: `Protocol` interfaces defining how the domain talks to the outside world.
- **Adapters**: Concrete implementations (pdfplumber, in-memory repos, FastAPI routes).

### Ingestion Pipeline

```
PDF Upload ──→ PdfDocumentParser ──→ ParsedDocument (validated)
                                          │
                                    SHA-256 Hash
                                          │
                                   Deduplication Check
                                          │
                                   Sentence-boundary Chunking
                                          │
                                   Page-number Assignment
                                          │
                              ┌────────────┴────────────┐
                              │                         │
                     DocumentRepository          ChunkRepository
                       (save Document)           (save Chunks)
                              │                         │
                              └────────────┬────────────┘
                                           │
                                  DocumentIngested Event
                                           │
                                  Pattern-based Analysis
                                           │
                                  IngestionResponse + Insights
```

---

## Project Structure

```
src/forgemind/
├── shared/                 # Cross-cutting concerns
│   ├── types.py            # NewType aliases (DocumentId, ChunkId, etc.)
│   ├── errors.py           # Exception hierarchy (frozen dataclasses)
│   ├── logging.py          # Structured logging (structlog)
│   └── config.py           # Pydantic settings
│
├── knowledge/              # Document ingestion & entity extraction
│   ├── domain/
│   │   ├── entities.py     # Document, Chunk, Entity, Relationship
│   │   ├── value_objects.py # EntityType, RelationType, Provenance
│   │   ├── services.py     # chunk_text, merge_entities, normalize
│   │   ├── events.py       # DocumentIngested domain event
│   │   └── parsed_document.py  # ParsedDocument value object
│   ├── ports/
│   │   ├── document_parser.py  # DocumentParser protocol
│   │   ├── inbound.py          # Inbound port protocols
│   │   └── outbound.py         # Repository protocols
│   └── adapters/
│       ├── pdf_parser.py               # PdfDocumentParser (pdfplumber)
│       ├── memory_document_repository.py # In-memory with hash index
│       ├── memory_chunk_repository.py    # In-memory with doc index
│       ├── ingestion_service.py          # Full pipeline orchestrator
│       └── analysis_service.py           # Pattern-based entity extraction
│
├── graph/                  # Knowledge graph (future phases)
├── retrieval/              # Hybrid retrieval (future phases)
├── reasoning/              # LLM reasoning (future phases)
│
└── api/
    ├── app.py              # FastAPI app factory + lifespan
    ├── state.py            # Composition root (DI wiring)
    └── routes/
        └── documents.py    # Document CRUD + analysis endpoints

tests/
├── unit/                   # 123 unit tests (no I/O)
├── integration/            # 4 integration tests (real PDF parsing)
├── architecture/           # 40 boundary tests (import rules)
└── conftest.py             # Shared fixtures (PDF generator)

data/demo/
├── generate_test_pdf.py    # Generates a 3-page test PDF
└── pump_p101_manual.pdf    # Generated test document
```

---

## Quality Gates

Every change must pass all quality gates before merging:

| Tool | Command | What It Checks |
| :--- | :--- | :--- |
| **Ruff** | `uv run ruff check .` | 400+ lint rules (replaces flake8+isort+pycodestyle) |
| **Ruff Format** | `uv run ruff format --check .` | Consistent code formatting |
| **Mypy** | `uv run mypy src/` | Strict type checking (no `Any`, no untyped calls) |
| **Pytest** | `uv run pytest` | 167 tests across unit/integration/architecture |
| **Bandit** | `uv run bandit -r src/` | Security vulnerability scanning |

### Test Breakdown

| Category | Count | Coverage |
| :--- | :--- | :--- |
| Unit tests | 123 | Domain logic, services, repositories, parsers |
| Integration tests | 4 | End-to-end PDF → chunks pipeline |
| Architecture tests | 40 | Import boundaries, hexagonal rules |
| **Total** | **167** | All passing |

---

## Key Technologies

| Component | Technology | Why |
| :--- | :--- | :--- |
| Language | Python 3.12+ | AI/ML ecosystem, fast iteration |
| Package Manager | uv | 10-100x faster than pip, lockfile support |
| Web Framework | FastAPI | Async, type-safe, auto-generated OpenAPI docs |
| PDF Parsing | pdfplumber | Reliable text extraction with page boundaries |
| Graph Store | NetworkX (V1) → Neo4j (V2) | Zero-infrastructure MVP |
| Vector Store | ChromaDB | Embedded, persistent, zero-infrastructure |
| Linting | ruff | Replaces black + isort + flake8 in one tool |
| Type Checking | mypy (strict) | Catch bugs before runtime |
| Logging | structlog | Structured JSON logging, production-ready |

---

## Architecture Decision Records

See [docs/adr/](docs/adr/) for all architectural decisions:

- [ADR-0001: Modular Monolith](docs/adr/0001-modular-monolith.md)
- [ADR-0002: Hexagonal Architecture](docs/adr/0002-hexagonal-architecture.md)
- [ADR-0003: Python as Primary Language](docs/adr/0003-python-primary-language.md)
- [ADR-0004: Graph Storage Strategy](docs/adr/0004-graph-storage-strategy.md)
- [ADR-0005: Hybrid Retrieval](docs/adr/0005-hybrid-retrieval.md)
- [ADR-0006: Vertical Slice Development](docs/adr/0006-vertical-slice-development.md)
- [ADR-0007: Knowledge-First Domain Model](docs/adr/0007-knowledge-first-domain-model.md)

---

## Roadmap

| Phase | Status | What It Delivers |
| :--- | :--- | :--- |
| Phase 0 | ✅ Complete | Repository structure, CI/CD, engineering standards |
| Phase 1 | ✅ Complete | Domain model (entities, value objects, services, events) |
| Phase 2 | ✅ Complete | Document ingestion pipeline (PDF → chunks → storage) |
| Phase 2.5 | ✅ Complete | API layer + pattern-based document analysis |
| Phase 3 | 🔜 Next | Knowledge graph construction (NetworkX) |
| Phase 4 | Planned | Vector embeddings + hybrid retrieval |
| Phase 5 | Planned | LLM-powered entity extraction |
| Phase 6 | Planned | Natural language Q&A with explainable reasoning |

---

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for setup instructions, coding standards, and PR guidelines.

## License

MIT — see [LICENSE](LICENSE).
