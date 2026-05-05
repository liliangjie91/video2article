"""download package — YouTube subtitle API + yt-dlp fallback."""

import logging
import os

from dotenv import load_dotenv

logger = logging.getLogger(__name__)

# Make .env vars available to submodules at import time
load_dotenv()

YOUTUBE_API_BASE = "https://www.googleapis.com/youtube/v3"
YOUTUBE_API_KEY = os.getenv("YOUTUBE_API_KEY")

CACHE_FILE = os.path.join(os.path.dirname(__file__), ".download.cache")
CACHE_TYPES = frozenset({"video", "audio", "info"})

# Known non-YouTube platforms that yt-dlp can handle directly
_KNOWN_NON_YOUTUBE = {"bilibili.com", "b23.tv", "nicovideo.jp", "vimeo.com"}
