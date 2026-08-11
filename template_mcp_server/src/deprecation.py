"""Feature lifecycle and deprecation metadata (SEP-2596, SEP-2577).

Tracks the Active → Deprecated → Removed lifecycle for MCP protocol features.
All entries from the 2026-07-28 specification are pre-registered.
"""

from typing import Any, Dict, List, Optional

LIFECYCLE_ACTIVE = "active"
LIFECYCLE_DEPRECATED = "deprecated"
LIFECYCLE_REMOVED = "removed"


class DeprecationEntry:
    """A single deprecated or removed feature."""

    def __init__(
        self,
        feature: str,
        lifecycle: str,
        *,
        replacement: Optional[str] = None,
        deprecated_since: Optional[str] = None,
        removed_in: Optional[str] = None,
        migration: Optional[str] = None,
    ) -> None:
        """Initialize a deprecation entry."""
        self.feature = feature
        self.lifecycle = lifecycle
        self.replacement = replacement
        self.deprecated_since = deprecated_since
        self.removed_in = removed_in
        self.migration = migration

    def to_dict(self) -> Dict[str, Any]:
        """Serialize entry to JSON-compatible dict."""
        result: Dict[str, Any] = {
            "feature": self.feature,
            "lifecycle": self.lifecycle,
        }
        if self.replacement:
            result["replacement"] = self.replacement
        if self.deprecated_since:
            result["deprecatedSince"] = self.deprecated_since
        if self.removed_in:
            result["removedIn"] = self.removed_in
        if self.migration:
            result["migration"] = self.migration
        return result


class DeprecationRegistry:
    """Registry of deprecated and removed features (SEP-2596)."""

    def __init__(self) -> None:
        """Initialize an empty deprecation registry."""
        self._entries: Dict[str, DeprecationEntry] = {}

    def register(self, entry: DeprecationEntry) -> None:
        """Register a deprecation entry."""
        self._entries[entry.feature] = entry

    def get(self, feature: str) -> Optional[DeprecationEntry]:
        """Look up a feature by name."""
        return self._entries.get(feature)

    def get_all(self) -> List[DeprecationEntry]:
        """Return all entries."""
        return list(self._entries.values())

    def get_by_lifecycle(self, lifecycle: str) -> List[DeprecationEntry]:
        """Filter entries by lifecycle stage."""
        return [e for e in self._entries.values() if e.lifecycle == lifecycle]

    def to_list(self) -> List[Dict[str, Any]]:
        """Serialize all entries to a list of dicts."""
        return [e.to_dict() for e in self._entries.values()]


deprecation_registry = DeprecationRegistry()

_SPEC_VERSION = "2026-07-28"
_PREV_SPEC_VERSION = "2025-11-05"

# ── Removed features (SEP-2575, SEP-2567) ──────────────────────────────

_REMOVED = [
    DeprecationEntry(
        "sessions",
        LIFECYCLE_REMOVED,
        replacement="stateless HTTP",
        deprecated_since=_PREV_SPEC_VERSION,
        removed_in=_SPEC_VERSION,
    ),
    DeprecationEntry(
        "initialize_handshake",
        LIFECYCLE_REMOVED,
        replacement="server/discover + _meta fields",
        deprecated_since=_PREV_SPEC_VERSION,
        removed_in=_SPEC_VERSION,
    ),
    DeprecationEntry("ping", LIFECYCLE_REMOVED, removed_in=_SPEC_VERSION),
    DeprecationEntry(
        "logging/setLevel",
        LIFECYCLE_REMOVED,
        replacement="logLevel in _meta per-request",
        removed_in=_SPEC_VERSION,
    ),
    DeprecationEntry(
        "notifications/roots/list_changed",
        LIFECYCLE_REMOVED,
        removed_in=_SPEC_VERSION,
    ),
    DeprecationEntry(
        "sse_resumability",
        LIFECYCLE_REMOVED,
        replacement="client re-issues request",
        removed_in=_SPEC_VERSION,
    ),
    DeprecationEntry(
        "elicitation/create",
        LIFECYCLE_REMOVED,
        replacement="MRTR (SEP-2322)",
        removed_in=_SPEC_VERSION,
    ),
    DeprecationEntry(
        "elicitation_notification",
        LIFECYCLE_REMOVED,
        replacement="MRTR retry pattern",
        removed_in=_SPEC_VERSION,
    ),
    DeprecationEntry(
        "tasks/list",
        LIFECYCLE_REMOVED,
        replacement="tasks/get",
        removed_in=_SPEC_VERSION,
    ),
]

# ── Deprecated features (12-month window, SEP-2577, SEP-2596) ──────────

_DEPRECATED = [
    DeprecationEntry(
        "roots",
        LIFECYCLE_DEPRECATED,
        replacement="tool params, resource URIs, config",
        deprecated_since=_SPEC_VERSION,
        migration="Pass context directly as tool parameters instead of using Roots capability.",
    ),
    DeprecationEntry(
        "sampling",
        LIFECYCLE_DEPRECATED,
        replacement="direct LLM provider APIs",
        deprecated_since=_SPEC_VERSION,
        migration="Use LLM provider APIs directly instead of MCP sampling.",
    ),
    DeprecationEntry(
        "logging",
        LIFECYCLE_DEPRECATED,
        replacement="stderr / OpenTelemetry",
        deprecated_since=_SPEC_VERSION,
        migration="Use per-request logLevel in _meta. Server-side logging via stderr/OpenTelemetry.",
    ),
    DeprecationEntry(
        "http_sse_transport",
        LIFECYCLE_DEPRECATED,
        replacement="Streamable HTTP",
        deprecated_since=_SPEC_VERSION,
        migration="Migrate to Streamable HTTP transport.",
    ),
    DeprecationEntry(
        "includeContext",
        LIFECYCLE_DEPRECATED,
        replacement="omit or use 'none'",
        deprecated_since=_SPEC_VERSION,
    ),
    DeprecationEntry(
        "dcr",
        LIFECYCLE_DEPRECATED,
        replacement="CIMD (Client ID Metadata Document)",
        deprecated_since=_SPEC_VERSION,
        migration="Use GET /auth/client-metadata/{client_id} instead of POST /auth/register.",
    ),
]

for _entry in _REMOVED + _DEPRECATED:
    deprecation_registry.register(_entry)
