"""Search abstraction — Tavily, Brave, DuckDuckGo."""

import importlib
import logging
import os

from dotenv import load_dotenv
from config import get_config

load_dotenv()

from ._utils import SearchResult  # noqa: F401

logger = logging.getLogger(__name__)

_ENGINES = {
    "tavily": "search.engine_tavily",
    "brave": "search.engine_brave",
    "ddg": "search.engine_ddg",
}

_next_engine = 0


def get_configured_engines() -> list[str]:
    """Read engine list from ``config.ini [search]``, filtered by API key availability."""
    cfg = get_config()
    raw = cfg.get("search", "engines", fallback="")
    if not raw:
        return []
    engines = [e.strip() for e in raw.split(",") if e.strip()]

    available = []
    for e in engines:
        if e == "ddg":
            available.append(e)
        elif e == "tavily" and os.environ.get("TAVILY_API_KEY"):
            available.append(e)
        elif e == "brave" and os.environ.get("BRAVE_API_KEY"):
            available.append(e)
        else:
            logger.debug("Search engine '%s' not available (missing API key)", e)
    return available


def search(query: str, engines: list[str] | None = None, num_results: int = 5) -> list[SearchResult]:
    """Execute a search query, round-robin across *engines*.

    Returns deduplicated results (by URL).  Falls back to the next engine on failure.
    """
    global _next_engine

    if engines is None:
        engines = get_configured_engines()
    if not engines:
        return []

    idx = _next_engine % len(engines)
    _next_engine = idx + 1
    engine_name = engines[idx]

    mod_path = _ENGINES.get(engine_name)
    if mod_path is None:
        logger.warning("Unknown search engine: %s", engine_name)
        return []

    try:
        mod = importlib.import_module(mod_path)
        results = mod.search(query, num_results)
        logger.info("'%s' returned %d results for: %s", engine_name, len(results), query[:80])
        return results
    except Exception as e:
        logger.warning("'%s' failed: %s — trying fallback", engine_name, e)
        remaining = [e for i, e in enumerate(engines) if i != idx]
        if remaining:
            return search(query, remaining, num_results)
        return []
