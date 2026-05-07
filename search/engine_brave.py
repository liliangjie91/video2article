"""Brave Search API."""

import logging
import os

import requests

from ._utils import SearchResult

logger = logging.getLogger(__name__)
_API_URL = "https://api.search.brave.com/res/v1/web/search"


def search(query: str, num_results: int = 5) -> list[SearchResult]:
    """Search via Brave Search API.  Returns empty list if ``BRAVE_API_KEY`` is not set."""
    api_key = os.environ.get("BRAVE_API_KEY")
    if not api_key:
        logger.warning("BRAVE_API_KEY not set, skipping Brave")
        return []

    try:
        resp = requests.get(
            _API_URL,
            headers={"X-Subscription-Token": api_key},
            params={"q": query, "count": num_results},
            timeout=15,
        )
        resp.raise_for_status()
        data = resp.json()
        return [
            SearchResult(
                title=r.get("title", ""),
                url=r.get("url", ""),
                snippet=(r.get("description", "") or "")[:500],
            )
            for r in data.get("web", {}).get("results", [])
        ]
    except Exception as e:
        logger.warning("Brave search failed: %s", e)
        return []
