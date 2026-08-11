"""Tests for MCP Tasks extension (SEP-2663) — 100% coverage."""

from template_mcp_server.src.tasks import (
    STATUS_CANCELLED,
    STATUS_COMPLETED,
    STATUS_FAILED,
    STATUS_PENDING,
    STATUS_RUNNING,
    TaskEntry,
    TaskStore,
    task_store,
)


class TestTaskEntry:
    """Test TaskEntry model."""

    def test_defaults(self):
        entry = TaskEntry("t1", "tools/call")
        assert entry.task_id == "t1"
        assert entry.method == "tools/call"
        assert entry.status == STATUS_PENDING
        assert entry.progress is None
        assert entry.message is None
        assert entry.result is None

    def test_to_dict_minimal(self):
        entry = TaskEntry("t1", "tools/call")
        d = entry.to_dict()
        assert d["taskId"] == "t1"
        assert d["method"] == "tools/call"
        assert d["status"] == "pending"
        assert "progress" not in d
        assert "message" not in d
        assert "result" not in d

    def test_to_dict_full(self):
        entry = TaskEntry(
            "t1",
            "tools/call",
            status=STATUS_RUNNING,
            progress=0.75,
            message="Processing",
            result={"output": "data"},
        )
        d = entry.to_dict()
        assert d["progress"] == 0.75
        assert d["message"] == "Processing"
        assert d["result"] == {"output": "data"}

    def test_is_terminal_pending(self):
        assert not TaskEntry("t", "m", status=STATUS_PENDING).is_terminal

    def test_is_terminal_running(self):
        assert not TaskEntry("t", "m", status=STATUS_RUNNING).is_terminal

    def test_is_terminal_completed(self):
        assert TaskEntry("t", "m", status=STATUS_COMPLETED).is_terminal

    def test_is_terminal_failed(self):
        assert TaskEntry("t", "m", status=STATUS_FAILED).is_terminal

    def test_is_terminal_cancelled(self):
        assert TaskEntry("t", "m", status=STATUS_CANCELLED).is_terminal

    def test_timestamps_set(self):
        entry = TaskEntry("t1", "m")
        assert entry.created_at > 0
        assert entry.updated_at == entry.created_at


class TestTaskStore:
    """Test TaskStore class."""

    def test_create_and_get(self):
        store = TaskStore()
        entry = store.create("t1", "tools/call")
        assert store.get("t1") is entry
        assert entry.status == STATUS_PENDING

    def test_get_missing_returns_none(self):
        store = TaskStore()
        assert store.get("missing") is None

    def test_update_status(self):
        store = TaskStore()
        store.create("t1", "tools/call")
        entry = store.update("t1", status=STATUS_RUNNING)
        assert entry is not None
        assert entry.status == STATUS_RUNNING

    def test_update_progress(self):
        store = TaskStore()
        store.create("t1", "tools/call")
        entry = store.update("t1", progress=0.5)
        assert entry.progress == 0.5

    def test_update_progress_clamps_to_range(self):
        store = TaskStore()
        store.create("t1", "tools/call")
        entry = store.update("t1", progress=1.5)
        assert entry.progress == 1.0
        entry = store.update("t1", progress=-0.5)
        assert entry.progress == 0.0

    def test_update_message(self):
        store = TaskStore()
        store.create("t1", "tools/call")
        entry = store.update("t1", message="halfway")
        assert entry.message == "halfway"

    def test_update_result(self):
        store = TaskStore()
        store.create("t1", "tools/call")
        entry = store.update("t1", result={"bmi": 22.5})
        assert entry.result == {"bmi": 22.5}

    def test_update_missing_returns_none(self):
        store = TaskStore()
        assert store.update("missing", status=STATUS_RUNNING) is None

    def test_update_terminal_returns_none(self):
        store = TaskStore()
        store.create("t1", "tools/call", status=STATUS_COMPLETED)
        assert store.update("t1", status=STATUS_RUNNING) is None

    def test_update_invalid_status_returns_none(self):
        store = TaskStore()
        store.create("t1", "tools/call")
        assert store.update("t1", status="invalid_status") is None

    def test_cancel_running(self):
        store = TaskStore()
        store.create("t1", "tools/call", status=STATUS_RUNNING)
        entry = store.cancel("t1")
        assert entry is not None
        assert entry.status == STATUS_CANCELLED

    def test_cancel_pending(self):
        store = TaskStore()
        store.create("t1", "tools/call")
        entry = store.cancel("t1")
        assert entry.status == STATUS_CANCELLED

    def test_cancel_missing_returns_none(self):
        store = TaskStore()
        assert store.cancel("missing") is None

    def test_cancel_terminal_returns_none(self):
        store = TaskStore()
        store.create("t1", "tools/call", status=STATUS_COMPLETED)
        assert store.cancel("t1") is None

    def test_count(self):
        store = TaskStore()
        assert store.count == 0
        store.create("t1", "tools/call")
        assert store.count == 1
        store.create("t2", "tools/call")
        assert store.count == 2

    def test_active_tasks(self):
        store = TaskStore()
        store.create("t1", "tools/call", status=STATUS_RUNNING)
        store.create("t2", "tools/call", status=STATUS_COMPLETED)
        store.create("t3", "tools/call", status=STATUS_PENDING)
        active = store.active_tasks()
        active_ids = {t.task_id for t in active}
        assert active_ids == {"t1", "t3"}

    def test_update_changes_timestamp(self):
        store = TaskStore()
        entry = store.create("t1", "tools/call")
        original_ts = entry.updated_at
        store.update("t1", message="updated")
        assert entry.updated_at >= original_ts


class TestModuleLevelStore:
    """Test module-level task_store singleton."""

    def test_task_store_is_instance(self):
        assert isinstance(task_store, TaskStore)
