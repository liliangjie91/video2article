"""Utility shared functions."""

import json
import os
import re

_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_OUTPUT_DIR = os.path.join(_PROJECT_ROOT, "output")


def format_srt_time(seconds: float) -> str:
    """Convert seconds to SRT timestamp HH:MM:SS,mmm."""
    h = int(seconds // 3600)
    m = int((seconds % 3600) // 60)
    s = int(seconds % 60)
    ms = int((seconds - int(seconds)) * 1000)
    return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"


def is_video(file_path: str) -> bool:
    """Simple check if file is a video based on extension."""
    video_exts = {".mp4", ".mov", ".mkv", ".avi", ".flv", ".wmv", ".webm"}
    ext = os.path.splitext(file_path)[1].lower()
    return ext in video_exts


def is_audio(file_path: str) -> bool:
    """Simple check if file is an audio based on extension."""
    audio_exts = {".mp3", ".wav", ".aac", ".flac", ".ogg", ".m4a"}
    ext = os.path.splitext(file_path)[1].lower()
    return ext in audio_exts


def is_subtitle(file_path: str) -> bool:
    """Simple check if file is a subtitle based on extension."""
    subtitle_exts = {".srt", ".vtt", ".ass", ".ssa"}
    ext = os.path.splitext(file_path)[1].lower()
    return ext in subtitle_exts


def detect_input_type(input_str: str) -> str:
    """Detect input type: ``'srt'``, ``'media'``, or ``'url'``."""
    if "youtube.com" in input_str or "youtu.be" in input_str or input_str.startswith("http"):
        return "url"
    ext = os.path.splitext(input_str)[1].lower()
    if ext in (".srt", ".vtt"):
        return "srt"
    if ext in (".mp4", ".mkv", ".m4a", ".wav", ".mp3", ".webm", ".mov", ".avi"):
        return "media"
    return "url"


def extract_json(raw: str) -> str:
    """Strip markdown fences and extract raw JSON string from LLM output."""
    raw = raw.strip()
    if raw.startswith("```"):
        raw = raw.split("\n", 1)[-1]
        if raw.endswith("```"):
            raw = raw[:-3]
        raw = raw.strip()
    return raw


def safe_parse_json(raw: str) -> dict:
    """Parse LLM JSON output with repair attempts for common failures.

    Handles:
    1. Unescaped double quotes inside string values (most common issue)
    2. Smart/curly quotes used instead of straight quotes
    """
    raw = raw.strip()

    # Attempt 1: direct parse
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        pass

    # Attempt 2: escape unescaped double quotes inside string values.
    # Heuristic: `"` between CJK chars or between CJK and Latin/digit
    # are content quotes, not JSON delimiters.
    CJK = r'[\u4e00-\u9fff\u3040-\u30ff\u3000-\u303f\uff00-\uffef]'
    repaired = re.sub(
        rf'({CJK})"({CJK})',
        lambda m: m.group(1) + "\u201c" + m.group(2),
        raw,
    )
    # CJK + " + letter/digit (e.g. 认为"AI)
    repaired = re.sub(
        rf'({CJK})"([a-zA-Z0-9])',
        lambda m: m.group(1) + "\u201c" + m.group(2),
        repaired,
    )
    # letter/digit + " + CJK (e.g. AI"这一)
    repaired = re.sub(
        rf'([a-zA-Z0-9])"({CJK})',
        lambda m: m.group(1) + "\u201d" + m.group(2),
        repaired,
    )
    # CJK + " + Chinese/ASCII punctuation (closing content quote)
    repaired = re.sub(
        rf'({CJK})"([\u3000-\u303f,.!?;:\s\uff00-\uffef])',
        lambda m: m.group(1) + "\u201d" + m.group(2),
        repaired,
    )
    try:
        return json.loads(repaired)
    except json.JSONDecodeError:
        pass

    raise json.JSONDecodeError(
        f"Failed to parse JSON after repair. Preview: {raw[:300]}", raw, 0
    )


def project_dir(filepath: str, output_dir: str | None = None) -> str:
    """Determine BASE project directory for one pipeline.
    1. If output_dir is provided, use it directly.
    2. If input file is under output/, use its parent directory.
    3. Otherwise, create a new directory under output/ named after the input file.
    """
    if output_dir:
        return output_dir

    abs_path = os.path.abspath(filepath)

    if abs_path.startswith(_OUTPUT_DIR) and abs_path != _OUTPUT_DIR:
        return os.path.dirname(abs_path)

    name = os.path.splitext(os.path.basename(filepath))[0]
    return os.path.join(_OUTPUT_DIR, name)
