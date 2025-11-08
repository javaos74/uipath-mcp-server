"""Google Search built-in tool."""

import logging
from typing import Dict, Any, Optional
import httpx

logger = logging.getLogger(__name__)


async def google_search(q: str, api_key: Optional[str] = None) -> Dict[str, Any]:
    """
    Perform a Google search using the Custom Search JSON API.
    
    Args:
        q: Search query string
        api_key: Google Custom Search API key (optional, from builtin_tools table)
        
    Returns:
        Dictionary containing search results or error information
        
    Note:
        This is a sample implementation. For production use, you need:
        1. Google Custom Search API key
        2. Custom Search Engine ID (CX)
        
        Get them from: https://developers.google.com/custom-search/v1/overview
    """
    try:
        logger.info(f"Executing google_search with query: {q}")
        
        # For demo purposes, return a mock response
        # In production, you would use the actual Google Custom Search API
        
        if not api_key:
            logger.warning("No API key provided for google_search")
            return {
                "success": False,
                "error": "Google Custom Search API key not configured",
                "message": "Please configure the API key in the built-in tool settings",
                "query": q
            }
        
        # Mock implementation - replace with actual API call
        # Example of actual implementation:
        """
        cx = "YOUR_CUSTOM_SEARCH_ENGINE_ID"
        url = "https://www.googleapis.com/customsearch/v1"
        params = {
            "key": api_key,
            "cx": cx,
            "q": q,
            "num": 5  # Number of results
        }
        
        async with httpx.AsyncClient() as client:
            response = await client.get(url, params=params)
            response.raise_for_status()
            data = response.json()
            
            results = []
            for item in data.get("items", []):
                results.append({
                    "title": item.get("title"),
                    "link": item.get("link"),
                    "snippet": item.get("snippet")
                })
            
            return {
                "success": True,
                "query": q,
                "total_results": data.get("searchInformation", {}).get("totalResults"),
                "results": results
            }
        """
        
        # Mock response for demonstration
        return {
            "success": True,
            "query": q,
            "message": "This is a demo response. Configure API key for real search.",
            "results": [
                {
                    "title": f"Sample result for: {q}",
                    "link": "https://example.com",
                    "snippet": f"This is a sample search result for the query '{q}'. "
                              "To use real Google search, configure the Google Custom Search API key."
                }
            ]
        }
        
    except httpx.HTTPError as e:
        logger.error(f"HTTP error in google_search: {e}")
        return {
            "success": False,
            "error": "HTTP request failed",
            "message": str(e),
            "query": q
        }
    except Exception as e:
        logger.error(f"Error in google_search: {e}", exc_info=True)
        return {
            "success": False,
            "error": "Search failed",
            "message": str(e),
            "query": q
        }
