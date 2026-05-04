"""Utility shared functions."""

import os

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
