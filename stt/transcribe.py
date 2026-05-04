"""Speech to text: 视频/音频 → SRT 字幕"""

import os
import subprocess
import logging
from faster_whisper import WhisperModel
from config import get_config
from tqdm import tqdm
from utils import format_srt_time, is_video, is_audio

logger = logging.getLogger(__name__)


def _model_dir() -> str:
    """Resolve whisper model cache directory from config.

    Priority: WHISPER_MODEL_DIR env var > config.ini [stt] model_dir > models/whisper
    """
    env_path = os.environ.get("WHISPER_MODEL_DIR")
    if env_path:
        abspath = os.path.join(os.path.dirname(os.path.dirname(__file__)), env_path)
        os.makedirs(abspath, exist_ok=True)
        return abspath

    cfg = get_config()
    path = cfg.get("stt", "model_dir", fallback="models/whisper")
    abspath = os.path.join(os.path.dirname(os.path.dirname(__file__)), path)
    os.makedirs(abspath, exist_ok=True)
    return abspath


def extract_audio(video_audio_path: str) -> str:
    """Extract audio track from video as WAV using ffmpeg."""
    
    base = os.path.splitext(os.path.basename(video_audio_path))[0]
    audio_path = os.path.join(os.path.dirname(video_audio_path), f"{base}.wav")
    if os.path.exists(audio_path):
        logger.info("Audio already extracted, skipping: %s", audio_path)
        return audio_path
    cmd = [
        "ffmpeg", "-y",
        "-i", video_audio_path,
        "-vn", "-acodec", "pcm_s16le", "-ar", "16000", "-ac", "1",
        audio_path,
    ]
    subprocess.run(cmd, capture_output=True, check=True)
    logger.info("Audio extracted: %s", audio_path)
    return audio_path


def transcribe(audio_path: str, model_name: str = "large-v3-turbo") -> str:
    """Transcribe audio to SRT using faster-whisper.

    Uses CTranslate2-optimized inference — runs large models efficiently on CPU.
    Returns path to the generated SRT file.
    """
    
    base = os.path.splitext(os.path.basename(audio_path))[0]
    srt_path = os.path.join(os.path.dirname(audio_path), f"{base}.srt")
    if os.path.exists(srt_path):
        logger.info("SRT already transcribed, skipping transcription: %s", srt_path)
        return srt_path
    logger.info("Loading faster-whisper model: %s (cache: %s)", model_name, _model_dir())
    with tqdm(total=1, desc="Loading model", unit="model", leave=False, disable=None) as pbar:
        model = WhisperModel(model_name, device="cpu", compute_type="int8", download_root=_model_dir())
        pbar.update(1)

    logger.info("Transcribing: %s", audio_path)
    segments, info = model.transcribe(audio_path, language="zh", beam_size=5)
    logger.info(
        "Detected language: %s (probability: %.2f)",
        info.language, info.language_probability,
    )

    total_duration = info.duration
    with open(srt_path, "w", encoding="utf-8") as f:
        with tqdm(total=100, desc="Transcribing", unit="%", leave=False) as pbar:
            last_pct = 0
            for i, seg in enumerate(segments, start=1):
                start = format_srt_time(seg.start)
                end = format_srt_time(seg.end)
                f.write(f"{i}\n{start} --> {end}\n{seg.text.strip()}\n\n")

                pct = min(int((seg.end / total_duration) * 100), 100)
                if pct > last_pct:
                    pbar.update(pct - last_pct)
                    last_pct = pct

    logger.info("Transcription complete: %s", srt_path)
    return srt_path


def run(video_audio_path: str, model: str = "large-v3-turbo") -> str:
    """Full STT pipeline: video/audio → SRT subtitle. Returns SRT path."""
    
    if is_video(video_audio_path):
        logger.info("Input is video, extracting audio...")
        video_audio_path = extract_audio(video_audio_path)
    elif is_audio(video_audio_path):
        logger.info("Input is audio, skipping extraction.")
    else:
        raise ValueError(f"Unsupported input format for STT: {video_audio_path}")

    srt_path = transcribe(video_audio_path, model)
    return srt_path
