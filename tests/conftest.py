"""Pytest configuration and common fixtures."""

from unittest.mock import Mock, patch

import pytest


@pytest.fixture(autouse=True)
def mock_imports():
    """Mock external dependencies to avoid import errors during testing."""
    with patch.dict(
        "sys.modules",
        {
            "fastmcp": Mock(),
            "structlog": Mock(),
            "uvicorn": Mock(),
            "httpx": Mock(),
            "requests": Mock(),
        },
    ):
        yield
