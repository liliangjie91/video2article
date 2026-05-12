"""DuckDuckGo search via HTML scrape (no API key needed).

Tries multiple endpoints and User-Agents to work around blocking.
Performs a one-time connectivity check on import; if DuckDuckGo is
unreachable (e.g. network-level SSL block), search() fails fast."""

import logging
import re
import time

import requests
from requests.exceptions import SSLError, ConnectionError as ReqConnError

from ._utils import SearchResult

logger = logging.getLogger(__name__)

_HTML_URL = "https://html.duckduckgo.com/html/"
_LITE_URL = "https://lite.duckduckgo.com/lite/"
_USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.5 Safari/605.1.15",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
]
_ATTEMPTS = [
    (_HTML_URL, 0, 1),   # 1st: HTML endpoint, UA[0], wait 1s
    (_HTML_URL, 1, 2),   # 2nd: HTML endpoint, UA[1], wait 2s
    (_LITE_URL, 2, 0),   # 3rd: Lite endpoint, UA[2], no wait
]

# One-time connectivity check — if DDG is fundamentally unreachable (SSL block),
# skip all retries to avoid ~15s of timeouts per search.
_available: bool = True


def _check_connectivity() -> bool:
    """Return False if DuckDuckGo is unreachable at the transport level."""
    for url in (_HTML_URL, _LITE_URL):
        try:
            resp = requests.get(url, timeout=5)
            resp.raise_for_status()
            return True
        except (SSLError, ReqConnError):
            continue
        except Exception:
            return True  # non-transport errors (4xx, etc.) mean DDG is reachable
    return False


_available = _check_connectivity()
if not _available:
    logger.warning(
        "DuckDuckGo is unreachable on this network (SSL connection failed). "
        "Remove 'ddg' from config.ini [search] engines or use a proxy."
    )


def search(query: str, num_results: int = 5) -> list[SearchResult]:
    """Search DuckDuckGo, trying multiple endpoints and User-Agents.

    Returns immediately if the one-time connectivity check failed.
    """
    if not _available:
        return []

    session = requests.Session()
    adapter = requests.adapters.HTTPAdapter(pool_maxsize=1)
    session.mount("https://", adapter)

    for url, ua_idx, wait in _ATTEMPTS:
        try:
            resp = session.post(
                url,
                data={"q": query},
                headers={"User-Agent": _USER_AGENTS[ua_idx]},
                timeout=15,
            )
            resp.raise_for_status()
            results = _parse_html(resp.text, num_results) if "html." in url else _parse_lite(resp.text, num_results)
            if results:
                return results
        except Exception as e:
            logger.warning("DuckDuckGo %s attempt failed: %s", url.split("/")[2], e)
            if wait:
                time.sleep(wait)

    logger.warning("DuckDuckGo search failed after all %d attempts", len(_ATTEMPTS))
    return []


def _parse_html(html: str, num_results: int) -> list[SearchResult]:
    """Parse the full HTML endpoint (html.duckduckgo.com/html/)."""
    results = []
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

        if url:
            results.append(SearchResult(title=title, url=url, snippet=snippet))
    return results


def _parse_lite(html: str, num_results: int) -> list[SearchResult]:
    """Parse the lite endpoint (lite.duckduckgo.com/lite/).

    Lite returns a table-based layout: each result is a <tr> with
    .result-link (title+url) and .result-snippet rows.
    """
    results = []
    # Find all result blocks wrapped in <tbody>
    sections = re.findall(
        r'<tbody[^>]*class="[^"]*result[^"]*"[^>]*>.*?</tbody>', html, re.DOTALL
    )
    for section in sections[:num_results]:
        url_match = re.search(r'href="(https?://[^"]+)"', section)
        url = url_match.group(1) if url_match else ""

        title_match = re.search(r'<a[^>]*>(.*?)</a>', section, re.DOTALL)
        title = re.sub(r"<[^>]+>", "", title_match.group(1)).strip() if title_match else ""

        snippet_match = re.search(
            r'<td class="result-snippet">(.*?)</td>', section, re.DOTALL
        )
        snippet = re.sub(r"<[^>]+>", "", snippet_match.group(1)).strip() if snippet_match else ""

        if url:
            results.append(SearchResult(title=title, url=url, snippet=snippet))
    return results
