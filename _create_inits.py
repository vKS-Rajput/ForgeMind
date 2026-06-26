import os

files = {
    # Retrieval
    "src/forgemind/retrieval/__init__.py": '"""Retrieval bounded context \u2014 hybrid vector + graph search and fusion."""\n',
    "src/forgemind/retrieval/domain/__init__.py": '"""Retrieval domain \u2014 pure retrieval entities and fusion logic."""\n',
    "src/forgemind/retrieval/domain/entities.py": '"""Retrieval domain entities \u2014 placeholder for Phase 6."""\n',
    "src/forgemind/retrieval/domain/value_objects.py": '"""Retrieval domain value objects \u2014 placeholder for Phase 6."""\n',
    "src/forgemind/retrieval/domain/services.py": '"""Retrieval domain services \u2014 placeholder for Phase 6."""\n',
    "src/forgemind/retrieval/ports/__init__.py": '"""Retrieval ports \u2014 vector store and embedding interfaces."""\n',
    "src/forgemind/retrieval/ports/inbound.py": '"""Retrieval inbound ports \u2014 placeholder for Phase 6."""\n',
    "src/forgemind/retrieval/ports/outbound.py": '"""Retrieval outbound ports \u2014 placeholder for Phase 6."""\n',
    "src/forgemind/retrieval/adapters/__init__.py": '"""Retrieval adapters \u2014 ChromaDB, sentence-transformers."""\n',
    # Reasoning
    "src/forgemind/reasoning/__init__.py": '"""Reasoning bounded context \u2014 LLM-powered reasoning with graph context."""\n',
    "src/forgemind/reasoning/domain/__init__.py": '"""Reasoning domain \u2014 pure prompt construction and response parsing."""\n',
    "src/forgemind/reasoning/domain/entities.py": '"""Reasoning domain entities \u2014 placeholder for Phase 7."""\n',
    "src/forgemind/reasoning/domain/value_objects.py": '"""Reasoning domain value objects \u2014 placeholder for Phase 7."""\n',
    "src/forgemind/reasoning/domain/services.py": '"""Reasoning domain services \u2014 placeholder for Phase 7."""\n',
    "src/forgemind/reasoning/ports/__init__.py": '"""Reasoning ports \u2014 LLM provider interfaces."""\n',
    "src/forgemind/reasoning/ports/inbound.py": '"""Reasoning inbound ports \u2014 placeholder for Phase 7."""\n',
    "src/forgemind/reasoning/ports/outbound.py": '"""Reasoning outbound ports \u2014 placeholder for Phase 7."""\n',
    "src/forgemind/reasoning/adapters/__init__.py": '"""Reasoning adapters \u2014 OpenAI, Ollama."""\n',
    # API
    "src/forgemind/api/__init__.py": '"""API layer \u2014 FastAPI routes, schemas, dependency injection (composition root)."""\n',
    "src/forgemind/api/routes/__init__.py": '"""API routes \u2014 endpoint definitions."""\n',
    "src/forgemind/api/schemas/__init__.py": '"""API schemas \u2014 Pydantic request/response models."""\n',
    # Tests
    "tests/__init__.py": "",
    "tests/unit/__init__.py": "",
    "tests/unit/knowledge/__init__.py": "",
    "tests/unit/graph/__init__.py": "",
    "tests/unit/retrieval/__init__.py": "",
    "tests/unit/reasoning/__init__.py": "",
    "tests/integration/__init__.py": "",
    "tests/architecture/__init__.py": "",
    "tests/golden/__init__.py": "",
}

for path, content in files.items():
    full_path = os.path.join(os.getcwd(), path.replace("/", os.sep))
    os.makedirs(os.path.dirname(full_path), exist_ok=True)
    with open(full_path, "w", encoding="utf-8") as f:
        f.write(content)

print(f"Created {len(files)} files.")
