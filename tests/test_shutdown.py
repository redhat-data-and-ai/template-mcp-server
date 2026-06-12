"""Tests for the graceful shutdown module."""

import asyncio
import signal
import sys
from concurrent.futures import ThreadPoolExecutor
from unittest.mock import AsyncMock, MagicMock, Mock, patch

import pytest

from template_mcp_server.src.main import main  # noqa: F401 — loaded for patch targets
from template_mcp_server.src.shutdown import (
    _cleanup_http_clients,
    _cleanup_storage,
    _graceful_shutdown,
    _install_closed_resource_handler,
    _make_signal_handler,
    install_signal_handlers,
    is_shutting_down,
    register_executor,
    shutdown_all_executors,
)


class TestShutdownState:
    """Test module-level shutdown state."""

    def test_is_shutting_down_default(self):
        """Test that is_shutting_down returns False by default."""
        import template_mcp_server.src.shutdown as mod

        original = mod._is_shutting_down
        try:
            mod._is_shutting_down = False
            assert is_shutting_down() is False
        finally:
            mod._is_shutting_down = original

    def test_is_shutting_down_true(self):
        """Test that is_shutting_down returns True when set."""
        import template_mcp_server.src.shutdown as mod

        original = mod._is_shutting_down
        try:
            mod._is_shutting_down = True
            assert is_shutting_down() is True
        finally:
            mod._is_shutting_down = original


class TestExecutorRegistry:
    """Test the executor registration and shutdown."""

    def setup_method(self):
        """Clear the executor registry before each test."""
        import template_mcp_server.src.shutdown as mod

        self._original_executors = mod._executors.copy()
        mod._executors.clear()

    def teardown_method(self):
        """Restore the executor registry after each test."""
        import template_mcp_server.src.shutdown as mod

        mod._executors.clear()
        mod._executors.extend(self._original_executors)

    def test_register_executor(self):
        """Test registering a thread pool executor."""
        import template_mcp_server.src.shutdown as mod

        executor = Mock(spec=ThreadPoolExecutor)
        register_executor(executor)
        assert executor in mod._executors

    def test_shutdown_all_executors(self):
        """Test shutting down all registered executors."""
        import template_mcp_server.src.shutdown as mod

        executor1 = Mock(spec=ThreadPoolExecutor)
        executor2 = Mock(spec=ThreadPoolExecutor)
        register_executor(executor1)
        register_executor(executor2)

        shutdown_all_executors(timeout=5.0)

        executor1.shutdown.assert_called_once_with(wait=True, cancel_futures=True)
        executor2.shutdown.assert_called_once_with(wait=True, cancel_futures=True)
        assert len(mod._executors) == 0

    def test_shutdown_all_executors_handles_errors(self):
        """Test that executor shutdown handles errors gracefully."""
        executor = Mock(spec=ThreadPoolExecutor)
        executor.shutdown.side_effect = RuntimeError("shutdown failed")
        register_executor(executor)

        # Should not raise
        shutdown_all_executors(timeout=5.0)

    def test_shutdown_all_executors_empty_list(self):
        """Test shutting down when no executors are registered."""
        # Should not raise
        shutdown_all_executors(timeout=5.0)


class TestCleanupStorage:
    """Test storage cleanup during shutdown."""

    @pytest.mark.asyncio
    async def test_cleanup_storage_success(self):
        """Test successful storage cleanup."""
        mock_cleanup = AsyncMock()
        with patch("template_mcp_server.src.shutdown.logger") as mock_logger:
            with patch.dict(
                "sys.modules",
                {
                    "template_mcp_server.src.oauth.service": MagicMock(
                        cleanup_storage=mock_cleanup
                    )
                },
            ):
                with patch(
                    "template_mcp_server.src.oauth.service.cleanup_storage",
                    mock_cleanup,
                    create=True,
                ):
                    await _cleanup_storage()
                    mock_logger.info.assert_called()

    @pytest.mark.asyncio
    async def test_cleanup_storage_import_error(self):
        """Test cleanup when storage module is not available."""
        with patch("template_mcp_server.src.shutdown.logger") as mock_logger:
            with patch.dict(
                "sys.modules", {"template_mcp_server.src.oauth.service": None}
            ):
                await _cleanup_storage()
                mock_logger.debug.assert_called()


class TestCleanupHttpClients:
    """Test HTTP client cleanup during shutdown."""

    @pytest.mark.asyncio
    async def test_cleanup_http_clients_success(self):
        """Test successful HTTP client cleanup."""
        with patch("template_mcp_server.src.shutdown.logger") as mock_logger:
            await _cleanup_http_clients()
            mock_logger.debug.assert_called()


