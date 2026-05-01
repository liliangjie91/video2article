"""Media download via yt-dlp — fallback when subtitles are unavailable."""

import logging
import os

import yt_dlp

logger = logging.getLogger(__name__)


def download(url: str, output_dir: str, down_type: str = "audio") -> str:
    """Download audio or video from URL using yt-dlp.

    Args:
        url: Video URL.
        output_dir: Output directory.
        down_type: ``"audio"`` (default) or ``"video"``.

    Returns:
        Path to the downloaded file.
    """
    os.makedirs(output_dir, exist_ok=True)

    if down_type == "video":
        ydl_opts = {
            "format": "bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best",
            "outtmpl": os.path.join(output_dir, "%(id)s.%(ext)s"),
            "merge_output_format": "mp4",
            "quiet": True,
            "no_warnings": True,
        }
    else:
        ydl_opts = {
            "format": "bestaudio[ext=m4a]/bestaudio/best",
            "outtmpl": os.path.join(output_dir, "%(id)s.%(ext)s"),
            "postprocessors": [{
                "key": "FFmpegExtractAudio",
                "preferredcodec": "m4a",
            }],
            "quiet": True,
            "no_warnings": True,
        }

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=True)

    title = info.get("title", url)
    base = os.path.join(output_dir, info["id"])

    if down_type == "video":
        for ext in ("mp4", "mkv", "webm"):
            path = f"{base}.{ext}"
            if os.path.exists(path):
                logger.info("Downloaded video: %s —> %s", title, path)
                return path
        raise FileNotFoundError(f"Downloaded file not found for {url} in {output_dir}")
    else:
        path = f"{base}.m4a"
        logger.info("Downloaded audio: %s —> %s", title, path)
        return path
