"""ForgeMind API application factory.

Creates and configures the FastAPI application with all routes,
middleware, and dependency injection wired up. This is the
composition root — where all adapters are instantiated and
connected to their ports.

Usage:
    # Run directly with uvicorn:
    uvicorn forgemind.api.app:create_app --factory --reload

    # Or import and use:
    app = create_app()
"""

from __future__ import annotations

from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from forgemind.api.routes.dashboard import router as dashboard_router
from forgemind.api.routes.documents import router as documents_router
from forgemind.api.routes.graph import router as graph_router
from forgemind.api.routes.reasoning import router as reasoning_router
from forgemind.api.routes.visualization import router as visualization_router
from forgemind.api.state import create_app_state
from forgemind.shared.logging import get_logger

logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Application lifespan manager — runs on startup and shutdown.

    On startup:
      - Creates all adapters (parser, repositories, ingestion service,
        graph repository, knowledge evolution engine).
      - Stores them in app.state for dependency injection via routes.

    On shutdown:
      - Logs a clean shutdown message.
    """
    # ── Startup ──────────────────────────────────────────────────
    logger.info("application_starting", version="0.4.0")

    # Create the application state with all wired-up adapters.
    # This is the composition root: adapters are created here and
    # injected into the routes via FastAPI's dependency injection.
    app_state = create_app_state()
    app.state.forgemind = app_state

    logger.info(
        "application_started",
        supported_formats=list(app_state.parser.supported_extensions()),
        knowledge_graph="ready",
    )

    yield  # Application is running

    # ── Shutdown ─────────────────────────────────────────────────
    logger.info("application_shutdown")


def create_app() -> FastAPI:
    """Create and configure the FastAPI application.

    Returns:
        A fully configured FastAPI app ready to serve requests.
    """
    app = FastAPI(
        title="ForgeMind",
        description=(
            "Industrial Organizational Memory System — "
            "knowledge graphs, evolving confidence, "
            "and explainable reasoning backed by evidence."
        ),
        version="0.4.0",
        lifespan=lifespan,
    )

    # ── Register routes ──────────────────────────────────────────
    app.include_router(dashboard_router)  # Serves at / (the product experience)
    app.include_router(documents_router, prefix="/api/v1")
    app.include_router(graph_router, prefix="/api/v1")
    app.include_router(reasoning_router, prefix="/api/v1")
    app.include_router(visualization_router)  # Serves at /graph (no prefix)

    return app
