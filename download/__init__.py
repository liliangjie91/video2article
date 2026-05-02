"""download package — YouTube subtitle API + yt-dlp fallback."""

import json
import logging
import os

from dotenv import load_dotenv

logger = logging.getLogger(__name__)

# output folder : output/channel_name/20240101_video_id/video_id.{ext}

# Make .env vars available to submodules at import time
load_dotenv()
YOUTUBE_API_BASE = "https://www.googleapis.com/youtube/v3"
# ── Environment variable checks ──────────────────────────────
# youtube.py: get_channel_uploads() requires YouTube Data API key
YOUTUBE_API_KEY = os.getenv("YOUTUBE_API_KEY")
# if not YOUTUBE_API_KEY:
#     logger.warning(
#         "YOUTUBE_API_KEY not set — 'uploads' command will be unavailable. "
#         "Add YOUTUBE_API_KEY=your_key to .env"
#     )

CACHE_FILE = os.path.join(os.path.dirname(__file__), ".download.cache")
CACHE_TYPES = frozenset({"video", "audio", "info"})


def _read_cache(type: str | None = None) -> dict[str, dict[str, str]]:
    """Read download cache, filtering by type if given."""
    if not os.path.exists(CACHE_FILE):
        return {}
    cache: dict[str, dict[str, str]] = {}
    with open(CACHE_FILE, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            parts = line.split(",", 2)
            # New format: type,video_id,path
            if len(parts) == 3 and parts[0] in CACHE_TYPES:
                entry_type, vid, path = parts
            # Old format (backward compat): video_id,path
            elif len(parts) == 2:
                entry_type = "unknown"
                vid, path = parts
            else:
                continue
            # Skip stale file entries (info stores a JSON dict, not a file path)
            if entry_type != "info" and not os.path.exists(path):
                continue
            if type is None or entry_type == type:
                cache[vid] = {"type": entry_type, "path": path}
    return cache


def get_cache(type: str, video_id: str) -> dict | str | None:
    """Look up a cache entry by type and video_id.

    Args:
        type: ``'video'``, ``'audio'``, or ``'info'``.
        video_id: YouTube video ID.

    Returns:
        - For ``type='info'``: the parsed info dict.
        - For ``type='video'`` / ``'audio'``: the file path string.
        - ``None`` if not cached.
    """
    cache = _read_cache(type=type)
    if video_id not in cache:
        return None
    entry = cache[video_id]["path"]
    if type == "info":
        return json.loads(entry)
    return entry


def write_cache(type: str, video_id: str, data: str | dict) -> None:
    """Append one entry to the download cache.

    Args:
        type: ``'video'``, ``'audio'``, or ``'info'``.
        video_id: YouTube video ID.
        data: File path string, or for ``type='info'`` a dict (auto-serialized to JSON).
    """
    path = json.dumps(data, ensure_ascii=False) if isinstance(data, dict) else data
    with open(CACHE_FILE, "a", encoding="utf-8") as f:
        f.write(f"{type},{video_id},{path}\n")


def extract_video_id(url: str) -> str:
    """Extract YouTube video ID from URL or return as-is."""
    if "youtube.com" in url or "youtu.be" in url:
        if "youtu.be" in url:
            return url.split("/")[-1].split("?")[0]
        import urllib.parse
        parsed = urllib.parse.urlparse(url)
        qs = urllib.parse.parse_qs(parsed.query)
        return qs.get("v", [url])[0]
    return url