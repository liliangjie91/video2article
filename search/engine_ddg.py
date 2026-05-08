"""DuckDuckGo search via HTML scrape (no API key needed)."""

import logging
import re

import requests

from ._utils import SearchResult

logger = logging.getLogger(__name__)
_URL = "https://html.duckduckgo.com/html/"


def search(query: str, num_results: int = 5) -> list[SearchResult]:
    """Search DuckDuckGo via the HTML endpoint."""
    try:
        resp = requests.post(
            _URL,
            data={"q": query},
            headers={"User-Agent": "Mozilla/5.0 (compatible; video2article/1.0)"},
            timeout=15,
        )
        resp.raise_for_status()
        return _parse_results(resp.text, num_results)
    except Exception as e:
        logger.warning("DuckDuckGo search failed: %s", e)
        return []


def _parse_results(html: str, num_results: int) -> list[SearchResult]:
    results = []
    # DuckDuckGo HTML results are in <div class="... result__body"> blocks
    blocks = re.findall(
        r'<div[^>]*class="[^"]*result__body[^"]*">.*?</div>\s*</div>', html, re.DOTALL
    )
    for block in blocks[:num_results]:
        url_match = re.search(r'href="(https?://[^"]+)"', block)
        url = url_match.group(1) if url_match else ""

        title_match = re.search(
            r'<h2 class="result__title">.*?<a[^>]*>(.*?)</a>', block, re.DOTALL
        )
        title = re.sub(r"<[^>]+>", "", title_match.group(1)).strip() if title_match else ""

        snippet_match = re.search(
            r'<a class="result__snippet"[^>]*>(.*?)</a>', block, re.DOTALL
        )
        snippet = re.sub(r"<[^>]+>", "", snippet_match.group(1)).strip() if snippet_match else ""

        results.append(SearchResult(title=title, url=url, snippet=snippet))
    return results
