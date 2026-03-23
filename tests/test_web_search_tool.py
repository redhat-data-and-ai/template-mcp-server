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

_SETTINGS_PATH = "template_mcp_server.src.tools.web_search_tool.settings"
_CLIENT_PATH = "template_mcp_server.src.tools.web_search_tool.AsyncTavilyClient"


class TestTruncateSnippet:
    """Test the _truncate_snippet helper."""

    def test_short_content_unchanged(self):
        """Content shorter than max_length is returned as-is."""
        assert _truncate_snippet("hello", 100) == "hello"

    def test_exact_length_unchanged(self):
        """Content exactly at max_length is returned as-is."""
        text = "a" * 50
        assert _truncate_snippet(text, 50) == text

    def test_long_content_truncated_with_ellipsis(self):
        """Content exceeding max_length is truncated with trailing ellipsis."""
        text = "a" * 100
        result = _truncate_snippet(text, 50)
        assert len(result) == 50
        assert result.endswith("...")

    def test_empty_content(self):
        """Empty string is returned unchanged."""
        assert _truncate_snippet("", 100) == ""


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

    def test_retries_on_exception(self):
        """Search retries up to 3 times on transient exceptions."""
        client = AsyncMock()
        client.search.side_effect = [
            RuntimeError("fail"),
            RuntimeError("fail"),
            {"results": []},
        ]
        result = asyncio.run(
            _search_with_retry(client, "test", max_results=3, timeout=5.0)
        )
        assert result == {"results": []}
        assert client.search.call_count == 3

    def test_retries_on_timeout(self):
        """Search retries on asyncio.TimeoutError and succeeds."""
        client = AsyncMock()
        client.search.side_effect = [
            asyncio.TimeoutError(),
            {"results": [{"title": "OK"}]},
        ]
        result = asyncio.run(
            _search_with_retry(client, "test", max_results=3, timeout=0.01)
        )
        assert result == {"results": [{"title": "OK"}]}
        assert client.search.call_count == 2

    def test_raises_after_all_retries_exhausted(self):
        """Raises the last error after 3 failed attempts."""
        client = AsyncMock()
        client.search.side_effect = RuntimeError("persistent failure")
        with pytest.raises(RuntimeError, match="persistent failure"):
            asyncio.run(_search_with_retry(client, "test", max_results=3, timeout=5.0))
        assert client.search.call_count == 3

    def test_raises_timeout_after_all_retries(self):
        """Raises TimeoutError if all 3 attempts time out."""
        client = AsyncMock()
        client.search.side_effect = asyncio.TimeoutError()
        with pytest.raises(asyncio.TimeoutError):
            asyncio.run(_search_with_retry(client, "test", max_results=3, timeout=0.01))
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
    def test_single_query_success(self, mock_client_cls):
        """Successful search with a single query returns results."""
        mock_client = AsyncMock()
        mock_client.search.return_value = {
            "results": [
                {
                    "title": "Result 1",
                    "url": "https://example.com/1",
                    "content": "Snippet 1",
                    "score": 0.95,
                },
                {
                    "title": "Result 2",
                    "url": "https://example.com/2",
                    "content": "Snippet 2",
                    "score": 0.85,
                },
            ]
        }
        mock_client_cls.return_value = mock_client

        result = asyncio.run(search_web(queries=["python tutorial"]))

        assert result["status"] == "success"
        assert result["total_results"] == 2
        assert len(result["results"]) == 2
        assert result["results"][0]["title"] == "Result 1"
        assert result["results"][0]["url"] == "https://example.com/1"
        assert result["results"][0]["score"] == 0.95

    @patch(_CLIENT_PATH)
    @patch.object(settings, "TAVILY_API_KEY", "test-key")
    def test_deduplicates_results(self, mock_client_cls):
        """Duplicate URLs across queries are deduplicated."""
        mock_client = AsyncMock()
        mock_client.search.side_effect = [
            {
                "results": [
                    {
                        "title": "Shared",
                        "url": "https://example.com/shared",
                        "content": "Same",
                    }
                ]
            },
            {
                "results": [
                    {
                        "title": "Shared Copy",
                        "url": "https://example.com/shared",
                        "content": "Same again",
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
                    {
                        "title": "OK",
                        "url": "https://example.com/ok",
                        "content": "Fine",
                    }
                ]
            },
        ]
        mock_client_cls.return_value = mock_client

        result = asyncio.run(search_web(queries=["fail query", "ok query"]))

        assert result["status"] == "success"
        assert result["total_results"] == 1

    @patch(_CLIENT_PATH)
    @patch.object(settings, "TAVILY_API_KEY", "test-key")
    def test_skips_items_with_empty_url(self, mock_client_cls):
        """Results with empty URLs are excluded."""
        mock_client = AsyncMock()
        mock_client.search.return_value = {
            "results": [
                {"title": "No URL", "url": "", "content": "Skip me"},
                {
                    "title": "Has URL",
                    "url": "https://example.com/real",
                    "content": "Keep me",
                },
            ]
        }
        mock_client_cls.return_value = mock_client

        result = asyncio.run(search_web(queries=["test"]))

        assert result["total_results"] == 1
        assert result["results"][0]["url"] == "https://example.com/real"

    @patch(_CLIENT_PATH)
    @patch.object(settings, "TAVILY_API_KEY", "test-key")
    def test_snippet_truncation(self, mock_client_cls):
        """Long content is truncated via _truncate_snippet."""
        mock_client = AsyncMock()
        long_content = "x" * 5000
        mock_client.search.return_value = {
            "results": [
                {
                    "title": "Long",
                    "url": "https://example.com/long",
                    "content": long_content,
                }
            ]
        }
        mock_client_cls.return_value = mock_client

        result = asyncio.run(search_web(queries=["test"]))

        snippet = result["results"][0]["snippet"]
        assert len(snippet) <= 4000
        assert snippet.endswith("...")

    @patch.object(settings, "TAVILY_API_KEY", "")
    def test_max_results_clamped(self):
        """max_results is clamped between 1 and 10."""
        result = asyncio.run(search_web(queries=["test"], max_results=0))
        assert result["status"] == "error"
        assert "TAVILY_API_KEY" in result["error"]

    def test_return_structure_on_error(self):
        """Error responses have status, error, and message keys."""
        result = asyncio.run(search_web(queries=[]))
        assert isinstance(result, dict)
        assert "status" in result
        assert "error" in result
        assert "message" in result

    @patch(_CLIENT_PATH)
    @patch.object(settings, "WEB_SEARCH_TIMEOUT", 2.5)
    @patch.object(settings, "TAVILY_API_KEY", "test-key")
    def test_custom_timeout_from_settings(self, mock_client_cls):
        """WEB_SEARCH_TIMEOUT setting overrides default timeout."""
        mock_client = AsyncMock()
        mock_client.search.return_value = {"results": []}
        mock_client_cls.return_value = mock_client

        result = asyncio.run(search_web(queries=["test"]))
        assert result["status"] == "success"

    @patch(_CLIENT_PATH)
    @patch.object(settings, "WEB_SEARCH_MAX_SNIPPET_LENGTH", 50)
    @patch.object(settings, "TAVILY_API_KEY", "test-key")
    def test_custom_snippet_length_from_settings(self, mock_client_cls):
        """WEB_SEARCH_MAX_SNIPPET_LENGTH setting overrides default."""
        mock_client = AsyncMock()
        mock_client.search.return_value = {
            "results": [
                {
                    "title": "T",
                    "url": "https://example.com/t",
                    "content": "a" * 100,
                }
            ]
        }
        mock_client_cls.return_value = mock_client

        result = asyncio.run(search_web(queries=["test"]))
        assert len(result["results"][0]["snippet"]) <= 50

    @patch(_CLIENT_PATH)
    @patch.object(settings, "TAVILY_API_KEY", "test-key")
    def test_all_queries_fail(self, mock_client_cls):
        """When all queries return exceptions, result has zero items."""
        mock_client = AsyncMock()
        mock_client.search.side_effect = Exception("Total failure")
        mock_client_cls.return_value = mock_client

        result = asyncio.run(search_web(queries=["fail1", "fail2"]))

        assert result["status"] == "success"
        assert result["total_results"] == 0
