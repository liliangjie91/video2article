"""Media download via yt-dlp — fallback when subtitles are unavailable."""

import logging
import os

import yt_dlp
from download import extract_video_id
logger = logging.getLogger(__name__)

CACHE_FILE = os.path.join(os.path.dirname(__file__), ".download.cache")


def read_cache() -> dict[str, str]:
    """Read download cache. Returns dict of video_id → output_path."""
    if not os.path.exists(CACHE_FILE):
        return {}
    cache: dict[str, str] = {}
    with open(CACHE_FILE, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            parts = line.split(",", 1)
            if len(parts) == 2:
                vid, path = parts
                # Skip stale entries where the file no longer exists
                if os.path.exists(path):
                    cache[vid] = path
    return cache


def _write_cache(video_id: str, path: str) -> None:
    """Append one entry to the download cache."""
    with open(CACHE_FILE, "a", encoding="utf-8") as f:
        f.write(f"{video_id},{path}\n")


def _build_ydl_opts(output_dir: str, down_type: str) -> dict:
    """Build yt-dlp options for the given download type."""
    opts = {
        "outtmpl": os.path.join(output_dir, "%(uploader)s/%(upload_date)s_%(id)s/%(id)s.%(ext)s"),
        "quiet": True,
        "no_warnings": True,
    }

    if down_type == "video":
        opts.update({
            "format": "bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best",
            "merge_output_format": "mp4",
        })
    elif down_type == "audio":
        opts.update({
            "format": "bestaudio/best",
        })
    else:
        raise ValueError(f"Invalid down_type: {down_type}. Must be 'audio' or 'video'.")

    return opts


def download(url: str, output_dir: str = "../output", down_type: str = "audio") -> str:
    """Download audio or video from URL using yt-dlp.

    Cache-aware (per output_dir): checks ``.download.cache`` before fetching metadata.

    Args:
        url: Video URL.
        output_dir: Output directory.
        down_type: ``"audio"`` (default) or ``"video"``.

    Returns:
        Path to the downloaded file.
    """
    os.makedirs(output_dir, exist_ok=True)

    # Check global cache by video_id (zero network)
    vid = extract_video_id(url)
    if vid:
        cached = read_cache()
        if vid in cached:
            cached_path = cached[vid]
            if os.path.exists(cached_path):
                logger.info("Cache hit: %s —> %s", vid, cached_path)
                return cached_path
            logger.info("Stale cache entry for %s, re-downloading...", vid)

    # Build yt-dlp options and download
    ydl_opts = _build_ydl_opts(output_dir, down_type)

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=True)
    res_file = ydl.prepare_filename(info)

    # Verify download success
    if not os.path.exists(res_file):
        raise FileNotFoundError(f"Downloaded file not found for {url} in {output_dir}")
    logger.info("Downloaded %s: %s —> %s", down_type, info.get("title", url), res_file)

    # Update global cache
    actual_id = info.get("id") or vid
    if actual_id:
        _write_cache(actual_id, res_file)

    return res_file
