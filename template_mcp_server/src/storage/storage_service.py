"""PostgreSQL storage service for the Template MCP Server."""

import json
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

import asyncpg

from template_mcp_server.utils.pylogger import get_python_logger

logger = get_python_logger()


class StorageService:
    """PostgreSQL storage service for persistent data storage.

    This service provides direct PostgreSQL storage functionality without
    abstraction layers. It will fail if PostgreSQL cannot be connected to.
    """

    def __init__(
        self,
        host: str = "localhost",
        port: int = 5432,
        database: str = "postgres",
        username: str = "postgres",
        password: str = "",
        pool_size: int = 10,
        max_connections: int = 20,
    ):
        """Initialize the PostgreSQL storage service.

        Args:
            host: PostgreSQL host
            port: PostgreSQL port
            database: Database name
            username: Database username
            password: Database password
            pool_size: Minimum pool size
            max_connections: Maximum pool size
        """
        self.host = host
        self.port = port
        self.database = database
        self.username = username
        self.password = password
        self.pool_size = pool_size
        self.max_connections = max_connections
        self.pool: Optional[asyncpg.Pool] = None

    async def connect(self) -> None:
        """Establish connection pool to PostgreSQL."""
        try:
            dsn = f"postgresql://{self.username}:{self.password}@{self.host}:{self.port}/{self.database}"

            self.pool = await asyncpg.create_pool(
                dsn,
                min_size=self.pool_size,
                max_size=self.max_connections,
                command_timeout=30,
            )

            # Create the storage table if it doesn't exist
            await self._create_table()
            logger.info("Storage service connected to PostgreSQL")

        except Exception as e:
            logger.error(f"Failed to connect to PostgreSQL: {e}")
            raise ConnectionError(f"PostgreSQL connection failed: {e}")

    async def disconnect(self) -> None:
        """Close PostgreSQL connection pool."""
        if self.pool:
            await self.pool.close()
            self.pool = None
            logger.info("Storage service disconnected from PostgreSQL")

    async def is_healthy(self) -> bool:
        """Check if PostgreSQL is healthy."""
        try:
            if not self.pool:
                return False

            async with self.pool.acquire() as conn:
                await conn.execute("SELECT 1")
            return True

        except Exception as e:
            logger.warning(f"PostgreSQL health check failed: {e}")
            return False

    async def _create_table(self) -> None:
        """Create OAuth-specific tables."""
        if not self.pool:
            raise RuntimeError("Not connected to PostgreSQL")

        async with self.pool.acquire() as conn:
            # OAuth Clients table
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS oauth_clients (
                    client_id VARCHAR(255) PRIMARY KEY,
                    client_secret VARCHAR(255) NOT NULL,
                    client_name VARCHAR(255) NOT NULL,
                    redirect_uris JSONB NOT NULL,
                    grant_types JSONB NOT NULL,
                    response_types JSONB NOT NULL,
                    scope VARCHAR(255) NOT NULL,
                    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
                    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),

                    -- Unique constraint for client name + redirect URIs combination
                    CONSTRAINT unique_client_name_redirect UNIQUE (client_name, redirect_uris)
                )
            """)

            # Authorization Codes table
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS oauth_authorization_codes (
                    code VARCHAR(255) PRIMARY KEY,
                    client_id VARCHAR(255) NOT NULL,
                    redirect_uri VARCHAR(500) NOT NULL,
                    scope VARCHAR(255),
                    code_challenge VARCHAR(255) NOT NULL,
                    code_challenge_method VARCHAR(10) NOT NULL,
                    snowflake_token JSONB,
                    expires_at TIMESTAMP WITH TIME ZONE NOT NULL,
                    state VARCHAR(255),
                    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),

                    FOREIGN KEY (client_id) REFERENCES oauth_clients(client_id) ON DELETE CASCADE
                )
            """)

            # Access Tokens table
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS oauth_access_tokens (
                    token VARCHAR(255) PRIMARY KEY,
                    client_id VARCHAR(255) NOT NULL,
                    scope VARCHAR(255),
                    token_type VARCHAR(50) DEFAULT 'Bearer',
                    expires_at TIMESTAMP WITH TIME ZONE NOT NULL,
                    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),

                    FOREIGN KEY (client_id) REFERENCES oauth_clients(client_id) ON DELETE CASCADE
                )
            """)

            # Refresh Tokens table
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS oauth_refresh_tokens (
                    token VARCHAR(255) PRIMARY KEY,
                    client_id VARCHAR(255) NOT NULL,
                    access_token VARCHAR(255),
                    scope VARCHAR(255),
                    expires_at TIMESTAMP WITH TIME ZONE NOT NULL,
                    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),

                    FOREIGN KEY (client_id) REFERENCES oauth_clients(client_id) ON DELETE CASCADE,
                    FOREIGN KEY (access_token) REFERENCES oauth_access_tokens(token) ON DELETE SET NULL
                )
            """)

            # Create useful indexes
            await conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_auth_codes_expires ON oauth_authorization_codes (expires_at)"
            )
            await conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_access_tokens_expires ON oauth_access_tokens (expires_at)"
            )
            await conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_refresh_tokens_expires ON oauth_refresh_tokens (expires_at)"
            )
            await conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_client_name ON oauth_clients (client_name)"
            )

            logger.info("OAuth database tables created successfully")

    async def get_status(self) -> Dict[str, Any]:
        """Get storage service status."""
        try:
            is_healthy = await self.is_healthy()

            status = {
                "type": "postgresql",
                "healthy": is_healthy,
                "host": self.host,
                "port": self.port,
                "database": self.database,
            }

            if is_healthy and self.pool:
                status["pool_size"] = self.pool.get_size()
                status["pool_max_size"] = self.max_connections

            return status

        except Exception as e:
            logger.error(f"Failed to get storage status: {e}")
            return {"type": "postgresql", "healthy": False, "error": str(e)}

    async def get_client_by_name_and_redirect_uris(
        self, client_name: str, redirect_uris: List[str]
    ) -> Optional[Dict[str, Any]]:
        """Find an existing client by name and redirect URIs."""
        try:
            if not self.pool:
                return None

            async with self.pool.acquire() as conn:
                result = await conn.fetchrow(
                    """
                    SELECT client_id, client_secret, client_name, redirect_uris,
                           grant_types, response_types, scope, created_at
                    FROM oauth_clients
                    WHERE client_name = $1 AND redirect_uris = $2
                """,
                    client_name,
                    json.dumps(redirect_uris),
                )

                if result:
                    return {
                        "id": result["client_id"],
                        "secret": result["client_secret"],
                        "name": result["client_name"],
                        "redirect_uris": json.loads(result["redirect_uris"]),
                        "grant_types": json.loads(result["grant_types"]),
                        "response_types": json.loads(result["response_types"]),
                        "scope": result["scope"],
                        "created_at": result["created_at"].timestamp(),
                    }
                return None

        except Exception as e:
            logger.error(f"Failed to get client by name and redirect URIs: {e}")
            return None

    async def store_client(self, client_data: Dict[str, Any]) -> bool:
        """Store a new OAuth client."""
        try:
            if not self.pool:
                return False

            async with self.pool.acquire() as conn:
                await conn.execute(
                    """
                    INSERT INTO oauth_clients
                    (client_id, client_secret, client_name, redirect_uris, grant_types, response_types, scope)
                    VALUES ($1, $2, $3, $4, $5, $6, $7)
                """,
                    client_data["id"],
                    client_data["secret"],
                    client_data["name"],
                    json.dumps(client_data["redirect_uris"]),
                    json.dumps(client_data["grant_types"]),
                    json.dumps(client_data["response_types"]),
                    client_data["scope"],
                )

                logger.info(f"Storing client: {client_data['id']}")
                return True

        except Exception as e:
            logger.error(f"Failed to store client: {e}")
            return False

    async def get_client(self, client_id: str) -> Optional[Dict[str, Any]]:
        """Get a client by ID."""
        try:
            if not self.pool:
                return None

            async with self.pool.acquire() as conn:
                result = await conn.fetchrow(
                    """
                    SELECT client_id, client_secret, client_name, redirect_uris,
                           grant_types, response_types, scope, created_at
                    FROM oauth_clients
                    WHERE client_id = $1
                """,
                    client_id,
                )

                if result:
                    return {
                        "id": result["client_id"],
                        "secret": result["client_secret"],
                        "name": result["client_name"],
                        "redirect_uris": json.loads(result["redirect_uris"]),
                        "grant_types": json.loads(result["grant_types"]),
                        "response_types": json.loads(result["response_types"]),
                        "scope": result["scope"],
                        "created_at": result["created_at"].timestamp(),
                    }
                return None

        except Exception as e:
            logger.error(f"Failed to get client: {e}")
            return None

    async def store_authorization_code(
        self, code: str, code_data: Dict[str, Any]
    ) -> bool:
        """Store an authorization code."""
        try:
            if not self.pool:
                return False

            async with self.pool.acquire() as conn:
                await conn.execute(
                    """
                    INSERT INTO oauth_authorization_codes
                    (code, client_id, redirect_uri, scope, code_challenge, code_challenge_method, expires_at, state)
                    VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
                """,
                    code,
                    code_data["client_id"],
                    code_data["redirect_uri"],
                    code_data.get("scope"),
                    code_data["code_challenge"],
                    code_data["code_challenge_method"],
                    datetime.fromtimestamp(code_data["expires_at"]).replace(
                        tzinfo=timezone.utc
                    ),
                    code_data["state"],
                )
                return True

        except Exception as e:
            logger.error(f"Failed to store authorization code: {e}")
            return False

    async def get_authorization_code(self, code: str) -> Optional[Dict[str, Any]]:
        """Get authorization code data."""
        try:
            if not self.pool:
                return None

            async with self.pool.acquire() as conn:
                result = await conn.fetchrow(
                    """
                    SELECT code, client_id, redirect_uri, scope, code_challenge,
                           code_challenge_method, snowflake_token, expires_at, state
                    FROM oauth_authorization_codes
                    WHERE code = $1
                """,
                    code,
                )

                if result:
                    return {
                        "client_id": result["client_id"],
                        "redirect_uri": result["redirect_uri"],
                        "scope": result["scope"],
                        "code_challenge": result["code_challenge"],
                        "code_challenge_method": result["code_challenge_method"],
                        "snowflake_token": json.loads(result["snowflake_token"])
                        if result["snowflake_token"]
                        else None,
                        "expires_at": result["expires_at"].timestamp(),
                        "state": result["state"],
                    }
                return None

        except Exception as e:
            logger.error(f"Failed to get authorization code: {e}")
            return None

    async def update_authorization_code_token(
        self, code: str, snowflake_token: Dict[str, Any]
    ) -> bool:
        """Update authorization code with Snowflake token."""
        try:
            if not self.pool:
                return False

            async with self.pool.acquire() as conn:
                await conn.execute(
                    """
                    UPDATE oauth_authorization_codes
                    SET snowflake_token = $2
                    WHERE code = $1
                """,
                    code,
                    json.dumps(snowflake_token),
                )
                return True

        except Exception as e:
            logger.error(f"Failed to update authorization code: {e}")
            return False

    async def delete_authorization_code(self, code: str) -> bool:
        """Delete an authorization code."""
        try:
            if not self.pool:
                return False

            async with self.pool.acquire() as conn:
                result = await conn.execute(
                    """
                    DELETE FROM oauth_authorization_codes WHERE code = $1
                """,
                    code,
                )
                return result != "DELETE 0"

        except Exception as e:
            logger.error(f"Failed to delete authorization code: {e}")
            return False

    async def store_access_token(self, token: str, token_data: Dict[str, Any]) -> bool:
        """Store an access token."""
        try:
            if not self.pool:
                return False

            async with self.pool.acquire() as conn:
                await conn.execute(
                    """
                    INSERT INTO oauth_access_tokens
                    (token, client_id, scope, expires_at)
                    VALUES ($1, $2, $3, $4)
                """,
                    token,
                    token_data["client_id"],
                    token_data.get("scope"),
                    datetime.fromtimestamp(token_data["expires_at"]).replace(
                        tzinfo=timezone.utc
                    ),
                )
                return True

        except Exception as e:
            logger.error(f"Failed to store access token: {e}")
            return False

    async def get_access_token(self, token: str) -> Optional[Dict[str, Any]]:
        """Get access token data."""
        try:
            if not self.pool:
                return None

            async with self.pool.acquire() as conn:
                result = await conn.fetchrow(
                    """
                    SELECT token, client_id, scope, token_type, expires_at
                    FROM oauth_access_tokens
                    WHERE token = $1
                """,
                    token,
                )

                if result:
                    return {
                        "client_id": result["client_id"],
                        "scope": result["scope"],
                        "token_type": result["token_type"],
                        "expires_at": result["expires_at"].timestamp(),
                    }
                return None

        except Exception as e:
            logger.error(f"Failed to get access token: {e}")
            return None

    async def delete_access_token(self, token: str) -> bool:
        """Delete an access token."""
        try:
            if not self.pool:
                return False

            async with self.pool.acquire() as conn:
                result = await conn.execute(
                    """
                    DELETE FROM oauth_access_tokens WHERE token = $1
                """,
                    token,
                )
                return result != "DELETE 0"

        except Exception as e:
            logger.error(f"Failed to delete access token: {e}")
            return False

    async def store_refresh_token(self, token: str, token_data: Dict[str, Any]) -> bool:
        """Store a refresh token."""
        try:
            if not self.pool:
                return False

            async with self.pool.acquire() as conn:
                await conn.execute(
                    """
                    INSERT INTO oauth_refresh_tokens
                    (token, client_id, access_token, scope, expires_at)
                    VALUES ($1, $2, $3, $4, $5)
                """,
                    token,
                    token_data["client_id"],
                    token_data.get("access_token"),
                    token_data.get("scope"),
                    datetime.fromtimestamp(token_data["expires_at"]).replace(
                        tzinfo=timezone.utc
                    ),
                )
                return True

        except Exception as e:
            logger.error(f"Failed to store refresh token: {e}")
            return False

    async def get_refresh_token(self, token: str) -> Optional[Dict[str, Any]]:
        """Get refresh token data."""
        try:
            if not self.pool:
                return None

            async with self.pool.acquire() as conn:
                result = await conn.fetchrow(
                    """
                    SELECT token, client_id, access_token, scope, expires_at
                    FROM oauth_refresh_tokens
                    WHERE token = $1
                """,
                    token,
                )

                if result:
                    return {
                        "client_id": result["client_id"],
                        "access_token": result["access_token"],
                        "scope": result["scope"],
                        "expires_at": result["expires_at"].timestamp(),
                    }
                return None

        except Exception as e:
            logger.error(f"Failed to get refresh token: {e}")
            return None

    async def delete_refresh_token(self, token: str) -> bool:
        """Delete a refresh token."""
        try:
            if not self.pool:
                return False

            async with self.pool.acquire() as conn:
                result = await conn.execute(
                    """
                    DELETE FROM oauth_refresh_tokens WHERE token = $1
                """,
                    token,
                )
                return result != "DELETE 0"

        except Exception as e:
            logger.error(f"Failed to delete refresh token: {e}")
            return False
