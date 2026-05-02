"""Utility shared functions."""


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