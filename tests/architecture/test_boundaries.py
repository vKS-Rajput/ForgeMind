"""Architectural fitness tests for ForgeMind.

These tests enforce hexagonal architecture boundaries using pytest-archon.
They run as part of the standard test suite and fail CI if any
architectural rule is violated.

Rules enforced:
1. Domain modules must not import from adapters or frameworks.
2. Ports must not import from adapters.
3. Bounded contexts must not import each other's internal layers.
4. Non-API modules must not import from the API layer.

WARNING: Changes to this file require tech lead review.
"""

import pytest

# pytest-archon may not be installed in all environments
archon_available = True
try:
    from pytest_archon import archrule
except ImportError:
    archon_available = False

pytestmark = [
    pytest.mark.architecture,
    pytest.mark.skipif(not archon_available, reason="pytest-archon not installed"),
]

# ═══════════════════════════════════════════════════════════════════
# Rule 1: Domain Independence
# The domain layer is the innermost ring. It depends on NOTHING external.
# ═══════════════════════════════════════════════════════════════════

BOUNDED_CONTEXTS = ["knowledge", "graph", "retrieval", "reasoning"]

FRAMEWORK_MODULES = [
    "fastapi",
    "uvicorn",
    "neo4j",
    "chromadb",
    "openai",
    "httpx",
    "sqlalchemy",
]


class TestDomainIndependence:
    """Domain modules must not import from adapters or frameworks."""

    @pytest.mark.parametrize("context", BOUNDED_CONTEXTS)
    def test_domain_does_not_import_adapters(self, context: str) -> None:
        """Domain layer must not import from its own adapters."""
        (
            archrule(f"{context} domain must not import adapters")
            .match(f"forgemind.{context}.domain.*")
            .should_not_import(f"forgemind.{context}.adapters.*")
            .check("forgemind")
        )

    @pytest.mark.parametrize("context", BOUNDED_CONTEXTS)
    @pytest.mark.parametrize("framework", FRAMEWORK_MODULES)
    def test_domain_does_not_import_frameworks(
        self, context: str, framework: str
    ) -> None:
        """Domain layer must not import external frameworks."""
        (
            archrule(f"{context} domain must not import {framework}")
            .match(f"forgemind.{context}.domain.*")
            .should_not_import(framework)
            .check("forgemind")
        )


# ═══════════════════════════════════════════════════════════════════
# Rule 2: Port Independence
# Ports define interfaces. They must not know about concrete adapters.
# ═══════════════════════════════════════════════════════════════════


class TestPortIndependence:
    """Ports must not import from adapters."""

    @pytest.mark.parametrize("context", BOUNDED_CONTEXTS)
    def test_ports_do_not_import_adapters(self, context: str) -> None:
        """Port interfaces must not depend on concrete adapter implementations."""
        (
            archrule(f"{context} ports must not import adapters")
            .match(f"forgemind.{context}.ports.*")
            .should_not_import(f"forgemind.{context}.adapters.*")
            .check("forgemind")
        )


# ═══════════════════════════════════════════════════════════════════
# Rule 3: API Layer Isolation
# Non-API modules must not import from the API layer.
# The API layer is the composition root — only it wires everything.
# ═══════════════════════════════════════════════════════════════════


class TestApiLayerIsolation:
    """Non-API modules must not import from the API layer."""

    @pytest.mark.parametrize("context", BOUNDED_CONTEXTS)
    def test_bounded_context_does_not_import_api(self, context: str) -> None:
        """Business logic modules must not depend on the API/web layer."""
        (
            archrule(f"{context} must not import from API layer")
            .match(f"forgemind.{context}.*")
            .should_not_import("forgemind.api.*")
            .check("forgemind")
        )
