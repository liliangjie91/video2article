"""Tests for download/__init__.py — cache logic + video ID extraction."""

import pytest
from download import write_cache, get_cache, extract_video_id, is_youtube_url


class TestCache:
    def test_write_and_read_video(self, tmp_path, monkeypatch):
        monkeypatch.setattr("download.CACHE_FILE", str(tmp_path / ".download.cache"))
        video_path = tmp_path / "video.mp4"
        video_path.write_text("dummy")
        write_cache("video", "abc123", str(video_path))
        result = get_cache("video", "abc123")
        assert result == str(video_path)

    def test_write_and_read_audio(self, tmp_path, monkeypatch):
        monkeypatch.setattr("download.CACHE_FILE", str(tmp_path / ".download.cache"))
        audio_path = tmp_path / "audio.m4a"
        audio_path.write_text("dummy")
        write_cache("audio", "abc123", str(audio_path))
        result = get_cache("audio", "abc123")
        assert result == str(audio_path)

    def test_write_and_read_info(self, tmp_path, monkeypatch):
        monkeypatch.setattr("download.CACHE_FILE", str(tmp_path / ".download.cache"))
        info = {"title": "Test Video", "channel": "Test Channel"}
        write_cache("info", "abc123", info)
        result = get_cache("info", "abc123")
        assert result == {"title": "Test Video", "channel": "Test Channel"}

    def test_skips_stale_file_entry(self, tmp_path, monkeypatch):
        """Entry whose file no longer exists should be skipped on read."""
        monkeypatch.setattr("download.CACHE_FILE", str(tmp_path / ".download.cache"))
        write_cache("video", "abc123", "/nonexistent/path.mp4")
        assert get_cache("video", "abc123") is None

    def test_get_cache_missing(self, tmp_path, monkeypatch):
        monkeypatch.setattr("download.CACHE_FILE", str(tmp_path / ".download.cache"))
        assert get_cache("video", "nonexistent") is None

    def test_get_cache_wrong_type(self, tmp_path, monkeypatch):
        monkeypatch.setattr("download.CACHE_FILE", str(tmp_path / ".download.cache"))
        video_path = tmp_path / "video.mp4"
        video_path.write_text("dummy")
        write_cache("video", "abc123", str(video_path))
        assert get_cache("audio", "abc123") is None

    def test_cache_file_not_exists(self, tmp_path, monkeypatch):
        monkeypatch.setattr("download.CACHE_FILE", str(tmp_path / ".nonexistent"))
        assert get_cache("video", "anything") is None

    def test_multiple_entries(self, tmp_path, monkeypatch):
        monkeypatch.setattr("download.CACHE_FILE", str(tmp_path / ".download.cache"))
        vid1_path = tmp_path / "1.mp4"
        vid2_path = tmp_path / "2.m4a"
        vid1_path.write_text("dummy")
        vid2_path.write_text("dummy")
        write_cache("video", "vid1", str(vid1_path))
        write_cache("audio", "vid2", str(vid2_path))
        assert get_cache("video", "vid1") == str(vid1_path)
        assert get_cache("audio", "vid2") == str(vid2_path)
        assert get_cache("video", "vid2") is None


class TestExtractVideoID:
    def test_youtube_watch_url(self):
        assert extract_video_id("https://youtube.com/watch?v=dQw4w9WgXcQ") == "dQw4w9WgXcQ"

    def test_youtube_watch_with_params(self):
        assert (
            extract_video_id("https://youtube.com/watch?v=abc123&t=30s") == "abc123"
        )

    def test_youtu_be_url(self):
        assert extract_video_id("https://youtu.be/dQw4w9WgXcQ") == "dQw4w9WgXcQ"

    def test_non_youtube_url_strips_query(self):
        assert (
            extract_video_id("https://bilibili.com/video/BV1xx?p=2")
            == "https://bilibili.com/video/BV1xx"
        )


class TestIsYoutubeUrl:
    @pytest.mark.parametrize(
        "url",
        [
            "https://youtube.com/watch?v=abc123",
            "https://www.youtube.com/watch?v=abc123",
            "https://youtu.be/abc123",
            "dQw4w9WgXcQ",  # bare video ID
        ],
    )
    def test_youtube_urls(self, url):
        assert is_youtube_url(url) is True

    @pytest.mark.parametrize(
        "url",
        [
            "https://bilibili.com/video/BV1xx",
            "https://b23.tv/abc123",
            "https://nicovideo.jp/watch/sm123",
            "https://vimeo.com/12345",
        ],
    )
    def test_non_youtube_urls(self, url):
        assert is_youtube_url(url) is False
