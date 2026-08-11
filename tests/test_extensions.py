"""Tests for MCP Extensions framework (SEP-2133)."""

import pytest

from template_mcp_server.src.extensions import (
    EXTENSION_APPS,
    EXTENSION_TASKS,
    ExtensionRegistry,
    extension_registry,
)


class TestExtensionRegistry:
    """Test ExtensionRegistry core operations."""

    def test_register_and_retrieve(self):
        reg = ExtensionRegistry()
        reg.register("io.example/test", {"version": "1.0"})
        assert reg.is_registered("io.example/test")
        assert reg.get_extension("io.example/test") == {"version": "1.0"}

    def test_register_without_config(self):
        reg = ExtensionRegistry()
        reg.register("io.example/minimal")
        assert reg.is_registered("io.example/minimal")
        assert reg.get_extension("io.example/minimal") == {}

    def test_unregister(self):
        reg = ExtensionRegistry()
        reg.register("io.example/temp")
        reg.unregister("io.example/temp")
        assert not reg.is_registered("io.example/temp")

    def test_unregister_nonexistent_is_noop(self):
        reg = ExtensionRegistry()
        reg.unregister("io.example/nonexistent")

    def test_get_nonexistent_returns_none(self):
        reg = ExtensionRegistry()
        assert reg.get_extension("io.example/missing") is None

    def test_get_capabilities_returns_copy(self):
        reg = ExtensionRegistry()
        reg.register("io.example/a", {"x": 1})
        reg.register("io.example/b", {"y": 2})
        caps = reg.get_capabilities()
        assert caps == {"io.example/a": {"x": 1}, "io.example/b": {"y": 2}}
        caps["io.example/c"] = {}
        assert not reg.is_registered("io.example/c")

    def test_registered_ids(self):
        reg = ExtensionRegistry()
        reg.register("io.example/first")
        reg.register("io.example/second")
        assert set(reg.registered_ids) == {"io.example/first", "io.example/second"}

    def test_empty_registry(self):
        reg = ExtensionRegistry()
        assert reg.get_capabilities() == {}
        assert reg.registered_ids == []

    def test_overwrite_registration(self):
        reg = ExtensionRegistry()
        reg.register("io.example/test", {"v": 1})
        reg.register("io.example/test", {"v": 2})
        assert reg.get_extension("io.example/test") == {"v": 2}


class TestExtensionConstants:
    """Test well-known extension ID constants."""

    def test_apps_extension_id(self):
        assert EXTENSION_APPS == "io.modelcontextprotocol/ui"

    def test_tasks_extension_id(self):
        assert EXTENSION_TASKS == "io.modelcontextprotocol/tasks"


class TestSingletonRegistry:
    """Test the module-level singleton registry."""

    def test_singleton_exists(self):
        assert extension_registry is not None

    def test_singleton_is_extension_registry(self):
        assert isinstance(extension_registry, ExtensionRegistry)
