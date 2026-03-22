"""Web search tool for the Template MCP Server.

This tool provides web search functionality using the Tavily API,
supporting multiple parallel queries with result deduplication.
"""

import asyncio
from typing import Any, Dict, List

from template_mcp_server.src.settings import settings
from template_mcp_server.utils.pylogger import get_python_logger

try:
    from tavily import AsyncTavilyClient
except ImportError:
    AsyncTavilyClient = None

logger = get_python_logger()

RETRY_DELAYS_SECONDS = (1, 2)
_SEARCH_CONCURRENCY = 5


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

    I/O-bound operation - uses async for network requests.

    Args:
        queries: List of search query strings to execute in parallel
        max_results: Maximum number of results to return per query (1-10)

    Returns:
        Dictionary containing deduplicated search results with structured metadata

    Raises:
        ValueError: If queries list is empty or max_results is out of range
    """
    timeout = settings.WEB_SEARCH_TIMEOUT
    max_snippet_length = settings.WEB_SEARCH_MAX_SNIPPET_LENGTH

    try:
        if not queries:
            raise ValueError("At least one search query is required")

        max_results = max(1, min(max_results, 10))

        api_key = settings.TAVILY_API_KEY
        if not api_key:
            return {
                "status": "error",
                "error": "TAVILY_API_KEY is not configured",
                "message": "Web search requires a Tavily API key",
            }

        if AsyncTavilyClient is None:
            return {
                "status": "error",
                "error": "tavily-python package is not installed",
                "message": "Install tavily-python to use web search",
            }

        client = AsyncTavilyClient(api_key=api_key)

        semaphore = asyncio.Semaphore(_SEARCH_CONCURRENCY)

        async def _limited_search(query: str) -> Dict[str, Any]:
            async with semaphore:
                return await _search_with_retry(client, query, max_results, timeout)

        tasks = [_limited_search(query) for query in queries]
        raw_results = await asyncio.gather(*tasks, return_exceptions=True)

        seen_urls: set[str] = set()
        deduplicated: List[Dict[str, Any]] = []

        for i, result in enumerate(raw_results):
            if isinstance(result, BaseException):
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
        logger.exception("Error in web_search tool: %s", e)
        return {
            "status": "error",
            "error": str(e),
            "message": "Failed to perform web search",
        }
