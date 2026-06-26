"""Shared test fixtures for ForgeMind test suite.

This module provides reusable fixtures used across unit, integration,
and golden tests. Fixtures follow the principle of least surprise:
they provide minimal, predictable test data.
"""

import pytest

from forgemind.shared.config import AppSettings


@pytest.fixture
def test_settings() -> AppSettings:
    """Provide test-safe application settings.

    Overrides defaults to disable LLM calls and use in-memory stores.
    """
    return AppSettings(
        env="testing",
        debug=True,
        log_level="DEBUG",
        log_format="console",
    )
