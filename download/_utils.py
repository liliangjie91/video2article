"""Internal utilities for download package — cache, URL detection, ID extraction."""

import json
import os

import download


def is_youtube_url(url: str) -> bool:
    """Check whether a URL targets YouTube.

    Returns True for ``youtube.com``/``youtu.be`` links or bare video IDs
    (the default assumption). Returns False for known non-YouTube platforms.
    """
    if "youtube.com" in url or "youtu.be" in url:
        return True
    if "/" not in url and "." not in url and not url.startswith("http"):
        return True
    return not any(p in url for p in download._KNOWN_NON_YOUTUBE)


def extract_video_id(url: str) -> str:
    """Extract YouTube video ID from URL, or clean URL for cache key."""
    if "youtube.com" in url or "youtu.be" in url:
        if "youtu.be" in url:
            return url.split("/")[-1].split("?")[0]
        import urllib.parse

        parsed = urllib.parse.urlparse(url)
        qs = urllib.parse.parse_qs(parsed.query)
        return qs.get("v", [url])[0]
    clean = url.split("?")[0] if "?" in url else url
    return clean.rstrip("/")


def _read_cache(type: str | None = None) -> dict[str, dict[str, str]]:
    """Read download cache, filtering by type if given."""
    if not os.path.exists(download.CACHE_FILE):
        return {}
    cache: dict[str, dict[str, str]] = {}
    with open(download.CACHE_FILE, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            parts = line.split(",", 2)
            if len(parts) == 3 and parts[0] in download.CACHE_TYPES:
                entry_type, vid, path = parts
            elif len(parts) == 2:
                entry_type = "unknown"
                vid, path = parts
            else:
                continue
            if entry_type != "info" and not os.path.exists(path):
                continue
            if type is None or entry_type == type:
                cache[vid] = {"type": entry_type, "path": path}
    return cache


def get_cache(type: str, video_id: str) -> dict | str | None:
    """Look up a cache entry by type and video_id."""
    cache = _read_cache(type=type)
    if video_id not in cache:
        return None
    entry = cache[video_id]["path"]
    if type == "info":
        return json.loads(entry)
    return entry


def write_cache(type: str, video_id: str, data: str | dict) -> None:
    """Append one entry to the download cache."""
    path = json.dumps(data, ensure_ascii=False) if isinstance(data, dict) else data
    with open(download.CACHE_FILE, "a", encoding="utf-8") as f:
        f.write(f"{type},{video_id},{path}\n")
