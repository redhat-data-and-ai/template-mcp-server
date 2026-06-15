import json
import time
from unittest.mock import AsyncMock, patch

import pytest

from template_mcp_server.src.storage.redis_service import (
    RedisStorageService,
    _get_client_index_key,
)


class TestRedisStorageServiceInit:
    """Test RedisStorageService initialization."""

    def test_init_default_values(self):
        service = RedisStorageService()
        assert service.host == "localhost"
        assert service.port == 6379
        assert service.password is None
        assert service.db == 0
        assert service.redis is None

    def test_init_custom_values(self):
        service = RedisStorageService(host="redis", port=6380, password="secret", db=1)
        assert service.host == "redis"
        assert service.port == 6380
        assert service.password == "secret"
        assert service.db == 1


class TestRedisStorageServiceConnection:
    """Test connection management."""

    @pytest.mark.asyncio
    async def test_connect_success(self):
        service = RedisStorageService()
        mock_redis = AsyncMock()

        with patch(
            "template_mcp_server.src.storage.redis_service.redis.Redis",
            return_value=mock_redis,
        ):
            await service.connect()
            mock_redis.ping.assert_called_once()
            assert service.redis == mock_redis

    @pytest.mark.asyncio
    async def test_connect_failure(self):
        service = RedisStorageService()
        mock_redis = AsyncMock()
        mock_redis.ping.side_effect = Exception("Connection refused")

        with patch(
            "template_mcp_server.src.storage.redis_service.redis.Redis",
            return_value=mock_redis,
        ):
            with pytest.raises(ConnectionError):
                await service.connect()

    @pytest.mark.asyncio
    async def test_disconnect(self):
        service = RedisStorageService()
        mock_redis = AsyncMock()
        service.redis = mock_redis

        await service.disconnect()
        mock_redis.aclose.assert_called_once()
        assert service.redis is None


class TestRedisStorageServiceMethods:
    """Test storage methods."""

    @pytest.fixture
    def service(self):
        s = RedisStorageService()
        s.redis = AsyncMock()
        return s

    @pytest.mark.asyncio
    async def test_store_client(self, service):
        client_data = {
            "id": "123",
            "name": "Test",
            "redirect_uris": ["http://localhost"],
        }
        result = await service.store_client(client_data)

        assert result is True
        # Check that it saves the client info and the index
        assert service.redis.set.call_count == 2
        idx_key = _get_client_index_key("Test", ["http://localhost"])
        service.redis.set.assert_any_call("client:123", json.dumps(client_data))
        service.redis.set.assert_any_call(idx_key, "123")

    @pytest.mark.asyncio
    async def test_get_client(self, service):
        client_data = {"id": "123", "name": "Test"}
        service.redis.get.return_value = json.dumps(client_data)

        result = await service.get_client("123")
        assert result == client_data
        service.redis.get.assert_called_once_with("client:123")

    @pytest.mark.asyncio
    async def test_store_authorization_code(self, service):
        code_data = {"expires_at": time.time() + 600, "client_id": "123"}
        result = await service.store_authorization_code("code1", code_data)

        assert result is True
        service.redis.setex.assert_called_once()
        args, _ = service.redis.setex.call_args
        assert args[0] == "auth_code:code1"
        assert args[1] > 0  # TTL
        assert args[2] == json.dumps(code_data)

    @pytest.mark.asyncio
    async def test_update_authorization_code_token(self, service):
        code_data = {"client_id": "123", "snowflake_token": None}
        service.redis.get.return_value = json.dumps(code_data)
        service.redis.ttl.return_value = 300

        snowflake = {"access_token": "token1"}
        result = await service.update_authorization_code_token("code1", snowflake)

        assert result is True
        service.redis.setex.assert_called_once()
        args, _ = service.redis.setex.call_args
        assert args[0] == "auth_code:code1"
        assert args[1] == 300
        saved_data = json.loads(args[2])
        assert saved_data["snowflake_token"] == snowflake

    @pytest.mark.asyncio
    async def test_get_client_by_name_and_redirect_uris(self, service):
        client_data = {"id": "123", "name": "Test", "redirect_uris": ["url"]}
        service.redis.get.side_effect = ["123", json.dumps(client_data)]

        result = await service.get_client_by_name_and_redirect_uris("Test", ["url"])

        assert result == client_data
        assert service.redis.get.call_count == 2
