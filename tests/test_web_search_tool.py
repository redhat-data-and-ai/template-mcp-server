"""Tests for the search_web MCP tool — 100% coverage."""

import asyncio
import importlib
import sys
from unittest.mock import AsyncMock, patch

from template_mcp_server.src.settings import settings
from template_mcp_server.src.tools.web_search_tool import (
    _search_with_retry,
    _truncate_snippet,
    search_web,
)


class TestTavilyImportGuard:
    """Cover lines 15-16: tavily ImportError fallback."""

    def test_async_tavily_client_none_when_not_installed(self):
        saved = sys.modules.pop("tavily", None)
        saved_tool = sys.modules.pop(
            "template_mcp_server.src.tools.web_search_tool", None
        )
        try:
            with patch.dict("sys.modules", {"tavily": None}):
                mod = importlib.import_module(
                    "template_mcp_server.src.tools.web_search_tool"
                )
                assert mod.AsyncTavilyClient is None
        finally:
            if saved is not None:
                sys.modules["tavily"] = saved
            if saved_tool is not None:
                sys.modules["template_mcp_server.src.tools.web_search_tool"] = (
                    saved_tool
                )


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

    @patch(_CLIENT_PATH, None)
    @patch.object(settings, "TAVILY_API_KEY", "test-key")
    def test_tavily_not_installed(self):
        result = asyncio.run(search_web(queries=["hello"]))
        assert result["status"] == "error"
        assert "not installed" in result["error"]

    @patch(_CLIENT_PATH)
    @patch.object(settings, "TAVILY_API_KEY", "test-key")
    def test_search_deduplicates_urls(self, mock_client_cls):
        mock_client = AsyncMock()
        mock_client.search.return_value = {
            "results": [
                {
                    "title": "R1",
                    "url": "https://example.com/same",
                    "content": "A",
                    "score": 1,
                },
                {
                    "title": "R2",
                    "url": "https://example.com/same",
                    "content": "B",
                    "score": 0.5,
                },
            ]
        }
        mock_client_cls.return_value = mock_client
        result = asyncio.run(search_web(queries=["q1"]))
        assert result["total_results"] == 1

    @patch(_CLIENT_PATH)
    @patch.object(settings, "TAVILY_API_KEY", "test-key")
    def test_failed_query_counted_in_results(self, mock_client_cls):
        mock_client = AsyncMock()
        mock_client.search.side_effect = Exception("network error")
        mock_client_cls.return_value = mock_client
        result = asyncio.run(search_web(queries=["q1"]))
        assert result["status"] == "success"
        assert result["total_results"] == 0


class TestSearchWithRetry:
    """Test _search_with_retry retry and timeout logic."""

    def test_succeeds_on_first_attempt(self):
        client = AsyncMock()
        client.search.return_value = {"results": []}
        result = asyncio.run(_search_with_retry(client, "q", 5, 10.0))
        assert result == {"results": []}
        assert client.search.call_count == 1

    @patch("template_mcp_server.src.tools.web_search_tool.RETRY_DELAYS_SECONDS", (0, 0))
    def test_retries_on_timeout(self):
        client = AsyncMock()
        client.search.side_effect = [
            asyncio.TimeoutError(),
            asyncio.TimeoutError(),
            {"results": [{"title": "ok"}]},
        ]
        result = asyncio.run(_search_with_retry(client, "q", 5, 0.001))
        assert result["results"][0]["title"] == "ok"
        assert client.search.call_count == 3

    @patch("template_mcp_server.src.tools.web_search_tool.RETRY_DELAYS_SECONDS", (0, 0))
    def test_retries_on_exception(self):
        client = AsyncMock()
        client.search.side_effect = [
            RuntimeError("transient"),
            {"results": []},
        ]
        result = asyncio.run(_search_with_retry(client, "q", 5, 10.0))
        assert result == {"results": []}

    @patch("template_mcp_server.src.tools.web_search_tool.RETRY_DELAYS_SECONDS", (0, 0))
    def test_raises_after_all_retries_exhausted(self):
        client = AsyncMock()
        client.search.side_effect = RuntimeError("permanent")
        import pytest

        with pytest.raises(RuntimeError, match="permanent"):
            asyncio.run(_search_with_retry(client, "q", 5, 10.0))
        assert client.search.call_count == 3


class TestTruncateSnippet:
    """Test _truncate_snippet utility."""

    def test_short_content_unchanged(self):
        assert _truncate_snippet("hello", 100) == "hello"

    def test_long_content_truncated(self):
        result = _truncate_snippet("a" * 200, 50)
        assert len(result) <= 50
        assert result.endswith("...")

    def test_exact_length_unchanged(self):
        assert _truncate_snippet("abc", 3) == "abc"
