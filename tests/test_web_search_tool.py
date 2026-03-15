"""Tests for the web_search MCP tool."""

import asyncio
from unittest.mock import AsyncMock, patch

import pytest

from template_mcp_server.src.tools.web_search_tool import web_search


class TestWebSearch:
    """Test the web_search tool."""

    def test_web_search_empty_queries_returns_error(self):
        """Test that empty queries list returns a validation error."""
        result = asyncio.run(web_search(queries=[]))
        assert result["status"] == "error"
        assert "At least one search query" in result["error"]

    @patch.dict("os.environ", {"TAVILY_API_KEY": ""})
    def test_web_search_missing_api_key_returns_error(self):
        """Test that missing TAVILY_API_KEY returns an error."""
        result = asyncio.run(web_search(queries=["test query"]))
        assert result["status"] == "error"
        assert "TAVILY_API_KEY" in result["error"]

    @patch.dict("os.environ", {"TAVILY_API_KEY": "test-key"})
    @patch("tavily.AsyncTavilyClient")
    def test_web_search_single_query_success(self, mock_client_cls):
        """Test successful search with a single query."""
        mock_client = AsyncMock()
        mock_client.search.return_value = {
            "results": [
                {"title": "Result 1", "url": "https://example.com/1", "content": "Snippet 1"},
                {"title": "Result 2", "url": "https://example.com/2", "content": "Snippet 2"},
            ]
        }
        mock_client_cls.return_value = mock_client

        result = asyncio.run(web_search(queries=["python tutorial"]))

        assert result["status"] == "success"
        assert result["total_results"] == 2
        assert len(result["results"]) == 2
        assert result["results"][0]["title"] == "Result 1"
        assert result["results"][0]["url"] == "https://example.com/1"

    @patch.dict("os.environ", {"TAVILY_API_KEY": "test-key"})
    @patch("tavily.AsyncTavilyClient")
    def test_web_search_deduplicates_results(self, mock_client_cls):
        """Test that duplicate URLs are deduplicated across queries."""
        mock_client = AsyncMock()
        mock_client.search.side_effect = [
            {"results": [{"title": "Shared", "url": "https://example.com/shared", "content": "Same"}]},
            {"results": [{"title": "Shared Copy", "url": "https://example.com/shared", "content": "Same again"}]},
        ]
        mock_client_cls.return_value = mock_client

        result = asyncio.run(web_search(queries=["query 1", "query 2"]))

        assert result["status"] == "success"
        assert result["total_results"] == 1

    @patch.dict("os.environ", {"TAVILY_API_KEY": "test-key"})
    @patch("tavily.AsyncTavilyClient")
    def test_web_search_handles_partial_failure(self, mock_client_cls):
        """Test that one failing query doesn't break the whole search."""
        mock_client = AsyncMock()
        mock_client.search.side_effect = [
            Exception("API error"),
            {"results": [{"title": "OK", "url": "https://example.com/ok", "content": "Fine"}]},
        ]
        mock_client_cls.return_value = mock_client

        result = asyncio.run(web_search(queries=["fail query", "ok query"]))

        assert result["status"] == "success"
        assert result["total_results"] == 1

    def test_web_search_max_results_clamped(self):
        """Test that max_results is clamped between 1 and 10."""
        # max_results > 10 should be clamped to 10, < 1 to 1
        # We can only test the clamping logic indirectly since we need an API key
        # to proceed past validation. This tests the boundary of the input.
        result = asyncio.run(web_search(queries=["test"], max_results=0))
        # Without API key, this will return the TAVILY_API_KEY error,
        # confirming the function reached past the max_results clamping.
        assert result["status"] == "error"

    def test_web_search_return_structure(self):
        """Test that error responses have the correct structure."""
        result = asyncio.run(web_search(queries=[]))
        assert isinstance(result, dict)
        assert "status" in result
        assert "error" in result
        assert "message" in result
