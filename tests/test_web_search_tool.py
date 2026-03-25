"""Tests for the search_web MCP tool."""

import asyncio
from unittest.mock import AsyncMock, patch

import pytest

from template_mcp_server.src.settings import settings
from template_mcp_server.src.tools.web_search_tool import (
    _search_with_retry,
    _truncate_snippet,
    search_web,
)

_CLIENT_PATH = "template_mcp_server.src.tools.web_search_tool.AsyncTavilyClient"


class TestTruncateSnippet:
    """Test the _truncate_snippet helper."""

    def test_short_content_unchanged(self):
        """Content shorter than max_length is returned as-is."""
        assert _truncate_snippet("hello", 100) == "hello"

    def test_long_content_truncated(self):
        """Content exceeding max_length is truncated with ellipsis."""
        text = "a" * 100
        result = _truncate_snippet(text, 50)
        assert len(result) == 50
        assert result.endswith("...")


class TestSearchWithRetry:
    """Test the _search_with_retry function."""

    def test_success_on_first_attempt(self):
        """Successful search on the first try returns immediately."""
        client = AsyncMock()
        client.search.return_value = {"results": []}
        result = asyncio.run(
            _search_with_retry(client, "test", max_results=3, timeout=5.0)
        )
        assert result == {"results": []}
        assert client.search.call_count == 1

    def test_retries_and_succeeds(self):
        """Search retries on failure and eventually succeeds."""
        client = AsyncMock()
        client.search.side_effect = [
            RuntimeError("fail"),
            {"results": []},
        ]
        result = asyncio.run(
            _search_with_retry(client, "test", max_results=3, timeout=5.0)
        )
        assert result == {"results": []}
        assert client.search.call_count == 2

    def test_raises_after_all_retries_exhausted(self):
        """Raises the last error after 3 failed attempts."""
        client = AsyncMock()
        client.search.side_effect = RuntimeError("persistent failure")
        with pytest.raises(RuntimeError, match="persistent failure"):
            asyncio.run(_search_with_retry(client, "test", max_results=3, timeout=5.0))
        assert client.search.call_count == 3


class TestWebSearch:
    """Test the search_web tool."""

    def test_empty_queries_returns_error(self):
        """Empty queries list returns a validation error."""
        result = asyncio.run(search_web(queries=[]))
        assert result["status"] == "error"
        assert "At least one search query" in result["error"]

    @patch.object(settings, "TAVILY_API_KEY", "")
    def test_missing_api_key_returns_error(self):
        """Missing TAVILY_API_KEY returns an error."""
        result = asyncio.run(search_web(queries=["test query"]))
        assert result["status"] == "error"
        assert "TAVILY_API_KEY" in result["error"]

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
        assert result["results"][0]["url"] == "https://example.com/1"

    @patch(_CLIENT_PATH)
    @patch.object(settings, "TAVILY_API_KEY", "test-key")
    def test_deduplicates_results(self, mock_client_cls):
        """Duplicate URLs across queries are deduplicated."""
        mock_client = AsyncMock()
        mock_client.search.side_effect = [
            {
                "results": [
                    {
                        "title": "A",
                        "url": "https://example.com/shared",
                        "content": "Same",
                    }
                ]
            },
            {
                "results": [
                    {
                        "title": "B",
                        "url": "https://example.com/shared",
                        "content": "Same",
                    }
                ]
            },
        ]
        mock_client_cls.return_value = mock_client

        result = asyncio.run(search_web(queries=["query 1", "query 2"]))

        assert result["status"] == "success"
        assert result["total_results"] == 1

    @patch(_CLIENT_PATH)
    @patch.object(settings, "TAVILY_API_KEY", "test-key")
    def test_handles_partial_failure(self, mock_client_cls):
        """One failing query doesn't break the whole search."""
        mock_client = AsyncMock()
        mock_client.search.side_effect = [
            RuntimeError("API error"),
            {
                "results": [
                    {"title": "OK", "url": "https://example.com/ok", "content": "Fine"}
                ]
            },
        ]
        mock_client_cls.return_value = mock_client

        result = asyncio.run(search_web(queries=["fail query", "ok query"]))

        assert result["status"] == "success"
        assert result["total_results"] == 1
