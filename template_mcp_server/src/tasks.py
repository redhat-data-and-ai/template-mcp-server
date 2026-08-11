"""MCP Tasks extension (SEP-2663).

Provides an in-memory task store for tracking long-running operations.
Supports the tasks/get, tasks/update, and tasks/cancel RPC methods.
tasks/list is removed in the 2026-07-28 spec.
"""

import time
from typing import Any, Dict, List, Optional

STATUS_PENDING = "pending"
STATUS_RUNNING = "running"
STATUS_COMPLETED = "completed"
STATUS_FAILED = "failed"
STATUS_CANCELLED = "cancelled"

_TERMINAL_STATUSES = frozenset({STATUS_COMPLETED, STATUS_FAILED, STATUS_CANCELLED})
_VALID_STATUSES = frozenset(
    {STATUS_PENDING, STATUS_RUNNING, STATUS_COMPLETED, STATUS_FAILED, STATUS_CANCELLED}
)


class TaskEntry:
    """A single tracked task."""

    def __init__(
        self,
        task_id: str,
        method: str,
        *,
        status: str = STATUS_PENDING,
        progress: Optional[float] = None,
        message: Optional[str] = None,
        result: Optional[Any] = None,
    ) -> None:
        """Initialize a task entry."""
        self.task_id = task_id
        self.method = method
        self.status = status
        self.progress = progress
        self.message = message
        self.result = result
        self.created_at = time.monotonic()
        self.updated_at = self.created_at

    def to_dict(self) -> Dict[str, Any]:
        """Serialize task to a JSON-compatible dict."""
        d: Dict[str, Any] = {
            "taskId": self.task_id,
            "method": self.method,
            "status": self.status,
        }
        if self.progress is not None:
            d["progress"] = self.progress
        if self.message is not None:
            d["message"] = self.message
        if self.result is not None:
            d["result"] = self.result
        return d

    @property
    def is_terminal(self) -> bool:
        """Return True if the task reached a terminal state."""
        return self.status in _TERMINAL_STATUSES


class TaskStore:
    """In-memory task store for SEP-2663."""

    def __init__(self) -> None:
        """Initialize an empty task store."""
        self._tasks: Dict[str, TaskEntry] = {}

    def create(self, task_id: str, method: str, **kwargs: Any) -> TaskEntry:
        """Create and store a new task entry."""
        entry = TaskEntry(task_id, method, **kwargs)
        self._tasks[task_id] = entry
        return entry

    def get(self, task_id: str) -> Optional[TaskEntry]:
        """Retrieve a task by ID."""
        return self._tasks.get(task_id)

    def update(
        self,
        task_id: str,
        *,
        status: Optional[str] = None,
        progress: Optional[float] = None,
        message: Optional[str] = None,
        result: Optional[Any] = None,
    ) -> Optional[TaskEntry]:
        """Update a non-terminal task's fields."""
        entry = self._tasks.get(task_id)
        if entry is None:
            return None
        if entry.is_terminal:
            return None
        if status is not None:
            if status not in _VALID_STATUSES:
                return None
            entry.status = status
        if progress is not None:
            entry.progress = max(0.0, min(progress, 1.0))
        if message is not None:
            entry.message = message
        if result is not None:
            entry.result = result
        entry.updated_at = time.monotonic()
        return entry

    def cancel(self, task_id: str) -> Optional[TaskEntry]:
        """Cancel a non-terminal task."""
        entry = self._tasks.get(task_id)
        if entry is None:
            return None
        if entry.is_terminal:
            return None
        entry.status = STATUS_CANCELLED
        entry.updated_at = time.monotonic()
        return entry

    @property
    def count(self) -> int:
        """Return total number of tracked tasks."""
        return len(self._tasks)

    def active_tasks(self) -> List[TaskEntry]:
        """Return tasks that have not reached a terminal state."""
        return [t for t in self._tasks.values() if not t.is_terminal]


task_store = TaskStore()
