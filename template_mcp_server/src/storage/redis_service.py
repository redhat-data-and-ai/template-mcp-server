"""Redis storage service for the Template MCP Server."""

import hashlib
import json
import time
from typing import Any, Dict, List, Optional

import redis.asyncio as redis

from template_mcp_server.src.storage.base import BaseStorageService
from template_mcp_server.utils.pylogger import get_python_logger

logger = get_python_logger()


def _get_client_index_key(client_name: str, redirect_uris: List[str]) -> str:
    """Generate a stable hash key for a client name and redirect URIs combination."""
    normalized_uris = sorted(redirect_uris)
    hash_input = json.dumps(
        {"name": client_name, "uris": normalized_uris}, sort_keys=True
    )
    hash_val = hashlib.sha256(hash_input.encode("utf-8")).hexdigest()
    return f"client_index:{hash_val}"


class RedisStorageService(BaseStorageService):
    """Redis storage service for persistent data storage.

    This service provides direct Redis storage functionality.
    It automatically uses Redis built-in TTL for tokens and auth codes.
    """

    def __init__(
        self,
        host: str = "localhost",
        port: int = 6379,
        password: Optional[str] = None,
        db: int = 0,
    ):
        """Initialize the Redis storage service.

        Args:
            host: Redis host
            port: Redis port
            password: Redis password
            db: Database index
        """
        self.host = host
        self.port = port
        self.password = password
        self.db = db
        self.redis: Optional[redis.Redis] = None

    async def connect(self) -> None:
        """Establish connection to Redis."""
        try:
            self.redis = redis.Redis(
                host=self.host,
                port=self.port,
                password=self.password,
                db=self.db,
                decode_responses=True,
            )
            # Ping to verify connection
            await self.redis.ping()
            logger.info("Storage service connected to Redis")
        except Exception as e:
            logger.error(f"Failed to connect to Redis: {e}")
            raise ConnectionError(f"Redis connection failed: {e}")

    async def disconnect(self) -> None:
        """Close Redis connection."""
        if self.redis:
            await self.redis.aclose()
            self.redis = None
            logger.info("Storage service disconnected from Redis")

    async def is_healthy(self) -> bool:
        """Check if Redis is healthy."""
        if not self.redis:
            return False
        try:
            await self.redis.ping()
            return True
        except Exception as e:
            logger.warning(f"Redis health check failed: {e}")
            return False

    async def get_status(self) -> Dict[str, Any]:
        """Get storage service status."""
        try:
            is_healthy = await self.is_healthy()
            status = {
                "type": "redis",
                "healthy": is_healthy,
                "host": self.host,
                "port": self.port,
                "db": self.db,
            }
            return status
        except Exception as e:
            logger.error(f"Failed to get storage status: {e}")
            return {"type": "redis", "healthy": False, "error": str(e)}

    async def get_client_by_name_and_redirect_uris(
        self, client_name: str, redirect_uris: List[str]
    ) -> Optional[Dict[str, Any]]:
        """Find an existing client by name and redirect URIs."""
        if not self.redis:
            return None
        try:
            idx_key = _get_client_index_key(client_name, redirect_uris)
            client_id = await self.redis.get(idx_key)
            if client_id:
                cid = client_id.decode("utf-8") if isinstance(client_id, bytes) else str(client_id)
                return await self.get_client(cid)
            return None
        except Exception as e:
            logger.error(f"Failed to get client by name and redirect URIs: {e}")
            return None

    async def store_client(self, client_data: Dict[str, Any]) -> bool:
        """Store a new OAuth client."""
        if not self.redis:
            return False
        try:
            client_id = client_data["id"]
            # Store client details
            await self.redis.set(f"client:{client_id}", json.dumps(client_data))

            # Store index for lookup by name and redirect URIs
            idx_key = _get_client_index_key(
                client_data["name"], client_data["redirect_uris"]
            )
            await self.redis.set(idx_key, client_id)

            logger.info(f"Storing client: {client_id}")
            return True
        except Exception as e:
            logger.error(f"Failed to store client: {e}")
            return False

    async def get_client(self, client_id: str) -> Optional[Dict[str, Any]]:
        """Get a client by ID."""
        if not self.redis:
            return None
        try:
            val = await self.redis.get(f"client:{client_id}")
            if val:
                return json.loads(val)
            return None
        except Exception as e:
            logger.error(f"Failed to get client: {e}")
            return None

    async def store_authorization_code(
        self, code: str, code_data: Dict[str, Any]
    ) -> bool:
        """Store an authorization code."""
        if not self.redis:
            return False
        try:
            ttl = max(1, int(code_data["expires_at"] - time.time()))
            await self.redis.setex(f"auth_code:{code}", ttl, json.dumps(code_data))
            return True
        except Exception as e:
            logger.error(f"Failed to store authorization code: {e}")
            return False

    async def get_authorization_code(self, code: str) -> Optional[Dict[str, Any]]:
        """Get authorization code data."""
        if not self.redis:
            return None
        try:
            val = await self.redis.get(f"auth_code:{code}")
            if val:
                return json.loads(val)
            return None
        except Exception as e:
            logger.error(f"Failed to get authorization code: {e}")
            return None

    async def update_authorization_code_token(
        self, code: str, snowflake_token: Dict[str, Any]
    ) -> bool:
        """Update authorization code with Snowflake token."""
        if not self.redis:
            return False
        try:
            key = f"auth_code:{code}"
            data_str = await self.redis.get(key)
            if not data_str:
                return False
            data = json.loads(data_str)
            data["snowflake_token"] = snowflake_token
            # Get remaining TTL to preserve it
            ttl = await self.redis.ttl(key)
            if ttl > 0:
                await self.redis.setex(key, ttl, json.dumps(data))
            else:
                await self.redis.set(key, json.dumps(data))
            return True
        except Exception as e:
            logger.error(f"Failed to update authorization code: {e}")
            return False

    async def delete_authorization_code(self, code: str) -> bool:
        """Delete an authorization code."""
        if not self.redis:
            return False
        try:
            result = await self.redis.delete(f"auth_code:{code}")
            return result > 0
        except Exception as e:
            logger.error(f"Failed to delete authorization code: {e}")
            return False

    async def store_access_token(self, token: str, token_data: Dict[str, Any]) -> bool:
        """Store an access token."""
        if not self.redis:
            return False
        try:
            ttl = max(1, int(token_data["expires_at"] - time.time()))
            await self.redis.setex(f"access_token:{token}", ttl, json.dumps(token_data))
            return True
        except Exception as e:
            logger.error(f"Failed to store access token: {e}")
            return False

    async def get_access_token(self, token: str) -> Optional[Dict[str, Any]]:
        """Get access token data."""
        if not self.redis:
            return None
        try:
            val = await self.redis.get(f"access_token:{token}")
            if val:
                return json.loads(val)
            return None
        except Exception as e:
            logger.error(f"Failed to get access token: {e}")
            return None

    async def delete_access_token(self, token: str) -> bool:
        """Delete an access token."""
        if not self.redis:
            return False
        try:
            result = await self.redis.delete(f"access_token:{token}")
            return result > 0
        except Exception as e:
            logger.error(f"Failed to delete access token: {e}")
            return False

    async def store_refresh_token(self, token: str, token_data: Dict[str, Any]) -> bool:
        """Store a refresh token."""
        if not self.redis:
            return False
        try:
            ttl = max(1, int(token_data["expires_at"] - time.time()))
            await self.redis.setex(
                f"refresh_token:{token}", ttl, json.dumps(token_data)
            )
            return True
        except Exception as e:
            logger.error(f"Failed to store refresh token: {e}")
            return False

    async def get_refresh_token(self, token: str) -> Optional[Dict[str, Any]]:
        """Get refresh token data."""
        if not self.redis:
            return None
        try:
            val = await self.redis.get(f"refresh_token:{token}")
            if val:
                return json.loads(val)
            return None
        except Exception as e:
            logger.error(f"Failed to get refresh token: {e}")
            return None

    async def delete_refresh_token(self, token: str) -> bool:
        """Delete a refresh token."""
        if not self.redis:
            return False
        try:
            result = await self.redis.delete(f"refresh_token:{token}")
            return result > 0
        except Exception as e:
            logger.error(f"Failed to delete refresh token: {e}")
            return False
