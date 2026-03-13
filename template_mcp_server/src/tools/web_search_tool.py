"""Web search tool for the Template MCP Server.

This tool provides web search functionality using the Tavily API,
supporting multiple parallel queries with result deduplication.
"""

import asyncio
import os
from typing import Any, Dict, List

from template_mcp_server.utils.pylogger import get_python_logger

logger = get_python_logger()

DEFAULT_TIMEOUT_SECONDS = 15.0
DEFAULT_MAX_SNIPPET_LENGTH = 4000
RETRY_DELAYS_SECONDS = (1, 2)


async def _search_with_retry(
    client: Any,
    query: str,
    max_results: int,
    timeout: float,
) -> Dict[str, Any]:
    """Execute a single search with timeout and exponential backoff retries."""
    last_error: BaseException | None = None
    for attempt in range(3):
        try:
            coro = client.search(query, max_results=max_results)
            return await asyncio.wait_for(coro, timeout=timeout)
        except asyncio.TimeoutError as e:
            last_error = e
            logger.warning(
                f"Search timeout (attempt {attempt + 1}/3) for query: {query!r}"
            )
        except Exception as e:
            last_error = e
            logger.warning(
                f"Search failed (attempt {attempt + 1}/3) for query: {query!r} - {e}"
            )
        if attempt < 2:
            delay = RETRY_DELAYS_SECONDS[attempt]
            await asyncio.sleep(delay)
    raise last_error  # type: ignore[misc]


def _truncate_snippet(content: str, max_length: int) -> str:
    """Truncate content to max_length, appending ellipsis if shortened."""
    if len(content) <= max_length:
        return content
    return content[: max_length - 3].rstrip() + "..."


async def web_search(
    queries: List[str],
    max_results: int = 5,
) -> Dict[str, Any]:
    """Search the web for information using the Tavily API.

    TOOL_NAME=web_search
    DISPLAY_NAME=Web Search
    USECASE=Search the web for current information across multiple queries in parallel
    INSTRUCTIONS=1. Provide one or more search queries, 2. Call function, 3. Receive deduplicated results
    INPUT_DESCRIPTION=queries: list of search strings, max_results: results per query (default 5)
    OUTPUT_DESCRIPTION=Dictionary with status, results list (title, url, snippet, score), and query metadata
    EXAMPLES=web_search(["Python 3.12 new features"]), web_search(["LangGraph tutorial", "MCP protocol"])
    PREREQUISITES=TAVILY_API_KEY environment variable must be set
    RELATED_TOOLS=None

    I/O-bound operation - uses async for network requests.

    Args:
        queries: List of search query strings to execute in parallel
        max_results: Maximum number of results to return per query (1-10)

    Returns:
        Dictionary containing deduplicated search results with structured metadata

    Raises:
        ValueError: If queries list is empty or max_results is out of range
    """
    timeout = float(os.environ.get("WEB_SEARCH_TIMEOUT", DEFAULT_TIMEOUT_SECONDS))
    max_snippet_length = int(
        os.environ.get("WEB_SEARCH_MAX_SNIPPET_LENGTH", str(DEFAULT_MAX_SNIPPET_LENGTH))
    )

    try:
        if not queries:
            raise ValueError("At least one search query is required")

        max_results = max(1, min(max_results, 10))

        api_key = os.environ.get("TAVILY_API_KEY", "")
        if not api_key:
            return {
                "status": "error",
                "error": "TAVILY_API_KEY environment variable is not set",
                "message": "Web search requires a Tavily API key",
            }

        from tavily import AsyncTavilyClient

        client = AsyncTavilyClient(api_key=api_key)

        tasks = [
            _search_with_retry(client, query, max_results, timeout) for query in queries
        ]
        raw_results = await asyncio.gather(*tasks, return_exceptions=True)

        seen_urls: set[str] = set()
        deduplicated: List[Dict[str, Any]] = []

        for i, result in enumerate(raw_results):
            if isinstance(result, (Exception, BaseException)):
                logger.warning(f"Search query failed: {queries[i]} - {result}")
                continue

            assert isinstance(result, dict)
            for item in result.get("results", []):
                url = item.get("url", "")
                if url and url not in seen_urls:
                    seen_urls.add(url)
                    content = item.get("content", "")
                    deduplicated.append(
                        {
                            "title": item.get("title", ""),
                            "url": url,
                            "snippet": _truncate_snippet(content, max_snippet_length),
                            "score": item.get("score"),
                            "query": queries[i],
                        }
                    )

        logger.info(
            f"Web search completed: {len(queries)} queries, "
            f"{len(deduplicated)} unique results"
        )

        return {
            "status": "success",
            "queries": queries,
            "total_results": len(deduplicated),
            "results": deduplicated,
            "message": f"Found {len(deduplicated)} results across {len(queries)} queries",
        }

    except Exception as e:
        logger.error(f"Error in web_search tool: {e}")
        return {
            "status": "error",
            "error": str(e),
            "message": "Failed to perform web search",
        }
