"""Speech to text: 视频/音频 → SRT 字幕"""

import os
import subprocess
import logging

logger = logging.getLogger(__name__)


def extract_audio(video_path: str, output_dir: str) -> str:
    """Extract audio track from video as WAV using ffmpeg."""
    os.makedirs(output_dir, exist_ok=True)
    audio_path = os.path.join(output_dir, "audio.wav")
    cmd = [
        "ffmpeg", "-y",
        "-i", video_path,
        "-vn", "-acodec", "pcm_s16le", "-ar", "16000", "-ac", "1",
        audio_path,
    ]
    subprocess.run(cmd, capture_output=True, check=True)
    logger.info("Audio extracted: %s", audio_path)
    return audio_path


def transcribe_with_whisper(audio_path: str, output_dir: str, model: str = "base") -> str:
    """Run whisper to transcribe audio to SRT. Requires `whisper` installed."""
    os.makedirs(output_dir, exist_ok=True)
    cmd = [
        "whisper", audio_path,
        "--model", model,
        "--output_format", "srt",
        "--output_dir", output_dir,
    ]
    subprocess.run(cmd, capture_output=True, check=True)
    # whisper names output after the input filename
    srt_path = os.path.join(output_dir, "audio.srt")
    logger.info("Transcription complete: %s", srt_path)
    return srt_path


def run(video_path: str, output_dir: str, model: str = "base") -> str:
    """Full STT pipeline: video → SRT subtitle. Returns SRT path."""
    os.makedirs(output_dir, exist_ok=True)
    audio_path = extract_audio(video_path, output_dir)
    srt_path = transcribe_with_whisper(audio_path, output_dir, model)
    # Rename to canonical name
    target = os.path.join(output_dir, "00_subtitle.srt")
    if srt_path != target:
        os.rename(srt_path, target)
    return target
