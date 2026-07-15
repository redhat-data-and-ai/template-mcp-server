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
    logger.debug(
        "Starting search with retry",
        extra={
            "input": {"query": query, "max_results": max_results, "timeout": timeout}
        },
    )

    last_error: BaseException | None = None
    for attempt in range(3):
        try:
            logger.debug(
                "Executing search attempt",
                extra={"query": query, "attempt": attempt + 1, "max_attempts": 3},
            )
            coro = client.search(query, max_results=max_results)
            result = await asyncio.wait_for(coro, timeout=timeout)
            logger.debug(
                "Search attempt succeeded",
                extra={
                    "query": query,
                    "attempt": attempt + 1,
                    "results_count": len(result.get("results", [])),
                },
            )
            return result
        except asyncio.TimeoutError as e:
            last_error = e
            logger.warning(
                "Search timeout",
                extra={
                    "query": query,
                    "attempt": attempt + 1,
                    "max_attempts": 3,
                    "timeout": timeout,
                },
            )
        except Exception as e:
            last_error = e
            logger.warning(
                "Search attempt failed",
                extra={
                    "query": query,
                    "attempt": attempt + 1,
                    "max_attempts": 3,
                    "error": str(e),
                },
            )
        if attempt < 2:
            delay = RETRY_DELAYS_SECONDS[attempt]
            logger.debug(
                "Retrying after delay",
                extra={"query": query, "delay_seconds": delay},
            )
            await asyncio.sleep(delay)

    logger.error(
        "All search attempts failed",
        extra={"query": query, "max_attempts": 3, "error": str(last_error)},
    )
    raise last_error  # type: ignore[misc]


def _truncate_snippet(content: str, max_length: int) -> str:
    """Truncate content to max_length, appending ellipsis if shortened."""
    if len(content) <= max_length:
        return content
    return content[: max_length - 3].rstrip() + "..."


async def search_web(
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

    logger.info(
        "search_web invoked",
        extra={
            "input": {
                "queries": queries,
                "max_results": max_results,
                "timeout": timeout,
                "max_snippet_length": max_snippet_length,
            }
        },
    )

    try:
        if not queries:
            error_msg = "At least one search query is required"
            logger.error(
                "Input validation failed",
                extra={"error": error_msg, "queries": queries},
            )
            raise ValueError(error_msg)

        max_results = max(1, min(max_results, 10))
        logger.debug(
            "max_results normalized",
            extra={"max_results": max_results},
        )

        api_key = settings.TAVILY_API_KEY
        if not api_key:
            error_result = {
                "status": "error",
                "error": "TAVILY_API_KEY is not configured",
                "message": "Web search requires a Tavily API key",
            }
            logger.error(
                "API key validation failed",
                extra={"output": error_result},
            )
            return error_result

        if AsyncTavilyClient is None:
            error_result = {
                "status": "error",
                "error": "tavily-python package is not installed",
                "message": "Install tavily-python to use web search",
            }
            logger.error(
                "Package validation failed",
                extra={"output": error_result},
            )
            return error_result

        client = AsyncTavilyClient(api_key=api_key)
        logger.debug("Tavily client initialized")

        semaphore = asyncio.Semaphore(_SEARCH_CONCURRENCY)
        logger.debug(
            "Search semaphore created",
            extra={"concurrency_limit": _SEARCH_CONCURRENCY},
        )

        async def _limited_search(query: str) -> Dict[str, Any]:
            async with semaphore:
                return await _search_with_retry(client, query, max_results, timeout)

        logger.info(
            "Executing parallel web searches",
            extra={"num_queries": len(queries), "queries": queries},
        )

        tasks = [_limited_search(query) for query in queries]
        raw_results = await asyncio.gather(*tasks, return_exceptions=True)

        logger.debug(
            "Raw search results received",
            extra={"num_results": len(raw_results)},
        )

        seen_urls: set[str] = set()
        deduplicated: List[Dict[str, Any]] = []
        failed_queries = 0

        for i, result in enumerate(raw_results):
            if isinstance(result, BaseException):
                failed_queries += 1
                logger.warning(
                    "Search query failed",
                    extra={"query": queries[i], "error": str(result), "query_index": i},
                )
                continue

            assert isinstance(result, dict)
            query_results_count = 0
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
                    query_results_count += 1

            logger.debug(
                "Query processed",
                extra={
                    "query": queries[i],
                    "results_count": query_results_count,
                    "query_index": i,
                },
            )

        logger.info(
            "Web search completed successfully",
            extra={
                "input": {
                    "num_queries": len(queries),
                    "queries": queries,
                    "max_results": max_results,
                },
                "output": {
                    "total_unique_results": len(deduplicated),
                    "failed_queries": failed_queries,
                    "successful_queries": len(queries) - failed_queries,
                },
            },
        )

        output = {
            "status": "success",
            "queries": queries,
            "total_results": len(deduplicated),
            "results": deduplicated,
            "message": f"Found {len(deduplicated)} results across {len(queries)} queries",
        }

        logger.debug("search_web output", extra={"output": output})
        return output

    except Exception as e:
        logger.exception(
            "Error in search_web",
            extra={
                "input": {"queries": queries, "max_results": max_results},
                "error": str(e),
            },
        )
        error_output = {
            "status": "error",
            "error": str(e),
            "message": "Failed to perform web search",
        }
        logger.debug("search_web error output", extra={"output": error_output})
        return error_output
