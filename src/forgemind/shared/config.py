"""Application configuration for ForgeMind.

All configuration is loaded from environment variables and/or .env files.
Uses pydantic-settings for type-safe validation.

Environment files are loaded in this priority (later overrides earlier):
1. .env            (base defaults for local development)
2. .env.{ENV}      (environment-specific overrides: .env.test, .env.prod)
3. Environment variables (highest priority, always wins)

Usage:
    from forgemind.shared.config import get_settings

    settings = get_settings()
    print(settings.llm.model_name)

Bounded Context: Shared
Layer: Infrastructure
Dependencies: pydantic-settings
"""

import os
from functools import lru_cache

from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class LLMSettings(BaseSettings):
    """LLM provider configuration.

    All fields are prefixed with LLM_ in environment variables.
    Example: LLM_PROVIDER=openai, LLM_API_KEY=sk-...
    """

    model_config = SettingsConfigDict(env_prefix="LLM_")

    provider: str = Field(default="openai", description="LLM provider: 'openai' or 'ollama'")
    model_name: str = Field(default="gpt-4o-mini", description="Model identifier")
    api_key: SecretStr = Field(default=SecretStr(""), description="API key (required for OpenAI)")
    base_url: str = Field(
        default="https://api.openai.com/v1", description="Base URL for API calls"
    )
    max_tokens: int = Field(default=2000, description="Maximum tokens in LLM response")
    temperature: float = Field(default=0.1, description="Sampling temperature (0.0-2.0)")


class GraphSettings(BaseSettings):
    """Knowledge graph storage configuration.

    All fields are prefixed with GRAPH_ in environment variables.
    """

    model_config = SettingsConfigDict(env_prefix="GRAPH_")

    backend: str = Field(default="networkx", description="Graph backend: 'networkx' or 'neo4j'")
    persistence_path: str = Field(
        default="data/graph.json", description="File path for NetworkX graph persistence"
    )
    neo4j_uri: str = Field(default="bolt://localhost:7687", description="Neo4j connection URI")
    neo4j_user: str = Field(default="neo4j", description="Neo4j username")
    neo4j_password: SecretStr = Field(default=SecretStr(""), description="Neo4j password")


class VectorSettings(BaseSettings):
    """Vector store configuration.

    All fields are prefixed with VECTOR_ in environment variables.
    """

    model_config = SettingsConfigDict(env_prefix="VECTOR_")

    backend: str = Field(default="chromadb", description="Vector store backend")
    persist_directory: str = Field(
        default="data/chromadb", description="ChromaDB persistence directory"
    )
    embedding_model: str = Field(
        default="all-MiniLM-L6-v2", description="Sentence-transformer model name"
    )
    collection_name: str = Field(
        default="forgemind_chunks", description="ChromaDB collection name"
    )


class AppSettings(BaseSettings):
    """Top-level application settings.

    All fields are prefixed with FORGEMIND_ in environment variables.
    Nested settings (llm, graph, vector) use their own prefixes.
    """

    model_config = SettingsConfigDict(
        env_file=(".env", f".env.{os.getenv('FORGEMIND_ENV', 'development')}"),
        env_prefix="FORGEMIND_",
        extra="ignore",
    )

    # ── Application ──────────────────────────────────────────
    env: str = Field(
        default="development",
        description="Environment: 'development', 'testing', or 'production'",
    )
    debug: bool = Field(default=False, description="Enable debug mode")
    log_level: str = Field(default="INFO", description="Log level: DEBUG, INFO, WARNING, ERROR")
    log_format: str = Field(default="json", description="Log format: 'json' or 'console'")

    # ── Server ───────────────────────────────────────────────
    host: str = Field(default="127.0.0.1", description="Server bind host")
    port: int = Field(default=8000, description="Server bind port")

    # ── Data ─────────────────────────────────────────────────
    data_dir: str = Field(default="data", description="Base directory for persistent data")

    # ── Nested Settings ──────────────────────────────────────
    llm: LLMSettings = Field(default_factory=LLMSettings)
    graph: GraphSettings = Field(default_factory=GraphSettings)
    vector: VectorSettings = Field(default_factory=VectorSettings)


@lru_cache(maxsize=1)
def get_settings() -> AppSettings:
    """Get the application settings singleton.

    Settings are loaded once and cached. Uses lru_cache to ensure
    only one instance exists per process.

    Returns:
        The validated application settings.
    """
    return AppSettings()
