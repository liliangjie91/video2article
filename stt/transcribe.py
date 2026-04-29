"""Speech to text: 视频/音频 → SRT 字幕"""

import os
import subprocess
import logging
from faster_whisper import WhisperModel
from config import get_config

logger = logging.getLogger(__name__)


def _model_dir() -> str:
    """Resolve whisper model cache directory from config."""
    cfg = get_config()
    path = cfg.get("stt", "model_dir", fallback="models/whisper")
    abspath = os.path.join(os.path.dirname(os.path.dirname(__file__)), path)
    os.makedirs(abspath, exist_ok=True)
    return abspath


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


def _format_srt_time(seconds: float) -> str:
    """Convert seconds to SRT timestamp format HH:MM:SS,mmm."""
    h = int(seconds // 3600)
    m = int((seconds % 3600) // 60)
    s = int(seconds % 60)
    ms = int((seconds - int(seconds)) * 1000)
    return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"


def transcribe(audio_path: str, output_dir: str, model_name: str = "large-v3-turbo") -> str:
    """Transcribe audio to SRT using faster-whisper.

    Uses CTranslate2-optimized inference — runs large models efficiently on CPU.
    Returns path to the generated SRT file.
    """
    os.makedirs(output_dir, exist_ok=True)
    base = os.path.splitext(os.path.basename(audio_path))[0]
    srt_path = os.path.join(output_dir, f"{base}.srt")

    logger.info("Loading faster-whisper model: %s (cache: %s)", model_name, _model_dir())
    model = WhisperModel(model_name, device="cpu", compute_type="int8", download_root=_model_dir())
    logger.info("Transcribing: %s", audio_path)

    segments, info = model.transcribe(audio_path, language="zh", beam_size=5)
    logger.info(
        "Detected language: %s (probability: %.2f)",
        info.language, info.language_probability,
    )

    with open(srt_path, "w", encoding="utf-8") as f:
        for i, seg in enumerate(segments, start=1):
            start = _format_srt_time(seg.start)
            end = _format_srt_time(seg.end)
            f.write(f"{i}\n{start} --> {end}\n{seg.text.strip()}\n\n")

    logger.info("Transcription complete: %s", srt_path)
    return srt_path


def run(video_path: str, model: str = "large-v3-turbo") -> str:
    """Full STT pipeline: video → SRT subtitle. Returns SRT path."""
    tmp_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "tmp", "srt")
    os.makedirs(tmp_dir, exist_ok=True)
    audio_path = extract_audio(video_path, tmp_dir)
    srt_path = transcribe(audio_path, tmp_dir, model)
    return srt_path