class TestGracefulShutdown:
    """Test the async graceful shutdown sequence."""

    def setup_method(self):
        """Reset shutdown state."""
        import template_mcp_server.src.shutdown as mod

        self._original_state = mod._is_shutting_down
        mod._is_shutting_down = False
        self._original_executors = mod._executors.copy()
        mod._executors.clear()

    def teardown_method(self):
        """Restore shutdown state."""
        import template_mcp_server.src.shutdown as mod

        mod._is_shutting_down = self._original_state
        mod._executors.clear()
        mod._executors.extend(self._original_executors)

    @pytest.mark.asyncio
    async def test_graceful_shutdown_sets_flag(self):
        """Test that graceful shutdown sets the is_shutting_down flag."""
        import template_mcp_server.src.shutdown as mod

        with patch.object(mod, "shutdown_all_executors"):
            with patch.object(mod, "_cleanup_storage", new_callable=AsyncMock):
                with patch.object(mod, "_cleanup_http_clients", new_callable=AsyncMock):
                    await _graceful_shutdown(timeout=5)

        assert mod._is_shutting_down is True

    @pytest.mark.asyncio
    async def test_graceful_shutdown_calls_cleanup(self):
        """Test that graceful shutdown calls all cleanup functions."""
        import template_mcp_server.src.shutdown as mod

        mock_storage = AsyncMock()
        mock_http = AsyncMock()

        with patch.object(mod, "shutdown_all_executors") as mock_exec:
            with patch.object(mod, "_cleanup_storage", mock_storage):
                with patch.object(mod, "_cleanup_http_clients", mock_http):
                    await _graceful_shutdown(timeout=10)

        mock_exec.assert_called_once()
        mock_storage.assert_awaited_once()
        mock_http.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_graceful_shutdown_handles_executor_timeout(self):
        """Test that executor cleanup timeout is handled."""
        import template_mcp_server.src.shutdown as mod

        with patch.object(
            mod, "shutdown_all_executors", side_effect=lambda *a: asyncio.sleep(100)
        ):
            with patch.object(mod, "_cleanup_storage", new_callable=AsyncMock):
                with patch.object(mod, "_cleanup_http_clients", new_callable=AsyncMock):
                    # Should complete without hanging — timeout is short
                    await _graceful_shutdown(timeout=1)

        assert mod._is_shutting_down is True


class TestClosedResourceHandler:
    """Test the ClosedResourceError exception hook."""

    def test_install_closed_resource_handler(self):
        """Test that the exception hook is installed."""
        original_hook = sys.excepthook
        try:
            _install_closed_resource_handler()
            assert sys.excepthook is not original_hook
        finally:
            sys.excepthook = original_hook

    def test_closed_resource_suppressed_during_shutdown(self):
        """Test that ConnectionResetError is suppressed during shutdown."""
        import template_mcp_server.src.shutdown as mod

        original_hook = sys.excepthook
        original_state = mod._is_shutting_down
        try:
            mod._is_shutting_down = True
            _install_closed_resource_handler()

            # This should not raise or print traceback
            err = ConnectionResetError("Connection reset")
            with patch("template_mcp_server.src.shutdown.logger") as mock_logger:
                sys.excepthook(type(err), err, None)
                mock_logger.debug.assert_called()
        finally:
            sys.excepthook = original_hook
            mod._is_shutting_down = original_state

    def test_non_closed_resource_not_suppressed(self):
        """Test that non-ClosedResourceError exceptions are not suppressed."""
        import template_mcp_server.src.shutdown as mod

        original_hook = sys.excepthook
        original_state = mod._is_shutting_down
        try:
            mod._is_shutting_down = True
            mock_original = Mock()
            sys.excepthook = mock_original
            _install_closed_resource_handler()

            err = ValueError("some other error")
            sys.excepthook(type(err), err, None)
            mock_original.assert_called_once_with(type(err), err, None)
        finally:
            sys.excepthook = original_hook
            mod._is_shutting_down = original_state

    def test_errors_pass_through_when_not_shutting_down(self):
        """Test that errors are not suppressed when not shutting down."""
        import template_mcp_server.src.shutdown as mod

        original_hook = sys.excepthook
        original_state = mod._is_shutting_down
        try:
            mod._is_shutting_down = False
            mock_original = Mock()
            sys.excepthook = mock_original
            _install_closed_resource_handler()

            err = ConnectionResetError("Connection reset")
            sys.excepthook(type(err), err, None)
            mock_original.assert_called_once_with(type(err), err, None)
        finally:
            sys.excepthook = original_hook
            mod._is_shutting_down = original_state


