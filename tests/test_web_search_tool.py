"""Minimal tests for the search_web MCP tool."""

import asyncio
from unittest.mock import AsyncMock, patch

from template_mcp_server.src.settings import settings
from template_mcp_server.src.tools.web_search_tool import search_web

_CLIENT_PATH = "template_mcp_server.src.tools.web_search_tool.AsyncTavilyClient"


class TestWebSearch:
    """Test the search_web tool."""

    def test_empty_queries_returns_error(self):
        """Empty queries list returns a validation error."""
        result = asyncio.run(search_web(queries=[]))
        assert result["status"] == "error"

    @patch.object(settings, "TAVILY_API_KEY", "")
    def test_missing_api_key_returns_error(self):
        """Missing TAVILY_API_KEY returns an error."""
        result = asyncio.run(search_web(queries=["test query"]))
        assert result["status"] == "error"

    @patch(_CLIENT_PATH)
    @patch.object(settings, "TAVILY_API_KEY", "test-key")
    def test_successful_search(self, mock_client_cls):
        """Successful search returns results with proper structure."""
        mock_client = AsyncMock()
        mock_client.search.return_value = {
            "results": [
                {
                    "title": "Result 1",
                    "url": "https://example.com/1",
                    "content": "Snippet 1",
                    "score": 0.95,
                }
            ]
        }
        mock_client_cls.return_value = mock_client

        result = asyncio.run(search_web(queries=["python tutorial"]))

        assert result["status"] == "success"
        assert result["total_results"] == 1
        assert result["results"][0]["title"] == "Result 1"
