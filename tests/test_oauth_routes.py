"""Tests for OAuth routes module — 100% coverage."""

from unittest.mock import AsyncMock, Mock, patch

import pytest
from fastapi.testclient import TestClient

from template_mcp_server.src.oauth import routes


@pytest.fixture
def mock_oauth_service():
    service = Mock()
    return service


@pytest.fixture
def app_with_routes(mock_oauth_service):
    from fastapi import FastAPI

    app = FastAPI()
    routes.register_oauth_routes(app, lambda: mock_oauth_service)
    return app


@pytest.fixture
def client(app_with_routes):
    return TestClient(app_with_routes)


class TestOAuthRoutesNotInitialized:
    """Test routes when OAuth service is not initialized."""

    def test_callback_not_initialized(self):
        from fastapi import FastAPI

        app = FastAPI()
        routes.get_oauth_service = None
        app.include_router(routes.oauth_router)
        c = TestClient(app, raise_server_exceptions=False)
        resp = c.get("/auth/callback/oidc")
        assert resp.status_code == 500

    def test_authorize_not_initialized(self):
        from fastapi import FastAPI

        app = FastAPI()
        routes.get_oauth_service = None
        app.include_router(routes.oauth_router)
        c = TestClient(app, raise_server_exceptions=False)
        resp = c.get("/auth/authorize")
        assert resp.status_code == 500

    def test_token_not_initialized(self):
        from fastapi import FastAPI

        app = FastAPI()
        routes.get_oauth_service = None
        app.include_router(routes.oauth_router)
        c = TestClient(app, raise_server_exceptions=False)
        resp = c.post("/auth/token")
        assert resp.status_code == 500

    def test_register_not_initialized(self):
        from fastapi import FastAPI

        app = FastAPI()
        routes.get_oauth_service = None
        app.include_router(routes.oauth_router)
        c = TestClient(app, raise_server_exceptions=False)
        resp = c.post("/auth/register", json={})
        assert resp.status_code == 500

    def test_client_metadata_not_initialized(self):
        from fastapi import FastAPI

        app = FastAPI()
        routes.get_oauth_service = None
        app.include_router(routes.oauth_router)
        c = TestClient(app, raise_server_exceptions=False)
        resp = c.get("/auth/client-metadata/test-id")
        assert resp.status_code == 500

    def test_introspect_not_initialized(self):
        from fastapi import FastAPI

        app = FastAPI()
        routes.get_oauth_service = None
        app.include_router(routes.oauth_router)
        c = TestClient(app, raise_server_exceptions=False)
        resp = c.post("/auth/introspect")
        assert resp.status_code == 500


class TestOAuthRoutesInitialized:
    """Test routes when OAuth service is properly initialized."""

    @patch.object(routes.controller, "handle_callback", new_callable=AsyncMock)
    def test_callback_calls_controller(self, mock_handler, client):
        from fastapi.responses import JSONResponse

        mock_handler.return_value = JSONResponse(content={"code": "abc"})
        resp = client.get("/auth/callback/oidc?code=abc")
        assert resp.status_code == 200
        mock_handler.assert_called_once()

    @patch.object(routes.controller, "handle_authorize", new_callable=AsyncMock)
    def test_authorize_calls_controller(self, mock_handler, client):
        from fastapi.responses import JSONResponse

        mock_handler.return_value = JSONResponse(content={"ok": True})
        resp = client.get("/auth/authorize?response_type=code&client_id=c1")
        assert resp.status_code == 200
        mock_handler.assert_called_once()

    @patch.object(routes.controller, "handle_token", new_callable=AsyncMock)
    def test_token_calls_controller(self, mock_handler, client):
        mock_result = Mock()
        mock_result.model_dump.return_value = {"access_token": "tok"}
        mock_handler.return_value = mock_result
        resp = client.post("/auth/token", data={"grant_type": "authorization_code"})
        assert resp.status_code == 200
        assert resp.json()["access_token"] == "tok"

    @patch.object(routes.controller, "handle_token", new_callable=AsyncMock)
    def test_token_dict_response(self, mock_handler, client):
        mock_handler.return_value = {"access_token": "tok"}
        resp = client.post("/auth/token", data={"grant_type": "authorization_code"})
        assert resp.status_code == 200

    @patch.object(routes.controller, "handle_register", new_callable=AsyncMock)
    def test_register_returns_deprecation_header(self, mock_handler, client):
        mock_result = Mock()
        mock_result.model_dump.return_value = {"client_id": "c1"}
        mock_handler.return_value = mock_result
        resp = client.post("/auth/register", json={"client_name": "test"})
        assert resp.status_code == 200
        assert resp.headers.get("deprecation") == "true"

    @patch.object(routes.controller, "handle_client_metadata", new_callable=AsyncMock)
    def test_client_metadata_calls_controller(self, mock_handler, client):
        mock_result = Mock()
        mock_result.model_dump.return_value = {"client_id": "c1", "client_name": "test"}
        mock_handler.return_value = mock_result
        resp = client.get("/auth/client-metadata/c1")
        assert resp.status_code == 200
        assert resp.json()["client_id"] == "c1"

    @patch.object(routes.controller, "handle_introspect", new_callable=AsyncMock)
    def test_introspect_calls_controller(self, mock_handler, client):
        mock_result = Mock()
        mock_result.model_dump.return_value = {"active": True}
        mock_handler.return_value = mock_result
        resp = client.post("/auth/introspect", data={"token": "tok"})
        assert resp.status_code == 200
        assert resp.json()["active"] is True

    @patch.object(routes.controller, "handle_introspect", new_callable=AsyncMock)
    def test_introspect_dict_response(self, mock_handler, client):
        mock_handler.return_value = {"active": False}
        resp = client.post("/auth/introspect", data={"token": "tok"})
        assert resp.status_code == 200


class TestRegisterOAuthRoutes:
    """Test the register_oauth_routes function."""

    def test_sets_oauth_service_provider(self):
        from fastapi import FastAPI

        app = FastAPI()
        provider = lambda: Mock()
        routes.register_oauth_routes(app, provider)
        assert routes.get_oauth_service is provider
