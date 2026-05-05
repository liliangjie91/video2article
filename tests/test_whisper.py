"""Tests for stt/transcribe.py — STT pipeline (mock whisper + ffmpeg)."""

import os
import pytest
from stt.transcribe import run, extract_audio, transcribe, _model_dir


class TestRun:
    def test_video_input_extracts_audio_then_transcribes(self, mocker):
        mock_extract = mocker.patch("stt.transcribe.extract_audio", return_value="/out/audio.wav")
        mock_transcribe = mocker.patch("stt.transcribe.transcribe", return_value="/out/audio.srt")
        mocker.patch("stt.transcribe.is_video", return_value=True)
        mocker.patch("stt.transcribe.is_audio", return_value=False)

        result = run("/path/video.mp4", model="base")

        assert result == "/out/audio.srt"
        mock_extract.assert_called_once_with("/path/video.mp4")
        mock_transcribe.assert_called_once_with("/out/audio.wav", "base")

    def test_audio_input_skips_extraction(self, mocker):
        mock_extract = mocker.patch("stt.transcribe.extract_audio")
        mock_transcribe = mocker.patch("stt.transcribe.transcribe", return_value="/out/audio.srt")
        mocker.patch("stt.transcribe.is_video", return_value=False)
        mocker.patch("stt.transcribe.is_audio", return_value=True)

        result = run("/path/audio.m4a", model="base")

        assert result == "/out/audio.srt"
        mock_extract.assert_not_called()

    def test_unsupported_input_raises(self, mocker):
        mocker.patch("stt.transcribe.is_video", return_value=False)
        mocker.patch("stt.transcribe.is_audio", return_value=False)

        with pytest.raises(ValueError, match="Unsupported input format"):
            run("/path/file.txt")


class TestExtractAudio:
    def test_skips_if_wav_exists(self, mocker):
        mocker.patch("os.path.exists", return_value=True)
        mock_run = mocker.patch("subprocess.run")

        result = extract_audio("/dir/video.mp4")

        assert result == "/dir/video.wav"
        mock_run.assert_not_called()

    def test_runs_ffmpeg_if_no_wav(self, mocker):
        mocker.patch("os.path.exists", return_value=False)
        mock_run = mocker.patch("subprocess.run")

        result = extract_audio("/dir/video.mp4")

        assert result == "/dir/video.wav"
        mock_run.assert_called_once()
        cmd = mock_run.call_args[0][0]
        assert "ffmpeg" in cmd[0]
        assert "-i" in cmd
        assert "/dir/video.mp4" in cmd


class TestModelDir:
    def test_uses_env_var_when_set(self, mocker):
        mocker.patch.dict(os.environ, {"WHISPER_MODEL_DIR": "/custom/path"})
        mocker.patch("os.makedirs")

        result = _model_dir()

        assert "custom" in result or "/custom/path" in result


# ── Manual integration test runner ─────────────────────────────
# Run: python tests/test_whisper.py <video_or_audio>
#
# This bypasses mocking and calls real faster-whisper + ffmpeg.
# Requires ffmpeg installed and sufficient RAM for the model.

if __name__ == "__main__":
    import sys
    import logging

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )

    if len(sys.argv) < 2:
        print("用法: python tests/test_whisper.py <video_or_audio> [model_name]")
        sys.exit(1)

    input_path = sys.argv[1]
    model = sys.argv[2] if len(sys.argv) > 2 else "large-v3-turbo"
    out_dir = "tmp/test_whisper"
    os.makedirs(out_dir, exist_ok=True)

    from stt.transcribe import _model_dir as get_model_dir

    print(f"Model cache: {get_model_dir()}")
    srt_path = run(input_path, model)
    print(f"\n完成！SRT: {srt_path}")

    with open(srt_path, encoding="utf-8") as f:
        lines = f.read().splitlines()[:15]
    print("\n--- 前几条字幕 ---")
    print("\n".join(lines))