class TestSignalHandler:
    """Test signal handler creation and behaviour."""

    def test_make_signal_handler_returns_callable(self):
        """Test that _make_signal_handler returns a callable."""
        handler = _make_signal_handler(timeout=30)
        assert callable(handler)

    @patch("template_mcp_server.src.shutdown.asyncio")
    @patch("template_mcp_server.src.shutdown.logger")
    def test_signal_handler_first_signal(self, mock_logger, mock_asyncio):
        """Test that first signal initiates graceful shutdown."""
        mock_loop = Mock()
        mock_asyncio.get_running_loop.return_value = mock_loop
        mock_loop.create_task = Mock()
        mock_loop.call_later = Mock()

        handler = _make_signal_handler(timeout=30)
        handler(signal.SIGTERM, None)

        mock_logger.info.assert_called()
        mock_loop.create_task.assert_called_once()

    @patch("template_mcp_server.src.shutdown.asyncio")
    @patch("template_mcp_server.src.shutdown.sys")
    @patch("template_mcp_server.src.shutdown.logger")
    def test_signal_handler_second_signal_forces_exit(
        self, mock_logger, mock_sys, mock_asyncio
    ):
        """Test that second signal forces immediate exit."""
        mock_loop = Mock()
        mock_asyncio.get_running_loop.return_value = mock_loop
        mock_loop.create_task = Mock()
        mock_loop.call_later = Mock()

        handler = _make_signal_handler(timeout=30)

        # First signal — starts graceful shutdown
        handler(signal.SIGTERM, None)

        # Second signal — should force exit
        handler(signal.SIGTERM, None)
        mock_sys.exit.assert_called_with(1)

    @patch("template_mcp_server.src.shutdown.shutdown_all_executors")
    @patch("template_mcp_server.src.shutdown.sys")
    @patch("template_mcp_server.src.shutdown.logger")
    def test_signal_handler_no_event_loop(self, mock_logger, mock_sys, mock_exec):
        """Test signal handler when no event loop is running."""
        with patch("template_mcp_server.src.shutdown.asyncio") as mock_asyncio:
            mock_asyncio.get_running_loop.side_effect = RuntimeError("no loop")

            handler = _make_signal_handler(timeout=30)
            handler(signal.SIGTERM, None)

            mock_exec.assert_called_once()
            mock_sys.exit.assert_called_with(0)


class TestInstallSignalHandlers:
    """Test the public install_signal_handlers function."""

    @patch("template_mcp_server.src.shutdown.signal")
    @patch("template_mcp_server.src.shutdown.logger")
    def test_install_signal_handlers(self, mock_logger, mock_signal):
        """Test that signal handlers are registered for SIGINT and SIGTERM."""
        mock_signal.SIGINT = signal.SIGINT
        mock_signal.SIGTERM = signal.SIGTERM

        install_signal_handlers(timeout=30)

        # Two signal.signal calls: SIGINT and SIGTERM
        assert mock_signal.signal.call_count == 2
        mock_logger.info.assert_called()

    @patch("template_mcp_server.src.shutdown.signal")
    @patch("template_mcp_server.src.shutdown.logger")
    def test_install_signal_handlers_custom_timeout(self, mock_logger, mock_signal):
        """Test that custom timeout is passed through."""
        mock_signal.SIGINT = signal.SIGINT
        mock_signal.SIGTERM = signal.SIGTERM

        install_signal_handlers(timeout=60)

        mock_logger.info.assert_called()
        # Verify the timeout appears in the log message
        call_kwargs = mock_logger.info.call_args
        assert 60 in call_kwargs[1].values() or any(
            60 in (v if isinstance(v, (list, tuple)) else [v])
            for v in call_kwargs[1].values()
        )


