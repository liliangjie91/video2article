"""download package — YouTube subtitle API + yt-dlp fallback."""

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