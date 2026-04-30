"""Media download via yt-dlp — fallback when subtitles are unavailable."""

import logging
import os

import yt_dlp

logger = logging.getLogger(__name__)


def download_audio(url: str, output_dir: str) -> str:
    """Download audio from URL using yt-dlp. Returns path to audio file."""
    os.makedirs(output_dir, exist_ok=True)

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

    # After postprocessing the file is always .m4a
    title = info.get("title", url)
    path = os.path.join(output_dir, f"{info['id']}.m4a")
    logger.info("Downloaded audio: %s —> %s", title, path)
    return path


def download_video(url: str, output_dir: str) -> str:
    """Download video from URL using yt-dlp. Returns path to video file."""
    os.makedirs(output_dir, exist_ok=True)

    ydl_opts = {
        "format": "bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best",
        "outtmpl": os.path.join(output_dir, "%(id)s.%(ext)s"),
        "merge_output_format": "mp4",
        "quiet": True,
        "no_warnings": True,
    }

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=True)

    title = info.get("title", url)
    base = os.path.join(output_dir, info["id"])

    # Find the actual downloaded file (yt-dlp may produce mp4/mkv)
    for ext in ("mp4", "mkv", "webm"):
        path = f"{base}.{ext}"
        if os.path.exists(path):
            logger.info("Downloaded video: %s —> %s", title, path)
            return path

    raise FileNotFoundError(f"Downloaded file not found for {url} in {output_dir}")
