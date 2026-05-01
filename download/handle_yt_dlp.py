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

    # set download options
    ydl_opts = {
        "outtmpl": os.path.join(output_dir, "%(uploader)s/%(upload_date)s_%(id)s/%(id)s.%(ext)s"),
        "quiet": True,
        "no_warnings": True,
    }

    if down_type == "video":
        ydl_opts.update({
            "format": "bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best",
            "merge_output_format": "mp4"
        })
    elif down_type == "audio":
        ydl_opts.update({
            "format": "bestaudio[ext=m4a]/bestaudio/best",
            "postprocessors": [{
                "key": "FFmpegExtractAudio",
                "preferredcodec": "m4a",
            }]
        })
    else:
        raise ValueError(f"Invalid down_type: {down_type}. Must be 'audio' or 'video'.")

    # download the media
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=True)
    res_file = ydl.prepare_filename(info)

    # check for downloaded file
    if os.path.exists(res_file):
        logger.info("Downloaded %s: %s —> %s", down_type, info.get("title", url), res_file)
        return res_file

    raise FileNotFoundError(f"Downloaded file not found for {url} in {output_dir}")
