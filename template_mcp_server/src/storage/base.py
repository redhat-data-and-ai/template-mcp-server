"""Abstract base class defining the storage interface for the Template MCP Server."""

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional


class BaseStorageService(ABC):
    """Abstract base class for storage services."""

    @abstractmethod
    async def connect(self) -> None:
        """Establish connection to storage backend."""
        pass

    @abstractmethod
    async def disconnect(self) -> None:
        """Close connection to storage backend."""
        pass

    @abstractmethod
    async def is_healthy(self) -> bool:
        """Check if storage backend is healthy."""
        pass

    @abstractmethod
    async def get_status(self) -> Dict[str, Any]:
        """Get storage service status."""
        pass

    @abstractmethod
    async def get_client_by_name_and_redirect_uris(
        self, client_name: str, redirect_uris: List[str]
    ) -> Optional[Dict[str, Any]]:
        """Find an existing client by name and redirect URIs."""
        pass

    @abstractmethod
    async def store_client(self, client_data: Dict[str, Any]) -> bool:
        """Store a new OAuth client."""
        pass

    @abstractmethod
    async def get_client(self, client_id: str) -> Optional[Dict[str, Any]]:
        """Get a client by ID."""
        pass

    @abstractmethod
    async def store_authorization_code(
        self, code: str, code_data: Dict[str, Any]
    ) -> bool:
        """Store an authorization code."""
        pass

    @abstractmethod
    async def get_authorization_code(self, code: str) -> Optional[Dict[str, Any]]:
        """Get authorization code data."""
        pass

    @abstractmethod
    async def update_authorization_code_token(
        self, code: str, snowflake_token: Dict[str, Any]
    ) -> bool:
        """Update authorization code with Snowflake token."""
        pass

    @abstractmethod
    async def delete_authorization_code(self, code: str) -> bool:
        """Delete an authorization code."""
        pass

    @abstractmethod
    async def store_access_token(self, token: str, token_data: Dict[str, Any]) -> bool:
        """Store an access token."""
        pass

    @abstractmethod
    async def get_access_token(self, token: str) -> Optional[Dict[str, Any]]:
        """Get access token data."""
        pass

    @abstractmethod
    async def delete_access_token(self, token: str) -> bool:
        """Delete an access token."""
        pass

    @abstractmethod
    async def store_refresh_token(self, token: str, token_data: Dict[str, Any]) -> bool:
        """Store a refresh token."""
        pass

    @abstractmethod
    async def get_refresh_token(self, token: str) -> Optional[Dict[str, Any]]:
        """Get refresh token data."""
        pass

    @abstractmethod
    async def delete_refresh_token(self, token: str) -> bool:
        """Delete a refresh token."""
        pass
