"""OAuth service module providing core OAuth 2.0 functionality.

This module implements OAuth 2.0 authorization server functionality including:
- Client management
- Authorization code flow with PKCE
- Token generation and validation
- JWT token handling
- Client credentials flow
- Refresh token flow
"""

import base64
import hashlib
import secrets
import time
from typing import Any, Dict, List, Optional

from template_mcp_server.src.settings import settings
from template_mcp_server.src.storage.storage_service import StorageService
from template_mcp_server.utils.pylogger import get_python_logger

logger = get_python_logger(settings.PYTHON_LOG_LEVEL)

# Global storage service for backward compatibility during transition
_storage_service: Optional[StorageService] = None


def generate_random_string(length: int = 32) -> str:
    """Generate a cryptographically secure random string."""
    chars = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789-._~"
    return "".join(secrets.choice(chars) for _ in range(length))


def base64url_encode(data: bytes) -> str:
    """Base64 URL-safe encode without padding."""
    # Use standard base64.urlsafe_b64encode, but ensure correct padding removal
    encoded = base64.urlsafe_b64encode(data).decode("utf-8")
    return encoded.rstrip("=")


def verify_code_challenge(code_verifier: str, code_challenge: str) -> bool:
    """Verify PKCE code challenge using S256 method.

    Args:
        code_verifier: The original code verifier from the client
        code_challenge: The code challenge from the authorization request

    Returns:
        bool: True if verification succeeds, False otherwise
    """
    try:
        # Compute SHA256 hash of the code verifier
        hash_bytes = hashlib.sha256(code_verifier.encode("utf-8")).digest()

        # Base64url encode the hash (without padding)
        computed_challenge = base64url_encode(hash_bytes)

        # Compare with the provided code challenge
        return computed_challenge == code_challenge

    except Exception as e:
        logger.error(f"PKCE verification failed with error: {e}")
        return False


