"""Tests for utils/__init__.py — format detection utilities."""

import pytest
from utils import is_video, is_audio, is_subtitle, detect_input_type, format_srt_time


class TestIsVideo:
    @pytest.mark.parametrize(
        "path", ["video.mp4", "movie.mov", "file.mkv", "test.avi", "clip.webm"]
    )
    def test_video_extensions(self, path):
        assert is_video(path) is True

    @pytest.mark.parametrize(
        "path", ["audio.mp3", "text.srt", "doc.txt", "image.png"]
    )
    def test_non_video_extensions(self, path):
        assert is_video(path) is False


class TestIsAudio:
    @pytest.mark.parametrize(
        "path", ["audio.mp3", "sound.wav", "track.m4a", "record.flac", "file.ogg"]
    )
    def test_audio_extensions(self, path):
        assert is_audio(path) is True

    @pytest.mark.parametrize(
        "path", ["video.mp4", "text.srt", "doc.txt"]
    )
    def test_non_audio_extensions(self, path):
        assert is_audio(path) is False


class TestIsSubtitle:
    @pytest.mark.parametrize(
        "path", ["subs.srt", "subs.vtt", "subs.ass", "subs.ssa"]
    )
    def test_subtitle_extensions(self, path):
        assert is_subtitle(path) is True

    @pytest.mark.parametrize(
        "path", ["video.mp4", "audio.mp3", "doc.txt"]
    )
    def test_non_subtitle_extensions(self, path):
        assert is_subtitle(path) is False


class TestDetectInputType:
    @pytest.mark.parametrize(
        "url",
        [
            "https://youtube.com/watch?v=dQw4w9WgXcQ",
            "https://youtu.be/dQw4w9WgXcQ",
            "https://www.youtube.com/watch?v=abc123",
            "https://bilibili.com/video/BV1xx",
        ],
    )
    def test_url(self, url):
        assert detect_input_type(url) == "url"

    def test_bare_video_id_is_url(self):
        assert detect_input_type("dQw4w9WgXcQ") == "url"

    def test_srt_path(self):
        assert detect_input_type("subtitles.srt") == "srt"

    def test_vtt_path(self):
        assert detect_input_type("subtitles.vtt") == "srt"

    @pytest.mark.parametrize(
        "path", ["video.mp4", "audio.m4a", "clip.webm", "sound.wav", "movie.mkv"]
    )
    def test_media_path(self, path):
        assert detect_input_type(path) == "media"

    def test_http_url_no_youtube(self):
        assert detect_input_type("https://example.com/video") == "url"


class TestFormatSrtTime:
    def test_basic(self):
        assert format_srt_time(3661.5) == "01:01:01,500"

    def test_zero(self):
        assert format_srt_time(0) == "00:00:00,000"

    def test_no_milliseconds(self):
        assert format_srt_time(5) == "00:00:05,000"
