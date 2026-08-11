"""Tests for feature lifecycle and deprecation metadata (SEP-2596, SEP-2577)."""

import pytest

from template_mcp_server.src.deprecation import (
    LIFECYCLE_ACTIVE,
    LIFECYCLE_DEPRECATED,
    LIFECYCLE_REMOVED,
    DeprecationEntry,
    DeprecationRegistry,
    deprecation_registry,
)


class TestLifecycleConstants:
    """Test lifecycle state constants."""

    def test_active(self):
        assert LIFECYCLE_ACTIVE == "active"

    def test_deprecated(self):
        assert LIFECYCLE_DEPRECATED == "deprecated"

    def test_removed(self):
        assert LIFECYCLE_REMOVED == "removed"


class TestDeprecationEntry:
    """Test DeprecationEntry model."""

    def test_minimal_entry(self):
        entry = DeprecationEntry("test_feature", LIFECYCLE_DEPRECATED)
        assert entry.feature == "test_feature"
        assert entry.lifecycle == LIFECYCLE_DEPRECATED
        assert entry.replacement is None

    def test_full_entry(self):
        entry = DeprecationEntry(
            "sampling",
            LIFECYCLE_DEPRECATED,
            replacement="direct LLM APIs",
            deprecated_since="2026-07-28",
            removed_in=None,
            migration="Use LLM provider APIs directly.",
        )
        assert entry.replacement == "direct LLM APIs"
        assert entry.deprecated_since == "2026-07-28"
        assert entry.migration == "Use LLM provider APIs directly."

    def test_to_dict_minimal(self):
        entry = DeprecationEntry("ping", LIFECYCLE_REMOVED)
        d = entry.to_dict()
        assert d == {"feature": "ping", "lifecycle": "removed"}
        assert "replacement" not in d

    def test_to_dict_full(self):
        entry = DeprecationEntry(
            "dcr",
            LIFECYCLE_DEPRECATED,
            replacement="CIMD",
            deprecated_since="2026-07-28",
            removed_in=None,
            migration="Use CIMD endpoint.",
        )
        d = entry.to_dict()
        assert d["feature"] == "dcr"
        assert d["lifecycle"] == "deprecated"
        assert d["replacement"] == "CIMD"
        assert d["deprecatedSince"] == "2026-07-28"
        assert d["migration"] == "Use CIMD endpoint."
        assert "removedIn" not in d

    def test_removed_entry_with_removed_in(self):
        entry = DeprecationEntry("ping", LIFECYCLE_REMOVED, removed_in="2026-07-28")
        d = entry.to_dict()
        assert d["removedIn"] == "2026-07-28"


class TestDeprecationRegistry:
    """Test DeprecationRegistry operations."""

    def test_register_and_get(self):
        reg = DeprecationRegistry()
        entry = DeprecationEntry("test", LIFECYCLE_DEPRECATED)
        reg.register(entry)
        assert reg.get("test") is entry

    def test_get_nonexistent(self):
        reg = DeprecationRegistry()
        assert reg.get("missing") is None

    def test_get_all(self):
        reg = DeprecationRegistry()
        reg.register(DeprecationEntry("a", LIFECYCLE_DEPRECATED))
        reg.register(DeprecationEntry("b", LIFECYCLE_REMOVED))
        assert len(reg.get_all()) == 2

    def test_get_by_lifecycle(self):
        reg = DeprecationRegistry()
        reg.register(DeprecationEntry("a", LIFECYCLE_DEPRECATED))
        reg.register(DeprecationEntry("b", LIFECYCLE_REMOVED))
        reg.register(DeprecationEntry("c", LIFECYCLE_DEPRECATED))
        deprecated = reg.get_by_lifecycle(LIFECYCLE_DEPRECATED)
        assert len(deprecated) == 2
        assert all(e.lifecycle == LIFECYCLE_DEPRECATED for e in deprecated)

    def test_to_list(self):
        reg = DeprecationRegistry()
        reg.register(DeprecationEntry("x", LIFECYCLE_REMOVED, removed_in="2026-07-28"))
        result = reg.to_list()
        assert len(result) == 1
        assert result[0]["feature"] == "x"

    def test_overwrite_entry(self):
        reg = DeprecationRegistry()
        reg.register(DeprecationEntry("x", LIFECYCLE_DEPRECATED))
        reg.register(DeprecationEntry("x", LIFECYCLE_REMOVED, removed_in="2026-07-28"))
        assert reg.get("x").lifecycle == LIFECYCLE_REMOVED


class TestPreregisteredEntries:
    """Test that the singleton registry has all 2026-07-28 spec entries."""

    def test_removed_features_registered(self):
        removed = deprecation_registry.get_by_lifecycle(LIFECYCLE_REMOVED)
        removed_names = {e.feature for e in removed}
        assert "sessions" in removed_names
        assert "initialize_handshake" in removed_names
        assert "ping" in removed_names
        assert "logging/setLevel" in removed_names
        assert "notifications/roots/list_changed" in removed_names
        assert "sse_resumability" in removed_names
        assert "elicitation/create" in removed_names
        assert "elicitation_notification" in removed_names
        assert "tasks/list" in removed_names

    def test_deprecated_features_registered(self):
        deprecated = deprecation_registry.get_by_lifecycle(LIFECYCLE_DEPRECATED)
        deprecated_names = {e.feature for e in deprecated}
        assert "roots" in deprecated_names
        assert "sampling" in deprecated_names
        assert "logging" in deprecated_names
        assert "http_sse_transport" in deprecated_names
        assert "includeContext" in deprecated_names
        assert "dcr" in deprecated_names

    def test_sep_2577_roots_has_migration(self):
        entry = deprecation_registry.get("roots")
        assert entry is not None
        assert entry.migration is not None
        assert "tool parameters" in entry.migration

    def test_sep_2577_sampling_has_migration(self):
        entry = deprecation_registry.get("sampling")
        assert entry is not None
        assert entry.migration is not None
        assert "LLM" in entry.migration

    def test_sep_2577_logging_has_migration(self):
        entry = deprecation_registry.get("logging")
        assert entry is not None
        assert entry.migration is not None
        assert "logLevel" in entry.migration

    def test_all_deprecated_have_deprecated_since(self):
        for entry in deprecation_registry.get_by_lifecycle(LIFECYCLE_DEPRECATED):
            assert entry.deprecated_since is not None, (
                f"{entry.feature} missing deprecated_since"
            )

    def test_total_entry_count(self):
        all_entries = deprecation_registry.get_all()
        assert len(all_entries) == 15
