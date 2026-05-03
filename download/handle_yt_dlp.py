"""Media download via yt-dlp — fallback when subtitles are unavailable."""

import logging
import os

import yt_dlp
from download import extract_video_id, get_cache, write_cache
logger = logging.getLogger(__name__)


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
            "format": "bestaudio[ext=m4a]/best",
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
    default_output = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "output"))
    output_dir = output_dir or default_output
    os.makedirs(output_dir, exist_ok=True)

    # Check cache by video_id (zero network)
    vid = extract_video_id(url)
    if vid:
        cached_path = get_cache(type=down_type, video_id=vid)
        if cached_path and os.path.exists(cached_path):
            logger.info("Cache hit (%s): %s —> %s", down_type, vid, cached_path)
            return cached_path

    # Build yt-dlp options and download
    ydl_opts = _build_ydl_opts(output_dir, down_type)

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        logger.info("Downloading %s via yt-dlp: %s \n using download opts: \n %s", down_type, url, ydl_opts)
        info = ydl.extract_info(url, download=True)
    res_file = ydl.prepare_filename(info)

    # Verify download success
    if not os.path.exists(res_file):
        raise FileNotFoundError(f"Downloaded file not found for {url} in {output_dir}")
    logger.info("Downloaded %s: %s —> %s", down_type, info.get("title", url), res_file)

    # Update cache
    actual_id = info.get("id") or vid
    if actual_id:
        write_cache(down_type, actual_id, res_file)

    return res_file
