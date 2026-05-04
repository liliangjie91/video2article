"""YouTube subtitle/channel features via youtube-transcript-api + YouTube Data API."""

import logging
import os
from typing import Optional

from download import YOUTUBE_API_BASE, YOUTUBE_API_KEY, extract_video_id, get_cache, write_cache
from utils import format_srt_time
from youtube_transcript_api import YouTubeTranscriptApi
from youtube_transcript_api._errors import (
    TranscriptsDisabled,
    NoTranscriptFound,
    VideoUnavailable,
)

logger = logging.getLogger(__name__)


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
        f'{video_info.get("publish_date", "unknown_date")}_{video_id}',
    )
    os.makedirs(output_dir, exist_ok=True)
    srt_path = os.path.join(output_dir, f"{video_id}.srt")
    if os.path.exists(srt_path):
        logger.info("SRT already exists, skipping: %s", srt_path)
        return srt_path

    available_transcripts = video_info.get("transcript_lang_code", "NOKEY")
    # NOAVAILABLE is a special marker meaning we already probed and found no transcripts, so skip trying again
    if available_transcripts == "NOAVAILABLE":
        logger.info("No transcripts available for %s", video_id)
        return None
    # Fetch transcript
    ## Try to fetch transcript
    ytt_api = YouTubeTranscriptApi()
    default_langs = ["zh", "zh-Hans", "zh-Hant", "zh-CN", "zh-TW", "zh-HK", "en"] + available_transcripts.split(';')
    try:
        transcript = ytt_api.fetch(video_id, languages=default_langs if not language else [language] + default_langs)
    except (NoTranscriptFound, TranscriptsDisabled, VideoUnavailable) as e:
        logger.info("No usable transcript found for: %s", video_id)
        return None
    except Exception as e:
        logger.warning("Error fetching transcript for %s: %s", video_id, e)
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
            "channel_title": snippet.get("channelTitle", ""),
            "published_at": snippet.get("publishedAt", "")[:10],
            "video_id": resource.get("videoId", ""),
            "title": snippet.get("title", ""),
        })

    return items


def get_video_info_from_id(video_id: str) -> Optional[dict]:
    """Get basic video info (title, channel) from YouTube URL using Data API."""
    cached = get_cache("info", video_id)
    if cached:
        logger.info("Cache hit: %s", '; '.join([v for v in cached.values()]))
        return cached

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
    result["channel_title"] = result.pop("channelTitle")

    # get transcript info
    transcript_info = _list_transcripts(video_id)
    result.update(transcript_info)
    # logger.info("Fetched video info: %s", '; '.join([v for v in result.values()]))

    logger.info("Fetched video info done")
    write_cache("info", video_id, result)
    return result

def _list_transcripts(url: str) -> dict:
    """Probe available subtitles for a YouTube video.

    Returns list of {language, language_code, is_generated} or None on failure.
    """
    video_id = extract_video_id(url)
    try:
        transcript_list = YouTubeTranscriptApi().list(video_id)
    except (VideoUnavailable, TranscriptsDisabled, NoTranscriptFound) as e:
        logger.info("No transcripts available for %s: %s", video_id, e)
        return {"transcript_lang_code": "NOAVAILABLE"}
    except Exception as e:
        logger.warning("Error fetching transcripts for %s: %s", video_id, e)
        return {"transcript_lang_code": "NOAVAILABLE"}
    
    trans_lan_code_set = set()
    for t in transcript_list:
        trans_lan_code_set.add(t.language_code)
    
    logline = ';'.join(trans_lan_code_set)
    logger.info("Available transcripts for %s: %s", video_id, logline)
    return {"transcript_lang_code": logline}

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
