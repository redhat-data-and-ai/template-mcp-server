"""Tests for MCP Apps extension (SEP-1865) — 100% coverage."""

from template_mcp_server.src.apps import AppEntry, AppRegistry, app_registry


class TestAppEntry:
    """Test AppEntry model."""

    def test_to_dict_minimal(self):
        entry = AppEntry("test-app", "Test App")
        d = entry.to_dict()
        assert d["appId"] == "test-app"
        assert d["name"] == "Test App"
        assert d["uiType"] == "iframe"
        assert "description" not in d
        assert "url" not in d
        assert "metadata" not in d

    def test_to_dict_full(self):
        entry = AppEntry(
            "full-app",
            "Full App",
            description="A full app",
            ui_type="embedded",
            url="/ui/full",
            metadata={"version": "1.0"},
        )
        d = entry.to_dict()
        assert d["appId"] == "full-app"
        assert d["description"] == "A full app"
        assert d["uiType"] == "embedded"
        assert d["url"] == "/ui/full"
        assert d["metadata"] == {"version": "1.0"}

    def test_default_ui_type(self):
        entry = AppEntry("x", "X")
        assert entry.ui_type == "iframe"

    def test_default_metadata_empty(self):
        entry = AppEntry("x", "X")
        assert entry.metadata == {}


class TestAppRegistry:
    """Test AppRegistry class."""

    def test_register_and_get(self):
        reg = AppRegistry()
        entry = AppEntry("a1", "App 1")
        reg.register(entry)
        assert reg.get("a1") is entry

    def test_get_missing_returns_none(self):
        reg = AppRegistry()
        assert reg.get("missing") is None

    def test_unregister_existing(self):
        reg = AppRegistry()
        reg.register(AppEntry("a1", "App 1"))
        assert reg.unregister("a1") is True
        assert reg.get("a1") is None

    def test_unregister_missing(self):
        reg = AppRegistry()
        assert reg.unregister("missing") is False

    def test_list_apps(self):
        reg = AppRegistry()
        reg.register(AppEntry("a1", "App 1"))
        reg.register(AppEntry("a2", "App 2"))
        apps = reg.list_apps()
        assert len(apps) == 2
        ids = {a["appId"] for a in apps}
        assert ids == {"a1", "a2"}

    def test_count(self):
        reg = AppRegistry()
        assert reg.count == 0
        reg.register(AppEntry("a1", "App 1"))
        assert reg.count == 1

    def test_get_extension_config(self):
        reg = AppRegistry()
        reg.register(AppEntry("a1", "App 1"))
        config = reg.get_extension_config()
        assert config["appCount"] == 1
        assert len(config["apps"]) == 1
        assert config["apps"][0]["appId"] == "a1"


class TestModuleLevelRegistry:
    """Test module-level app_registry singleton."""

    def test_app_registry_is_instance(self):
        assert isinstance(app_registry, AppRegistry)
