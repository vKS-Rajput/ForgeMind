# ForgeMind

> **AI-powered Industrial Knowledge Intelligence Platform**

ForgeMind is an **AI-powered Industrial Knowledge Intelligence Platform** that continuously builds an evolving organizational memory from manuals, incident reports, and inspection records. Rather than simply retrieving documents, it parses ingestion data, extracts entity-relationship topologies, detects contradictions, explains decisions, and updates maintenance recommendations as new operational knowledge arrives.

---

## The Industrial Challenge

Industrial organizations lose critical maintenance knowledge when experienced engineers retire or change roles. Equipment manuals sit in siloed PDFs, incident reports are filed and forgotten, and inspection logs are disconnected. The same failures repeat because the organization lacks a unified, evolving memory.

ForgeMind resolves this by constructing a deterministic, auditable **Knowledge Graph** directly from source documents, tracing confidence evolution, detecting conflicting evidence over time, and presenting recommendations through an integrated **Decision Intelligence Dashboard**.

---

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
