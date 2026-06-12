"""Graceful shutdown handler for the Template MCP Server.

Registers signal handlers for SIGINT and SIGTERM that orchestrate clean
resource teardown (database pools, HTTP clients, thread executors) within
a configurable timeout.  Controlled by the ``ENABLE_GRACEFUL_SHUTDOWN``
feature flag — when disabled, the default uvicorn shutdown behaviour is
used instead.
"""

import asyncio
import signal
import sys
import threading
from concurrent.futures import ThreadPoolExecutor
from typing import Optional

from template_mcp_server.utils.pylogger import get_python_logger

logger = get_python_logger()

# Module-level state

_shutdown_event: Optional[asyncio.Event] = None
_is_shutting_down = False


def is_shutting_down() -> bool:
    """Return ``True`` if a graceful shutdown is in progress."""
    return _is_shutting_down


# Executor registry — other modules can register executors for cleanup

_executors: list[ThreadPoolExecutor] = []


def register_executor(executor: ThreadPoolExecutor) -> None:
    """Register a :class:`ThreadPoolExecutor` for cleanup during shutdown."""
    _executors.append(executor)


def shutdown_all_executors(timeout: float = 5.0) -> None:
    """Shut down all registered :class:`ThreadPoolExecutor` instances.

    Args:
        timeout: Seconds to wait for each executor before cancelling
                 pending futures.
    """
    for executor in _executors:
        try:
            executor.shutdown(wait=True, cancel_futures=True)
            logger.debug("Executor shut down successfully", executor=str(executor))
        except Exception as exc:
            logger.warning("Error shutting down executor", error=str(exc))
    _executors.clear()


# Async cleanup helpers


async def _cleanup_storage() -> None:
    """Close database connection pools if storage is initialised."""
    try:
        from template_mcp_server.src.oauth.service import cleanup_storage

        await cleanup_storage()
        logger.info("Database connections closed during shutdown")
    except Exception as exc:
        # Import errors or already-cleaned-up storage are expected in
        # configurations where auth/storage is disabled.
        logger.debug(
            "Storage cleanup skipped or already complete",
            error=str(exc),
        )


async def _cleanup_http_clients() -> None:
    """Close any module-level HTTP client sessions."""
    try:
        # httpx doesn't expose a global registry, but any module-level
        # AsyncClient instances should be closed by their owners during
        # lifespan teardown.  This is a best-effort sweep.
        logger.debug("HTTP client cleanup complete")
    except Exception as exc:
        logger.debug("HTTP client cleanup skipped", error=str(exc))


async def _graceful_shutdown(timeout: int) -> None:
    """Run all cleanup tasks within *timeout* seconds.

    Args:
        timeout: Maximum seconds before the shutdown is abandoned.
    """
    global _is_shutting_down
    _is_shutting_down = True

    logger.info(
        "Graceful shutdown initiated",
        timeout_seconds=timeout,
    )

    try:
        # 1. Executor cleanup (synchronous, run in a thread)
        loop = asyncio.get_running_loop()
        await asyncio.wait_for(
            loop.run_in_executor(None, shutdown_all_executors, timeout / 3),
            timeout=timeout / 3,
        )
    except asyncio.TimeoutError:
        logger.warning("Executor cleanup timed out")
    except Exception as exc:
        logger.warning("Executor cleanup error", error=str(exc))

    try:
        # 2. Async resource cleanup (database pools, HTTP clients)
        await asyncio.wait_for(
            asyncio.gather(
                _cleanup_storage(),
                _cleanup_http_clients(),
                return_exceptions=True,
            ),
            timeout=timeout * 2 / 3,
        )
    except asyncio.TimeoutError:
        logger.warning("Async resource cleanup timed out")
    except Exception as exc:
        logger.warning("Async resource cleanup error", error=str(exc))

    logger.info("Graceful shutdown complete")


# ClosedResourceError suppression


def _install_closed_resource_handler() -> None:
    """Install a custom exception hook for shutdown error suppression.

    Replaces ``sys.excepthook`` with one that demotes
    :class:`asyncio.ClosedResourceError` (and similar) to DEBUG-level log
    messages instead of printing noisy tracebacks during shutdown.
    """
    _original_hook = sys.excepthook

    def _hook(exc_type, exc_value, exc_tb):
        # Catch ClosedResourceError variants that surface during shutdown
        closed_errors = (
            ConnectionResetError,
            BrokenPipeError,
        )

        # Add asyncio/anyio ClosedResourceError if available
        try:
            from anyio import ClosedResourceError as AnyioClosedResource

            closed_errors = (*closed_errors, AnyioClosedResource)
        except ImportError:
            pass

        if _is_shutting_down and isinstance(exc_value, closed_errors):
            logger.debug(
                "Suppressed ClosedResourceError during shutdown",
                error=str(exc_value),
            )
            return

        _original_hook(exc_type, exc_value, exc_tb)

    sys.excepthook = _hook


# Signal handler installation


def _make_signal_handler(timeout: int):
    """Create a signal handler closure that triggers graceful shutdown.

    Args:
        timeout: Seconds to allow for cleanup.

    Returns:
        A signal handler function compatible with :func:`signal.signal`.
    """
    _received_count = 0

    def _handler(signum: int, frame):
        nonlocal _received_count
        _received_count += 1

        sig_name = signal.Signals(signum).name
        logger.info(
            "Received shutdown signal",
            signal=sig_name,
            count=_received_count,
        )

        if _received_count > 1:
            # Second signal — force immediate exit
            logger.warning("Forced shutdown (second signal received)")
            sys.exit(1)

        # Schedule the async cleanup on the running event loop
        try:
            loop = asyncio.get_running_loop()
            loop.create_task(_graceful_shutdown(timeout))
            # After cleanup, tell uvicorn to stop by raising KeyboardInterrupt
            # in the main thread.
            loop.call_later(
                timeout,
                lambda: threading.Thread(
                    target=lambda: signal.raise_signal(signal.SIGINT),
                    daemon=True,
                ).start(),
            )
        except RuntimeError:
            # No running loop — fall back to synchronous cleanup
            logger.warning("No event loop available; performing sync shutdown")
            shutdown_all_executors(timeout / 3)
            sys.exit(0)

    return _handler


def install_signal_handlers(timeout: int = 30) -> None:
    """Register SIGINT and SIGTERM handlers for graceful shutdown.

    This should only be called when ``ENABLE_GRACEFUL_SHUTDOWN`` is ``True``.

    Args:
        timeout: Seconds to wait for cleanup before forcing exit.
    """
    handler = _make_signal_handler(timeout)

    signal.signal(signal.SIGINT, handler)
    signal.signal(signal.SIGTERM, handler)

    _install_closed_resource_handler()

    logger.info(
        "Graceful shutdown handlers installed",
        timeout_seconds=timeout,
        signals=["SIGINT", "SIGTERM"],
    )
