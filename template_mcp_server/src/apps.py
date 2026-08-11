"""MCP Apps extension (SEP-1865).

Provides an app registry for declaring UI-capable applications that MCP clients
can discover and render. Apps are advertised via the extensions framework
(SEP-2133) under the ``io.modelcontextprotocol/ui`` identifier.
"""

from typing import Any, Dict, List, Optional


class AppEntry:
    """A single registered MCP App."""

    def __init__(
        self,
        app_id: str,
        name: str,
        *,
        description: Optional[str] = None,
        ui_type: str = "iframe",
        url: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Initialize an app entry."""
        self.app_id = app_id
        self.name = name
        self.description = description
        self.ui_type = ui_type
        self.url = url
        self.metadata = metadata or {}

    def to_dict(self) -> Dict[str, Any]:
        """Serialize app entry to JSON-compatible dict."""
        result: Dict[str, Any] = {
            "appId": self.app_id,
            "name": self.name,
            "uiType": self.ui_type,
        }
        if self.description:
            result["description"] = self.description
        if self.url:
            result["url"] = self.url
        if self.metadata:
            result["metadata"] = self.metadata
        return result


class AppRegistry:
    """Registry for MCP Apps (SEP-1865)."""

    def __init__(self) -> None:
        """Initialize an empty app registry."""
        self._apps: Dict[str, AppEntry] = {}

    def register(self, entry: AppEntry) -> None:
        """Register an app entry."""
        self._apps[entry.app_id] = entry

    def unregister(self, app_id: str) -> bool:
        """Remove an app; return True if it existed."""
        return self._apps.pop(app_id, None) is not None

    def get(self, app_id: str) -> Optional[AppEntry]:
        """Look up an app by ID."""
        return self._apps.get(app_id)

    def list_apps(self) -> List[Dict[str, Any]]:
        """Return all apps as serialized dicts."""
        return [app.to_dict() for app in self._apps.values()]

    @property
    def count(self) -> int:
        """Return number of registered apps."""
        return len(self._apps)

    def get_extension_config(self) -> Dict[str, Any]:
        """Build the config dict for the extensions registry."""
        return {
            "appCount": self.count,
            "apps": self.list_apps(),
        }


app_registry = AppRegistry()
