"""Tests for utils/__init__.py — format detection utilities."""

import json
import pytest
from utils import is_video, is_audio, is_subtitle, detect_input_type, format_srt_time, safe_parse_json


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


class TestSafeParseJson:
    def test_valid_json(self):
        data = safe_parse_json('{"a": 1, "b": "hello"}')
        assert data == {"a": 1, "b": "hello"}

    def test_smart_quotes_in_values(self):
        """Curly quotes inside string values are valid and pass through."""
        raw = '{"a": "value with \u201csmart\u201d quotes"}'
        data = safe_parse_json(raw)

    def test_unescaped_quotes_in_chinese(self):
        """Double quotes between CJK chars should be auto-repaired."""
        raw = '{"text": "他说"很好"然后继续"}'
        data = safe_parse_json(raw)
        # Inner quotes replaced with curly quotes to make JSON valid
        assert "\u201c" in data["text"]
        assert data["text"].startswith("他说")
        assert data["text"].endswith("然后继续")

    def test_plain_text_with_curly_quotes_passes_through(self):
        """Smart/curly quotes inside string values should be left as-is."""
        raw = '{"key": "value with \u201cquote\u201d inside"}'
        data = safe_parse_json(raw)
        assert data == {"key": "value with \u201cquote\u201d inside"}


    def test_llm_output_with_embedded_quotes(self):
        """Realistic LLM output: Chinese text with quoted terms inside JSON."""
        raw = '{"core_summary": "作者认为"AI会取代人类"这一说法过于夸张"}'
        data = safe_parse_json(raw)
        assert '“' in data["core_summary"]
        assert "AI" in data["core_summary"]
    def test_raises_on_truly_invalid(self):
        with pytest.raises(json.JSONDecodeError):
            safe_parse_json("{not json at all}")
