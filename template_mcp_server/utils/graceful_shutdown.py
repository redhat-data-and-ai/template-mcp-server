"""Graceful shutdown helpers for production MCP server runs."""

from __future__ import annotations

import asyncio
import inspect
import signal
from collections.abc import Awaitable, Callable
from types import FrameType
from typing import Any

from template_mcp_server.utils.pylogger import get_python_logger

logger = get_python_logger()
CleanupCallback = Callable[[], Awaitable[None] | None]


class GracefulShutdownManager:
    """Coordinate bounded cleanup work during process shutdown."""

    def __init__(self, timeout_seconds: float = 30, logger: Any = logger) -> None:
        self.timeout_seconds = timeout_seconds
        self.logger = logger
        self.shutdown_requested = False
        self._cleanup_callbacks: list[CleanupCallback] = []

    def add_cleanup_callback(self, callback: CleanupCallback) -> None:
        """Register a cleanup callback to run during shutdown."""
        self._cleanup_callbacks.append(callback)

    async def shutdown(self, signum: signal.Signals | int | None = None) -> None:
        """Run registered cleanup callbacks with timeout protection."""
        if self.shutdown_requested:
            self.logger.debug("Graceful shutdown already requested")
            return

        self.shutdown_requested = True
        signal_name = _signal_name(signum)
        self.logger.info("Graceful shutdown initiated", signal=signal_name)

        try:
            await asyncio.wait_for(self._run_cleanup_callbacks(), self.timeout_seconds)
        except TimeoutError:
            self.logger.warning(
                "Graceful shutdown timed out",
                timeout_seconds=self.timeout_seconds,
            )

    async def _run_cleanup_callbacks(self) -> None:
        for callback in self._cleanup_callbacks:
            try:
                result = callback()
                if inspect.isawaitable(result):
                    await result
            except Exception as exc:
                if _is_closed_resource_error(exc):
                    self.logger.debug("Resource already closed during shutdown", error=str(exc))
                    continue
                self.logger.warning("Cleanup callback failed during shutdown", error=str(exc))


def register_graceful_shutdown(
    app: Any,
    manager: GracefulShutdownManager,
    *,
    enabled: bool = True,
) -> GracefulShutdownManager:
    """Register SIGINT/SIGTERM handlers and attach manager to the app state."""
    if hasattr(app, "state"):
        app.state.graceful_shutdown_manager = manager

    if not enabled:
        manager.logger.debug("Graceful shutdown signal handlers disabled")
        return manager

    def _handler(signum: int, _frame: FrameType | None) -> None:
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            asyncio.run(manager.shutdown(signum))
        else:
            loop.create_task(manager.shutdown(signum))

    signal.signal(signal.SIGINT, _handler)
    signal.signal(signal.SIGTERM, _handler)
    manager.logger.info("Graceful shutdown signal handlers registered")
    return manager


def _signal_name(signum: signal.Signals | int | None) -> str | None:
    if signum is None:
        return None
    try:
        return signal.Signals(signum).name
    except ValueError:
        return str(signum)


def _is_closed_resource_error(exc: Exception) -> bool:
    text = f"{exc.__class__.__name__}: {exc}".lower()
    return "closedresourceerror" in text or "closed resource" in text or "already closed" in text