class OAuthService:
    """OAuth service that manages OAuth 2.0 operations with dependency injection."""

    def __init__(self, storage_service: StorageService):
        """Initialize OAuth service with storage dependency.

        Args:
            storage_service: The storage service instance to use for persistence
        """
        self.storage = storage_service

    async def validate_client(
        self, client_id: str, client_secret: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """Validate client credentials."""
        client = await self.storage.get_client(client_id)
        if not client:
            return None

        if client_secret and client.get("secret") and client["secret"] != client_secret:
            return None

        return client

    async def create_authorization_code(
        self,
        client_id: str,
        redirect_uri: str,
        scope: Optional[str],
        code_challenge: str,
        code_challenge_method: str,
        state: str,
    ) -> str:
        """Create an authorization code."""
        auth_code = generate_random_string(32)
        code_data = {
            "client_id": client_id,
            "redirect_uri": redirect_uri,
            "scope": scope or "read",
            "code_challenge": code_challenge,
            "code_challenge_method": code_challenge_method,
            "expires_at": time.time() + (10 * 60),  # 10 minutes
            "state": state,
        }

        await self.storage.store_authorization_code(auth_code, code_data)
        return auth_code

    async def add_token_to_code(self, code: str, token_set: Dict[str, Any]) -> None:
        """Add Snowflake token to authorization code."""
        await self.storage.update_authorization_code_token(code, token_set)

    async def validate_authorization_code(self, code: str) -> Optional[Dict[str, Any]]:
        """Validate authorization code."""
        code_data = await self.storage.get_authorization_code(code)
        if not code_data or code_data["expires_at"] < time.time():
            return None
        return code_data

    async def mark_code_as_used(self, code: str) -> None:
        """Mark authorization code as used by deleting it from storage."""
        success = await self.storage.delete_authorization_code(code)
        if success:
            logger.info(f"Authorization code deleted after use: {code[:8]}...")
        else:
            logger.warning(f"Failed to delete authorization code: {code[:8]}...")

    async def validate_refresh_token(
        self, refresh_token: str
    ) -> Optional[Dict[str, Any]]:
        """Validate refresh token."""
        refresh_data = await self.storage.get_refresh_token(refresh_token)
        if not refresh_data:
            return None

        expires_at = refresh_data.get("expires_at")
        if expires_at is not None and expires_at < time.time():
            return None

        return refresh_data

    async def register_client(
        self,
        client_name: str,
        redirect_uris: List[str],
        grant_types: Optional[List[str]] = None,
        response_types: Optional[List[str]] = None,
        scope: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Register a new OAuth client.

        If a client with the same name and redirect URIs already exists,
        returns the existing client credentials instead of creating a new one.
        """
        existing_client = await self.storage.get_client_by_name_and_redirect_uris(
            client_name, redirect_uris
        )

        if existing_client:
            logger.info(
                f"Returning existing client for name '{client_name}': {existing_client['id']}"
            )
            return {
                "client_id": existing_client["id"],
                "client_secret": existing_client["secret"],
                "client_name": existing_client["name"],
                "redirect_uris": existing_client["redirect_uris"],
                "grant_types": existing_client["grant_types"],
                "response_types": existing_client["response_types"],
                "scope": existing_client["scope"],
                "client_id_issued_at": int(existing_client["created_at"]),
            }

        client_id = generate_random_string(16)
        client_secret = generate_random_string(32)

        client_data = {
            "id": client_id,
            "secret": client_secret,
            "name": client_name,
            "redirect_uris": redirect_uris,
            "grant_types": grant_types or ["authorization_code", "refresh_token"],
            "response_types": response_types or ["code"],
            "scope": scope or "read write",
            "created_at": time.time(),
        }

        success = await self.storage.store_client(client_data)

        if not success:
            logger.error(f"Failed to store client {client_id} in storage")
            raise RuntimeError("Failed to persist client registration")

        logger.info(f"New client registered: {client_id} for '{client_name}'")

        return {
            "client_id": client_id,
            "client_secret": client_secret,
            "client_name": client_name,
            "redirect_uris": redirect_uris,
            "grant_types": client_data["grant_types"],
            "response_types": client_data["response_types"],
            "scope": client_data["scope"],
            "client_id_issued_at": int(time.time()),
        }

    async def store_access_token(self, token: str, token_data: Dict[str, Any]) -> bool:
        """Store an access token."""
        return await self.storage.store_access_token(token, token_data)

    async def retrieve_access_token(self, token: str) -> Optional[Dict[str, Any]]:
        """Retrieve an access token."""
        return await self.storage.get_access_token(token)

    async def store_refresh_token(self, token: str, token_data: Dict[str, Any]) -> bool:
        """Store a refresh token."""
        return await self.storage.store_refresh_token(token, token_data)

    async def retrieve_refresh_token(self, token: str) -> Optional[Dict[str, Any]]:
        """Retrieve a refresh token."""
        return await self.storage.get_refresh_token(token)

    async def revoke_access_token(self, token: str) -> bool:
        """Revoke (delete) an access token."""
        return await self.storage.delete_access_token(token)

    async def revoke_refresh_token(self, token: str) -> bool:
        """Revoke (delete) a refresh token."""
        return await self.storage.delete_refresh_token(token)

    async def get_storage_status(self) -> Dict[str, Any]:
        """Get the current status of the storage service."""
        return await self.storage.get_status()


# Backward compatibility functions - will be deprecated in future versions
async def get_storage_service() -> StorageService:
    """Get the initialized storage service.

    Note: Storage service must be initialized via initialize_storage() during startup.

    Returns:
        StorageService: The initialized storage service

    Raises:
        RuntimeError: If storage service hasn't been initialized
    """
    global _storage_service
    if _storage_service is None:
        raise RuntimeError(
            "Storage service not initialized. Ensure initialize_storage() is called during startup."
        )
    return _storage_service


async def validate_client(
    client_id: str, client_secret: Optional[str] = None
) -> Optional[Dict[str, Any]]:
    """Validate client credentials."""
    storage = await get_storage_service()
    service = OAuthService(storage)
    return await service.validate_client(client_id, client_secret)


async def create_authorization_code(
    client_id: str,
    redirect_uri: str,
    scope: Optional[str],
    code_challenge: str,
    code_challenge_method: str,
    state: str,
) -> str:
    """Create an authorization code."""
    storage = await get_storage_service()
    service = OAuthService(storage)
    return await service.create_authorization_code(
        client_id,
        redirect_uri,
        scope,
        code_challenge,
        code_challenge_method,
        state,
    )


async def add_token_to_code(code: str, token_set: Dict[str, Any]) -> None:
    """Add Snowflake token to authorization code."""
    storage = await get_storage_service()
    service = OAuthService(storage)
    await service.add_token_to_code(code, token_set)


async def validate_authorization_code(code: str) -> Optional[Dict[str, Any]]:
    """Validate authorization code."""
    storage = await get_storage_service()
    service = OAuthService(storage)
    return await service.validate_authorization_code(code)


async def mark_code_as_used(code: str) -> None:
    """Mark authorization code as used by deleting it from storage."""
    storage = await get_storage_service()
    service = OAuthService(storage)
    await service.mark_code_as_used(code)


async def validate_refresh_token(refresh_token: str) -> Optional[Dict[str, Any]]:
    """Validate refresh token."""
    storage = await get_storage_service()
    service = OAuthService(storage)
    return await service.validate_refresh_token(refresh_token)


async def register_client(
    client_name: str,
    redirect_uris: List[str],
    grant_types: Optional[List[str]] = None,
    response_types: Optional[List[str]] = None,
    scope: Optional[str] = None,
) -> Dict[str, Any]:
    """Register a new OAuth client."""
    storage = await get_storage_service()
    service = OAuthService(storage)
    return await service.register_client(
        client_name, redirect_uris, grant_types, response_types, scope
    )


async def store_access_token(token: str, token_data: Dict[str, Any]) -> bool:
    """Store an access token."""
    storage = await get_storage_service()
    service = OAuthService(storage)
    return await service.store_access_token(token, token_data)


async def retrieve_access_token(token: str) -> Optional[Dict[str, Any]]:
    """Retrieve an access token."""
    storage = await get_storage_service()
    service = OAuthService(storage)
    return await service.retrieve_access_token(token)


async def store_refresh_token(token: str, token_data: Dict[str, Any]) -> bool:
    """Store a refresh token."""
    storage = await get_storage_service()
    service = OAuthService(storage)
    return await service.store_refresh_token(token, token_data)


async def retrieve_refresh_token(token: str) -> Optional[Dict[str, Any]]:
    """Retrieve a refresh token."""
    storage = await get_storage_service()
    service = OAuthService(storage)
    return await service.retrieve_refresh_token(token)


async def revoke_access_token(token: str) -> bool:
    """Revoke (delete) an access token."""
    storage = await get_storage_service()
    service = OAuthService(storage)
    return await service.revoke_access_token(token)


async def revoke_refresh_token(token: str) -> bool:
    """Revoke (delete) a refresh token."""
    storage = await get_storage_service()
    service = OAuthService(storage)
    return await service.revoke_refresh_token(token)


async def get_storage_status() -> Dict[str, Any]:
    """Get the current status of the storage service."""
    storage = await get_storage_service()
    service = OAuthService(storage)
    return await service.get_storage_status()


async def initialize_storage() -> StorageService:
    """Initialize the storage service. Call this during application startup.

    Returns:
        StorageService: The initialized storage service

    Raises:
        ValueError: If PostgreSQL configuration is missing
        ConnectionError: If PostgreSQL connection fails
    """
    global _storage_service

    if _storage_service is not None:
        logger.warning("Storage service already initialized")
        return _storage_service

    logger.info("Initializing PostgreSQL storage service")

    # Validate required configuration
    if not all(
        [
            settings.POSTGRES_HOST,
            settings.POSTGRES_PORT,
            settings.POSTGRES_DB,
            settings.POSTGRES_USER,
        ]
    ):
        missing = [
            name
            for name, value in [
                ("POSTGRES_HOST", settings.POSTGRES_HOST),
                ("POSTGRES_PORT", settings.POSTGRES_PORT),
                ("POSTGRES_DB", settings.POSTGRES_DB),
                ("POSTGRES_USER", settings.POSTGRES_USER),
            ]
            if not value
        ]
        raise ValueError(
            f"Missing required PostgreSQL configuration: {', '.join(missing)}"
        )

    # Create and connect storage service
    # Type assertions are safe here because we validated required fields above
    _storage_service = StorageService(
        host=str(settings.POSTGRES_HOST),
        port=int(settings.POSTGRES_PORT)
        if settings.POSTGRES_PORT is not None
        else 5432,
        database=str(settings.POSTGRES_DB),
        username=str(settings.POSTGRES_USER),
        password=settings.POSTGRES_PASSWORD or "",
        pool_size=settings.POSTGRES_POOL_SIZE,
        max_connections=settings.POSTGRES_MAX_CONNECTIONS,
    )
    await _storage_service.connect()
    logger.info("PostgreSQL storage service initialized successfully")

    return _storage_service


async def cleanup_storage() -> None:
    """Cleanup storage service. Call this during application shutdown."""
    global _storage_service
    if _storage_service is not None:
        logger.info("Disconnecting from PostgreSQL...")
        await _storage_service.disconnect()
        _storage_service = None
        logger.info("Storage service cleanup complete")