class TestMainIntegration:
    """Test graceful shutdown integration with main.py."""

    @patch("template_mcp_server.src.main.validate_config")
    @patch("template_mcp_server.src.main.logger")
    @patch("template_mcp_server.src.main.uvicorn")
    @patch("template_mcp_server.src.main.install_signal_handlers")
    def test_main_installs_signal_handlers_when_enabled(
        self, mock_install, mock_uvicorn, mock_logger, mock_validate
    ):
        """Test that main() installs signal handlers when feature flag is True."""

        mock_settings = Mock()
        mock_settings.MCP_HOST = "0.0.0.0"
        mock_settings.MCP_PORT = 4000
        mock_settings.MCP_TRANSPORT_PROTOCOL = "http"
        mock_settings.MCP_SSL_KEYFILE = None
        mock_settings.MCP_SSL_CERTFILE = None
        mock_settings.PYTHON_LOG_LEVEL = "INFO"
        mock_settings.ENABLE_GRACEFUL_SHUTDOWN = True
        mock_settings.SHUTDOWN_TIMEOUT_SECONDS = 30

        with patch("template_mcp_server.src.main.settings", mock_settings):
            main()

        mock_install.assert_called_once_with(timeout=30)

    @patch("template_mcp_server.src.main.validate_config")
    @patch("template_mcp_server.src.main.logger")
    @patch("template_mcp_server.src.main.uvicorn")
    @patch("template_mcp_server.src.main.install_signal_handlers")
    def test_main_skips_signal_handlers_when_disabled(
        self, mock_install, mock_uvicorn, mock_logger, mock_validate
    ):
        """Test that main() does NOT install signal handlers when feature flag is False."""

        mock_settings = Mock()
        mock_settings.MCP_HOST = "0.0.0.0"
        mock_settings.MCP_PORT = 4000
        mock_settings.MCP_TRANSPORT_PROTOCOL = "http"
        mock_settings.MCP_SSL_KEYFILE = None
        mock_settings.MCP_SSL_CERTFILE = None
        mock_settings.PYTHON_LOG_LEVEL = "INFO"
        mock_settings.ENABLE_GRACEFUL_SHUTDOWN = False
        mock_settings.SHUTDOWN_TIMEOUT_SECONDS = 30

        with patch("template_mcp_server.src.main.settings", mock_settings):
            main()

        mock_install.assert_not_called()

    @patch("template_mcp_server.src.main.validate_config")
    @patch("template_mcp_server.src.main.logger")
    @patch("template_mcp_server.src.main.uvicorn")
    @patch("template_mcp_server.src.main.install_signal_handlers")
    @patch("template_mcp_server.src.main.is_shutting_down", return_value=True)
    def test_main_keyboard_interrupt_during_shutdown(
        self, mock_is_shutting, mock_install, mock_uvicorn, mock_logger, mock_validate
    ):
        """Test that KeyboardInterrupt during shutdown logs correctly."""

        mock_settings = Mock()
        mock_settings.MCP_HOST = "0.0.0.0"
        mock_settings.MCP_PORT = 4000
        mock_settings.MCP_TRANSPORT_PROTOCOL = "http"
        mock_settings.MCP_SSL_KEYFILE = None
        mock_settings.MCP_SSL_CERTFILE = None
        mock_settings.PYTHON_LOG_LEVEL = "INFO"
        mock_settings.ENABLE_GRACEFUL_SHUTDOWN = True
        mock_settings.SHUTDOWN_TIMEOUT_SECONDS = 30

        mock_uvicorn.run.side_effect = KeyboardInterrupt()

        with patch("template_mcp_server.src.main.settings", mock_settings):
            main()

        mock_logger.info.assert_any_call("Shutdown complete (signal handler)")

    @patch("template_mcp_server.src.main.validate_config")
    @patch("template_mcp_server.src.main.logger")
    @patch("template_mcp_server.src.main.uvicorn")
    @patch("template_mcp_server.src.main.install_signal_handlers")
    @patch("template_mcp_server.src.main.is_shutting_down", return_value=True)
    def test_main_connection_reset_suppressed_during_shutdown(
        self, mock_is_shutting, mock_install, mock_uvicorn, mock_logger, mock_validate
    ):
        """Test that ConnectionResetError is suppressed during shutdown."""

        mock_settings = Mock()
        mock_settings.MCP_HOST = "0.0.0.0"
        mock_settings.MCP_PORT = 4000
        mock_settings.MCP_TRANSPORT_PROTOCOL = "http"
        mock_settings.MCP_SSL_KEYFILE = None
        mock_settings.MCP_SSL_CERTFILE = None
        mock_settings.PYTHON_LOG_LEVEL = "INFO"
        mock_settings.ENABLE_GRACEFUL_SHUTDOWN = True
        mock_settings.SHUTDOWN_TIMEOUT_SECONDS = 30

        mock_uvicorn.run.side_effect = ConnectionResetError("reset")

        with patch("template_mcp_server.src.main.settings", mock_settings):
            main()  # Should not raise

        mock_logger.debug.assert_any_call(
            "ClosedResourceError suppressed during shutdown"
        )
