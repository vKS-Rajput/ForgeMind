"""Smoke tests to verify the shared module is correctly structured."""

import pytest

pytestmark = pytest.mark.unit


class TestErrorHierarchy:
    """Verify the error hierarchy is correctly structured."""

    def test_all_errors_inherit_from_forgemind_error(self):
        from forgemind.shared.errors import (
            ChunkingError,
            ConfigurationError,
            DocumentParseError,
            EmbeddingError,
            EntityExtractionError,
            EntityNotFoundError,
            ForgeMindError,
            GraphConstructionError,
            GraphQueryError,
            IngestionError,
            LLMProviderError,
            PromptConstructionError,
            ReasoningError,
            RelationshipExtractionError,
            ResponseParseError,
            RetrievalError,
            UnsupportedFormatError,
            VectorSearchError,
        )

        errors = [
            IngestionError,
            DocumentParseError,
            ChunkingError,
            UnsupportedFormatError,
            EntityExtractionError,
            RelationshipExtractionError,
            GraphConstructionError,
            GraphQueryError,
            EntityNotFoundError,
            VectorSearchError,
            EmbeddingError,
            LLMProviderError,
            PromptConstructionError,
            ResponseParseError,
            RetrievalError,
            ReasoningError,
            ConfigurationError,
        ]

        for error_cls in errors:
            assert issubclass(error_cls, ForgeMindError), (
                f"{error_cls.__name__} must inherit from ForgeMindError"
            )

    def test_forgemind_error_has_structured_fields(self):
        from forgemind.shared.errors import ForgeMindError

        error = ForgeMindError(
            message="Test error",
            code="TEST_CODE",
            context={"key": "value"},
        )
        assert error.message == "Test error"
        assert error.code == "TEST_CODE"
        assert error.context == {"key": "value"}
        assert "[TEST_CODE] Test error" in str(error)

    def test_forgemind_error_is_frozen(self):
        from dataclasses import FrozenInstanceError

        from forgemind.shared.errors import ForgeMindError

        error = ForgeMindError(message="Immutable")
        with pytest.raises(FrozenInstanceError):
            error.message = "Changed"  # type: ignore[misc]


class TestTypeAliases:
    """Verify type aliases are importable and distinct."""

    def test_all_id_types_are_importable(self):
        from forgemind.shared.types import (
            ChunkId,
            Confidence,
            DocumentId,
            EmbeddingVector,
            EntityId,
            IncidentId,
            RelationshipId,
            WorkOrderId,
        )

        # NewType creates distinct types
        doc_id = DocumentId("doc-001")
        chunk_id = ChunkId("chunk-001")
        entity_id = EntityId("entity-001")
        rel_id = RelationshipId("rel-001")
        incident_id = IncidentId("inc-001")
        wo_id = WorkOrderId("wo-001")
        confidence = Confidence(0.95)
        embedding = EmbeddingVector([0.1, 0.2, 0.3])

        assert doc_id == "doc-001"
        assert chunk_id == "chunk-001"
        assert entity_id == "entity-001"
        assert rel_id == "rel-001"
        assert incident_id == "inc-001"
        assert wo_id == "wo-001"
        assert confidence == 0.95
        assert len(embedding) == 3


class TestConfiguration:
    """Verify configuration loads correctly."""

    def test_default_settings_load(self):
        from forgemind.shared.config import AppSettings

        settings = AppSettings(
            _env_file=None,  # type: ignore[call-arg]
        )
        assert settings.env == "development"
        assert settings.debug is False
        assert settings.log_level == "INFO"
        assert settings.port == 8000

    def test_nested_settings(self):
        from forgemind.shared.config import AppSettings

        settings = AppSettings(
            _env_file=None,  # type: ignore[call-arg]
        )
        assert settings.llm.provider == "openai"
        assert settings.graph.backend == "networkx"
        assert settings.vector.backend == "chromadb"
