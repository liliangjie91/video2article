"""Tavily Search API."""

import logging
import os

import requests

from ._utils import SearchResult

logger = logging.getLogger(__name__)
_API_URL = "https://api.tavily.com/search"


def search(query: str, num_results: int = 5) -> list[SearchResult]:
    """Search via Tavily API.  Returns empty list if ``TAVILY_API_KEY`` is not set."""
    api_key = os.environ.get("TAVILY_API_KEY")
    if not api_key:
        logger.warning("TAVILY_API_KEY not set, skipping Tavily")
        return []

    try:
        resp = requests.post(
            _API_URL,
            json={
                "api_key": api_key,
                "query": query,
                "search_depth": "basic",
                "max_results": num_results,
            },
            timeout=15,
        )
        resp.raise_for_status()
        data = resp.json()
        return [
            SearchResult(
                title=r.get("title", ""),
                url=r.get("url", ""),
                snippet=(r.get("content", "") or "")[:500],
            )
            for r in data.get("results", [])
        ]
    except Exception as e:
        logger.warning("Tavily search failed: %s", e)
        return []
