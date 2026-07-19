# ForgeMind

> **Industrial Knowledge Graph & Deterministic Decision Intelligence Platform**

ForgeMind is an **Industrial Knowledge Graph & Decision Intelligence Platform** that continuously builds an evolving organizational memory from equipment manuals, incident reports, and inspection records. Instead of relying on non-deterministic LLM text generation, it constructs a deterministic, auditable Knowledge Graph, extracts entity-relationship topologies, computes evolving evidence confidence, detects cross-document contradictions, and explains decisions through graph traversal.

---

## Technical Design & Architecture Focus

ForgeMind prioritizes **100% reproducible, auditable, sub-second decision intelligence**:
- **Deterministic Graph Reasoning**: Root cause analysis and recommendation generation use multi-hop graph traversal (BFS) over typed entity relationships, eliminating LLM hallucinations, API key requirements, and latency.
- **Evolving Evidence Confidence**: Entity and relationship confidence automatically strengthens with repeated evidence across documents and degrades when cross-document contradictions are detected.
- **Document Capability Analyzer**: Every uploaded document undergoes automated capability and industrial relevance assessment prior to graph evolution, providing graceful warnings and clear capability matrices for unsupported or partial formats.
- **Designed for Hybrid RAG Extension**: The modular architecture defines explicit ports for future vector search (`retrieval/`) and LLM summary layers while keeping core reasoning deterministic.


## Quick Start

