"""YouTube subtitle/channel features via youtube-transcript-api + YouTube Data API."""

import logging
import os
import re
from typing import Optional

from youtube_transcript_api import YouTubeTranscriptApi
from youtube_transcript_api._errors import (
    TranscriptsDisabled,
    NoTranscriptFound,
    VideoUnavailable,
)

logger = logging.getLogger(__name__)


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


def _format_srt_time(seconds: float) -> str:
    """Convert seconds to SRT timestamp HH:MM:SS,mmm."""
    h = int(seconds // 3600)
    m = int((seconds % 3600) // 60)
    s = int(seconds % 60)
    ms = int((seconds - int(seconds)) * 1000)
    return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"


def list_transcripts(url: str) -> Optional[list[dict]]:
    """Probe available subtitles for a YouTube video.

    Returns list of {language, language_code, is_generated} or None on failure.
    """
    video_id = extract_video_id(url)
    try:
        transcript_list = YouTubeTranscriptApi().list(video_id)
    except (VideoUnavailable, TranscriptsDisabled, NoTranscriptFound) as e:
        logger.info("No transcripts available for %s: %s", video_id, e)
        return None

    results = []
    for t in transcript_list:
        results.append({
            "language": t.language,
            "language_code": t.language_code,
            "is_generated": t.is_generated,
        })
    return results


def get_subtitle_srt(url: str, output_dir: str, language: Optional[str] = "zh") -> Optional[str]:
    """Fetch YouTube subtitles and save as SRT file.

    Tries the preferred language first; falls back to any available transcript.

    Args:
        url: YouTube video URL or video ID.
        output_dir: Directory to save the SRT file.
        language: Preferred language code (default zh). Pass None for auto.

    Returns:
        Path to the SRT file, or None if no subtitles available.
    """
    video_id = extract_video_id(url)
    os.makedirs(output_dir, exist_ok=True)
    ytt_api = YouTubeTranscriptApi()

    try:
        transcript_list = ytt_api.list(video_id)
    except VideoUnavailable:
        logger.warning("Video unavailable: %s", video_id)
        return None
    except TranscriptsDisabled:
        logger.info("Transcripts disabled for: %s", video_id)
        return None

    # Try to fetch transcript
    try:
        if language:
            transcript = transcript_list.find_transcript([language]).fetch()
        else:
            transcript = ytt_api.fetch(video_id)
    except (NoTranscriptFound, TranscriptsDisabled):
        # Fallback: try any available transcript
        try:
            transcript = transcript_list.find_transcript(
                [t.language_code for t in transcript_list]
            ).fetch()
        except (NoTranscriptFound, TranscriptsDisabled, StopIteration):
            logger.info("No usable transcript found for: %s", video_id)
            return None

    srt_path = os.path.join(output_dir, f"{video_id}.srt")
    with open(srt_path, "w", encoding="utf-8") as f:
        for i, snippet in enumerate(transcript, start=1):
            start = _format_srt_time(snippet.start)
            end = _format_srt_time(snippet.start + snippet.duration)
            f.write(f"{i}\n{start} --> {end}\n{snippet.text.strip()}\n\n")

    logger.info("Subtitles saved: %s", srt_path)
    return srt_path


# ── YouTube Data API (optional, requires YOUTUBE_API_KEY in .env) ──────

def _youtube_api_key() -> Optional[str]:
    """Get YouTube Data API key from environment."""
    from dotenv import load_dotenv
    load_dotenv()
    return os.getenv("YOUTUBE_API_KEY")


YOUTUBE_API_BASE = "https://www.googleapis.com/youtube/v3"


def get_channel_uploads(identifier: str, max_results: int = 5) -> Optional[list[dict]]:
    """List recent uploads from a YouTube channel.

    Args:
        identifier: Channel handle (@TED), channel ID (UCxxx), or channel URL.
        max_results: Number of videos to return (max 50).

    Returns:
        List of {video_id, title, published_at, channel_title}, or None if API key missing.
    """
    api_key = _youtube_api_key()
    if not api_key:
        logger.warning("YOUTUBE_API_KEY not set — skipping channel uploads")
        return None

    import requests

    # Resolve channel
    channel_value, id_type = _extract_channel_id(identifier)
    params = {"part": "contentDetails", "key": api_key}
    if id_type == "id":
        params["id"] = channel_value
    else:
        params["forHandle"] = channel_value

    resp = requests.get(f"{YOUTUBE_API_BASE}/channels", params=params, timeout=15)
    resp.raise_for_status()
    channel_data = resp.json()
    if not channel_data.get("items"):
        logger.warning("Channel not found: %s", identifier)
        return None

    uploads_id = channel_data["items"][0]["contentDetails"]["relatedPlaylists"]["uploads"]

    # Fetch uploads playlist
    params = {
        "part": "snippet",
        "playlistId": uploads_id,
        "maxResults": min(max_results, 50),
        "key": api_key,
    }
    resp = requests.get(f"{YOUTUBE_API_BASE}/playlistItems", params=params, timeout=15)
    resp.raise_for_status()
    playlist_data = resp.json()

    items = []
    for item in playlist_data.get("items", []):
        snippet = item["snippet"]
        resource = snippet.get("resourceId", {})
        items.append({
            "video_id": resource.get("videoId", ""),
            "title": snippet.get("title", ""),
            "published_at": snippet.get("publishedAt", ""),
            "channel_title": snippet.get("channelTitle", ""),
        })

    return items


def _extract_channel_id(input_str: str) -> tuple[str, str]:
    """Extract channel identifier and type from various formats."""
    input_str = input_str.strip()

    if input_str.startswith("UC") and len(input_str) == 24:
        return input_str, "id"
    if input_str.startswith("@"):
        return input_str, "handle"
    if "/channel/" in input_str:
        return input_str.split("/channel/")[-1].split("/")[0], "id"
    if "/@" in input_str:
        handle = input_str.split("/@")[-1].split("/")[0]
        if not handle.startswith("@"):
            handle = "@" + handle
        return handle, "handle"

    return input_str, "handle"
