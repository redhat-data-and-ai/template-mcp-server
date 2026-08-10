"""Tests for graceful shutdown helpers."""

import asyncio
import signal
from unittest.mock import Mock, patch

import pytest

from template_mcp_server.src.settings import Settings
from template_mcp_server.utils.graceful_shutdown import (
    GracefulShutdownManager,
    register_graceful_shutdown,
)


@pytest.mark.asyncio
async def test_shutdown_manager_runs_registered_async_cleanup_callbacks():
    calls = []

    async def cleanup_storage():
        calls.append("storage")

    manager = GracefulShutdownManager(timeout_seconds=1)
    manager.add_cleanup_callback(cleanup_storage)

    await manager.shutdown(signal.SIGTERM)

    assert calls == ["storage"]
    assert manager.shutdown_requested is True


@pytest.mark.asyncio
async def test_shutdown_manager_logs_closed_resource_errors_at_debug():
    logger = Mock()

    async def closed_resource_cleanup():
        raise RuntimeError("ClosedResourceError: pool already closed")

    manager = GracefulShutdownManager(timeout_seconds=1, logger=logger)
    manager.add_cleanup_callback(closed_resource_cleanup)

    await manager.shutdown(signal.SIGINT)

    logger.debug.assert_called()


@pytest.mark.asyncio
async def test_shutdown_manager_enforces_timeout():
    logger = Mock()

    async def slow_cleanup():
        await asyncio.sleep(0.2)

    manager = GracefulShutdownManager(timeout_seconds=0.01, logger=logger)
    manager.add_cleanup_callback(slow_cleanup)

    await manager.shutdown(signal.SIGTERM)

    logger.warning.assert_called()


def test_register_graceful_shutdown_registers_sigint_sigterm_handlers():
    app = Mock()
    manager = GracefulShutdownManager(timeout_seconds=1)

    with patch("template_mcp_server.utils.graceful_shutdown.signal.signal") as mock_signal:
        register_graceful_shutdown(app, manager, enabled=True)

    registered_signals = [call.args[0] for call in mock_signal.call_args_list]
    assert signal.SIGINT in registered_signals
    assert signal.SIGTERM in registered_signals


def test_register_graceful_shutdown_respects_feature_flag():
    app = Mock()
    manager = GracefulShutdownManager(timeout_seconds=1)

    with patch("template_mcp_server.utils.graceful_shutdown.signal.signal") as mock_signal:
        register_graceful_shutdown(app, manager, enabled=False)

    mock_signal.assert_not_called()


def test_graceful_shutdown_settings_defaults():
    settings = Settings()

    assert settings.ENABLE_GRACEFUL_SHUTDOWN is True
    assert settings.SHUTDOWN_TIMEOUT_SECONDS == 30
