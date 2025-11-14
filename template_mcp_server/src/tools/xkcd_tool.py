import httpx
from typing import Any, Dict, Optional

from template_mcp_server.utils.pylogger import get_python_logger

logger = get_python_logger()
http_client = httpx.AsyncClient()

async def get_xkcd_comic(comic_number: Optional[int] = None) -> Dict[str, Any]:
    """
    TOOL_NAME=get_xkcd_comic
    DISPLAY_NAME=XKCD Comic Fetcher
    USECASE=Fetches a specific XKCD comic by its number. If no number is given, fetches the latest comic.
    INSTRUCTIONS=1. Provide an optional 'comic_number' (integer). 2. If no number is provided, the latest comic is returned. 3. Receive the comic's title, image URL, and alt-text.
    INPUT_DESCRIPTION=An optional integer 'comic_number'.
    OUTPUT_DESCRIPTION=Dictionary with status, title, image URL (img_url), and alt-text (alt_text).
    EXAMPLES=get_xkcd_comic(comic_number=327), get_xkcd_comic()
    PREREQUISITES=None
    RELATED_TOOLS=None
    """
    if comic_number:
        url = f"https://xkcd.com/{comic_number}/info.0.json"
        log_msg = f"Fetching XKCD comic number {comic_number}"
    else:
        url = "https://xkcd.com/info.0.json"
        log_msg = "Fetching latest XKCD comic"
        
    logger.info(log_msg)

    try:
        response = await http_client.get(url, timeout=5.0)
        
        # This will raise an error for 404 (comic not found) or 500
        response.raise_for_status() 
        
        data = response.json()
        
        return {
            "status": "success",
            "operation": "get_xkcd",
            "comic_number": data["num"],
            "title": data["safe_title"],
            "img_url": data["img"],
            "alt_text": data["alt"],
            "message": f"Found comic: {data['safe_title']}"
        }

    except httpx.HTTPStatusError as e:
        if e.response.status_code == 404:
            logger.warning(f"XKCD comic not found: {comic_number}")
            return {"status": "error", "error": "Not found", "message": f"Comic {comic_number} does not exist."}
        logger.error(f"XKCD API error: {e}")
        return {"status": "error", "error": "API error", "message": f"API returned status {e.response.status_code}"}
    except Exception as e:
        logger.error(f"Error fetching XKCD: {e}")
        return {"status": "error", "error": str(e), "message": "Failed to fetch comic."}
