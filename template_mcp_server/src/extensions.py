"""MCP Extensions framework (SEP-2133).

Provides an extension registry for declaring and discovering MCP protocol
extensions using reverse-DNS identifiers. Extensions are advertised in
the server/discover capabilities response.
"""

from typing import Any, Dict, List, Optional

EXTENSION_APPS = "io.modelcontextprotocol/ui"
EXTENSION_TASKS = "io.modelcontextprotocol/tasks"


class ExtensionRegistry:
    """Registry for MCP protocol extensions (SEP-2133)."""

    def __init__(self) -> None:
        """Initialize an empty extension registry."""
        self._extensions: Dict[str, Dict[str, Any]] = {}

    def register(
        self, extension_id: str, config: Optional[Dict[str, Any]] = None
    ) -> None:
        """Register an extension by reverse-DNS identifier."""
        self._extensions[extension_id] = config or {}

    def unregister(self, extension_id: str) -> None:
        """Remove an extension from the registry."""
        self._extensions.pop(extension_id, None)

    def is_registered(self, extension_id: str) -> bool:
        """Check whether an extension is registered."""
        return extension_id in self._extensions

    def get_capabilities(self) -> Dict[str, Dict[str, Any]]:
        """Return extensions dict for server/discover capabilities."""
        return dict(self._extensions)

    def get_extension(self, extension_id: str) -> Optional[Dict[str, Any]]:
        """Return config for a single extension, or None."""
        return self._extensions.get(extension_id)

    @property
    def registered_ids(self) -> List[str]:
        """Return list of registered extension identifiers."""
        return list(self._extensions.keys())


extension_registry = ExtensionRegistry()
