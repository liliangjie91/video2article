"""YouTube subtitle/channel features via youtube-transcript-api + YouTube Data API."""

import logging
import os
from typing import Optional

from download import YOUTUBE_API_BASE, YOUTUBE_API_KEY, extract_video_id
from utils import format_srt_time
from youtube_transcript_api import YouTubeTranscriptApi
from youtube_transcript_api._errors import (
    TranscriptsDisabled,
    NoTranscriptFound,
    VideoUnavailable,
)

logger = logging.getLogger(__name__)


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
    # Extract video ID and info for naming & get result path
    video_id = extract_video_id(url)
    video_info = get_video_info_from_id(video_id)
    if not video_info:
        video_info = {}

    output_dir = os.path.join(
        output_dir,
        video_info.get("channel_title", "unknown_channel"),
        f"{video_info.get("publish_date", "unknown_date")}_{video_id}",
    )
    os.makedirs(output_dir, exist_ok=True)
    srt_path = os.path.join(output_dir, f"{video_id}.srt")
    if os.path.exists(srt_path):
        logger.info("SRT already exists, skipping: %s", srt_path)
        return srt_path

    # Fetch transcript
    ## list available transcripts to check for preferred language
    ytt_api = YouTubeTranscriptApi()

    try:
        transcript_list = ytt_api.list(video_id)
    except VideoUnavailable:
        logger.warning("Video unavailable: %s", video_id)
        return None
    except TranscriptsDisabled:
        logger.info("Transcripts disabled for: %s", video_id)
        return None

    ## Try to fetch transcript
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

    ## Save as SRT
    with open(srt_path, "w", encoding="utf-8") as f:
        for i, snippet in enumerate(transcript, start=1):
            start = format_srt_time(snippet.start)
            end = format_srt_time(snippet.start + snippet.duration)
            f.write(f"{i}\n{start} --> {end}\n{snippet.text.strip()}\n\n")

    logger.info("Subtitles saved: %s", srt_path)
    return srt_path


# ── YouTube Data API (optional, requires YOUTUBE_API_KEY in .env) ──────


def get_channel_uploads(identifier: str, max_results: int = 5) -> Optional[list[dict]]:
    """List recent uploads from a YouTube channel.

    Args:
        identifier: Channel handle (@TED), channel ID (UCxxx), or channel URL.
        max_results: Number of videos to return (max 50).

    Returns:
        List of {title, channel_title, video_id, published_at}, or None if API key missing.
    """
    api_key = YOUTUBE_API_KEY
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
            "title": snippet.get("title", ""),
            "channel_title": snippet.get("channelTitle", ""),
            "video_id": resource.get("videoId", ""),
            "published_at": snippet.get("publishedAt", ""),
        })

    return items


def get_video_info_from_id(video_id: str) -> Optional[dict]:
    """Get basic video info (title, channel) from YouTube URL using Data API."""
    api_key = YOUTUBE_API_KEY
    if not api_key:
        logger.warning("YOUTUBE_API_KEY not set — cannot fetch video info")
        return None
    import requests
    fields = ["title", "channelTitle", "publishedAt"]
    params_video = {"part": "snippet", "key": api_key, "id": video_id}
    resp_video = requests.get(f"{YOUTUBE_API_BASE}/videos", params=params_video, timeout=15)
    resp_video.raise_for_status()
    videos_info = resp_video.json()
    if not videos_info.get("items"):
        logger.warning("Video not found: %s", video_id)
        return None
    result = {k: videos_info.get("items")[0].get("snippet", {}).get(k, "") for k in fields}
    result["video_id"] = video_id
    published = result.pop("publishedAt")
    result["publish_date"] = published[:10].replace("-", "")
    return result


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