### Prerequisites
- Python 3.12+
- `uv` (Fast package manager: [astral.sh/uv](https://docs.astral.sh/uv/))

### Installation & Setup

```bash
# Clone the repository
git clone <repository-url>
cd ForgeMind

# Sync dependencies and virtual environment
uv sync --all-extras

# Install git pre-commit hooks
uv run pre-commit install

# Setup local environment
cp .env.example .env
```

### Running the Test Suite
ForgeMind features a comprehensive test suite (including unit, integration, and architectural boundary tests):

```bash
# Run all 283 tests
uv run pytest

# Run fast unit tests only (~2s)
uv run pytest -m unit

# Run architectural boundary tests (verifies strict hexagonal layer isolation)
uv run pytest -m architecture
```

### Launching the Platform

```bash
# Start the API & UI server
uv run uvicorn forgemind.api.app:create_app --factory --reload --port 8000
```

Once running, navigate to:
- **`http://localhost:8000/`** — Interactive Product Dashboard & AI Copilot
- **`http://localhost:8000/graph`** — Premium Hierarchical Knowledge Graph Visualizer
- **`http://localhost:8000/docs`** — Interactive Swagger API Documentation

---

## 3-Step Demo Walkthrough

ForgeMind demonstrates its true power when ingesting a series of documents over time. Use the following sequence to witness knowledge evolution, contradiction detection, and decision shifts:

### Step 1: Ingest the OEM Manual
The baseline document defines standard parameters and component configurations.
```bash
curl -X POST http://localhost:8000/api/v1/documents/upload \
  -F "file=@data/demo/pump_p101_manual.pdf"
```
*Creates initial entities and relationships (e.g., Pump P-101 is an Asset containing components like Bearing and Impeller).*

### Step 2: Ingest the Incident Report
An operational failure event occurs.
```bash
curl -X POST http://localhost:8000/api/v1/documents/upload \
  -F "file=@data/demo/incident_report_IR-2024-0847.pdf"
```
*Identifies symptoms (Vibration, Overheating), logs a failure mode, and raises a temperature contradiction based on operational telemetry.*

### Step 3: Ingest the Inspection Report
Post-incident inspection details.
```bash
curl -X POST http://localhost:8000/api/v1/documents/upload \
  -F "file=@data/demo/inspection_INS-2024-0392.pdf"
```
*Resolves contradictions, shifts confidence upwards to 95%, and updates recommended maintenance actions.*

### Ask the Copilot
Ask a question through the Dashboard UI or via the API:
```bash
curl -X POST http://localhost:8000/api/v1/decide \
  -H "Content-Type: application/json" \
  -d '{"query": "Why is Pump P-101 failing?"}'
```

---

## Core Capabilities

### 1. Evolving Knowledge Timeline
Every ingestion triggers the **Knowledge Evolution Engine**, which compares new findings against the existing graph, detects contradictions, merges nodes, and generates a structured event timeline.

### 2. Decision Intelligence & RCA
The reasoning service uses graph traversal to compile evidence and estimate downtime risks, cost categories, maintenance priorities, and confidence levels without needing non-deterministic LLMs.

### 3. Integrated Dashboard UI
A visual interface serving:
- **AI Copilot** hero console with preset queries.
- **Metrics Bar** tracking entities, relationships, contradictions, and average confidence.
- **What Changed** real-time feed displaying delta updates for each uploaded file.
- **Timeline Replay** to visually play back how organizational knowledge evolved step-by-step.

---

## Document Robustness & Support Matrix

ForgeMind includes an automated **Document Capability Analyzer** that evaluates uploaded files prior to ingestion. The system explicitly reports feature availability, support level, and graceful warnings rather than producing misleading outputs on unsupported document types:

| Document Category | Detect | Parse Text | Extract Entities | Graph Evolution | Deterministic RCA | Support Level |
| :--- | :---: | :---: | :---: | :---: | :---: | :--- |
| **OEM Manuals** | ✅ | ✅ | ✅ | ✅ | ✅ | **Full Support** |
| **Incident Reports** | ✅ | ✅ | ✅ | ✅ | ✅ | **Full Support** |
| **Inspection Reports** | ✅ | ✅ | ✅ | ✅ | ✅ | **Full Support** |
| **Maintenance Work Orders** | ✅ | ✅ | ⚠️ Partial | ⚠️ Partial | ⚠️ Partial | **Partial Support** |
| **Safety SOPs** | ✅ | ✅ | ⚠️ Partial | ⚠️ Partial | ❌ Excluded | **Partial Support** |
| **P&ID Schematics** | ✅ | ❌ Excluded | ❌ Excluded | ❌ Excluded | ❌ Excluded | **Unsupported (Graceful Warning)** |
| **Spreadsheets / Data Logs** | ✅ | ⚠️ Partial | ⚠️ Partial | ❌ Excluded | ❌ Excluded | **Unsupported (Graceful Warning)** |
| **General / Non-Industrial** | ✅ | ✅ | ❌ Excluded | ❌ Excluded | ❌ Excluded | **Unsupported (Graceful Warning)** |

---

## Architecture & Code Quality

ForgeMind is designed as a **Modular Monolith** using **Hexagonal Architecture** (Ports & Adapters) for separation of concerns and database independence:

```
┌──────────────────────────────────────────────────────────┐
│                        API Layer                         │
│       FastAPI + Root Dashboard + Visualizer + Swagger    │
├────────────┬────────────┬─────────────┬──────────────────┤
│ Knowledge  │   Graph    │  Retrieval  │    Reasoning     │
│  Context   │  Context   │   Context   │     Context      │
│            │            │             │                  │
│  domain/   │  domain/   │   domain/   │    domain/       │
│  ports/    │  ports/    │   ports/    │    ports/        │
│  adapters/ │  adapters/ │   adapters/ │    adapters/     │
├────────────┴────────────┴─────────────┴──────────────────┤
│                      Shared Module                       │
│             (types, errors, logging, config)             │
└──────────────────────────────────────────────────────────┘
```

- **Domain**: Pure business logic with zero framework or database dependencies.
- **Ports**: Inbound/Outbound protocol interfaces defining contract boundaries.
- **Adapters**: Concrete implementations (pdfplumber, NetworkX, FastAPI routes).

---

## Verification & Quality Standards

To maintain release-grade reliability, the repository enforces strict code quality checks:

| Tool | Purpose | Command |
| :--- | :--- | :--- |
| **Ruff** | Linting & code styling checks | `uv run ruff check .` |
| **Ruff Format** | Formatting compliance | `uv run ruff format --check .` |
| **Mypy** | Strict type analysis (no `Any` types) | `uv run mypy src/` |
| **Pytest** | Run the complete test suite | `uv run pytest` |
| **Bandit** | Security auditing | `uv run bandit -r src/` |

---

## Project Structure

```
src/forgemind/
├── shared/                 # Configuration, structured logging, errors, types
├── knowledge/              # Universal PDF parser, entity/relationship extraction
├── graph/                  # NetworkX Graph repository implementation
├── reasoning/              # Graph traversal, RCA, and decision engine
└── api/                    # FastAPI web app, visualizer, and dashboard routes
```

---

## License
MIT — see [LICENSE](LICENSE).
