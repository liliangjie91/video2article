"""Tests for utils/parser.py — subtitle parsing (no mock, pure IO)."""

import pytest
from utils.parser import (
    parse_srt,
    parse_vtt,
    parse_simple,
    parse,
    to_text,
    format_timestamp,
    _parse_hhmmss,
)


class TestParseHHMMSS:
    def test_basic(self):
        assert _parse_hhmmss("01:02:03") == 3723000

    def test_with_milliseconds(self):
        assert _parse_hhmmss("01:02:03.456") == 3723456

    def test_with_comma_milliseconds(self):
        assert _parse_hhmmss("01:02:03,456") == 3723456

    def test_zero(self):
        assert _parse_hhmmss("00:00:00") == 0

    def test_invalid_returns_zero(self):
        assert _parse_hhmmss("not-a-time") == 0


class TestParseSRT:
    def test_normal(self, tmp_path, sample_srt):
        p = tmp_path / "test.srt"
        p.write_text(sample_srt, encoding="utf-8")
        result = parse_srt(str(p))
        assert len(result) == 3

        assert result[0] == (1000, 4000, "Hello world, this is a test.")
        assert result[1] == (5000, 8500, "Second subtitle line here.")
        assert result[2] == (9000, 12000, "Third and final line.")

    def test_dot_timestamps(self, tmp_path, sample_srt_dot):
        p = tmp_path / "test.srt"
        p.write_text(sample_srt_dot, encoding="utf-8")
        result = parse_srt(str(p))
        assert len(result) == 1
        assert result[0] == (1000, 4000, "Dot timestamp line.")

    def test_empty_file(self, tmp_path):
        p = tmp_path / "empty.srt"
        p.write_text("", encoding="utf-8")
        assert parse_srt(str(p)) == []

    def test_only_newlines(self, tmp_path):
        p = tmp_path / "blank.srt"
        p.write_text("\n\n\n", encoding="utf-8")
        assert parse_srt(str(p)) == []

    def test_single_entry(self, tmp_path):
        content = (
            "1\n"
            "00:01:30,000 --> 00:01:35,000\n"
            "Single entry here.\n"
        )
        p = tmp_path / "single.srt"
        p.write_text(content, encoding="utf-8")
        result = parse_srt(str(p))
        assert len(result) == 1
        assert result[0] == (90000, 95000, "Single entry here.")

    def test_multiline_text(self, tmp_path):
        content = (
            "1\n"
            "00:00:01,000 --> 00:00:03,000\n"
            "Line one\n"
            "Line two\n"
        )
        p = tmp_path / "multiline.srt"
        p.write_text(content, encoding="utf-8")
        result = parse_srt(str(p))
        assert result[0][2] == "Line one Line two"

    def test_invalid_timestamp_skipped(self, tmp_path):
        content = (
            "1\n"
            "not-a-timestamp\n"
            "Some text\n"
        )
        p = tmp_path / "invalid.srt"
        p.write_text(content, encoding="utf-8")
        assert parse_srt(str(p)) == []


class TestParseVTT:
    def test_normal(self, tmp_path, sample_vtt):
        p = tmp_path / "test.vtt"
        p.write_text(sample_vtt, encoding="utf-8")
        result = parse_vtt(str(p))
        assert len(result) == 2
        assert result[0] == (1000, 4000, "Hello from VTT.")
        assert result[1] == (5000, 8500, "Second VTT line.")

    def test_strips_tags(self, tmp_path, sample_vtt_with_tags):
        p = tmp_path / "tagged.vtt"
        p.write_text(sample_vtt_with_tags, encoding="utf-8")
        result = parse_vtt(str(p))
        assert len(result) == 1
        assert result[0][2] == "Hello from tagged VTT."

    def test_with_cue_label(self, tmp_path, sample_vtt_with_cue_label):
        p = tmp_path / "cued.vtt"
        p.write_text(sample_vtt_with_cue_label, encoding="utf-8")
        result = parse_vtt(str(p))
        assert len(result) == 1
        assert result[0][2] == "Text after a cue label."

    def test_empty_file(self, tmp_path):
        p = tmp_path / "empty.vtt"
        p.write_text("", encoding="utf-8")
        assert parse_vtt(str(p)) == []


class TestParseSimple:
    def test_normal(self, tmp_path, sample_simple):
        p = tmp_path / "test.txt"
        p.write_text(sample_simple, encoding="utf-8")
        result = parse_simple(str(p))
        assert len(result) == 3
        assert result[0] == (1000, 5000, "Hello world, simple format.")
        assert result[1] == (5000, 9000, "Second line here.")
        # Last entry gets +3s
        assert result[2] == (9000, 12000, "Third and final line.")

    def test_single_entry_adds_3s(self, tmp_path, sample_simple_single):
        p = tmp_path / "single.txt"
        p.write_text(sample_simple_single, encoding="utf-8")
        result = parse_simple(str(p))
        assert len(result) == 1
        assert result[0] == (90000, 93000, "Only one line.")

    def test_empty_file(self, tmp_path):
        p = tmp_path / "empty.txt"
        p.write_text("", encoding="utf-8")
        assert parse_simple(str(p)) == []

    def test_skips_empty_text_lines(self, tmp_path):
        content = "[00:00:01] First\n[00:00:02] \n[00:00:03] Third\n"
        p = tmp_path / "mixed.txt"
        p.write_text(content, encoding="utf-8")
        result = parse_simple(str(p))
        assert len(result) == 2


class TestParseAutoDetect:
    def test_simple_by_first_line(self, tmp_path):
        p = tmp_path / "whatever.txt"
        p.write_text("[00:00:01] Simple format line.\n", encoding="utf-8")
        result = parse(str(p))
        assert len(result) == 1

    def test_srt_by_extension(self, tmp_path, sample_srt):
        p = tmp_path / "test.srt"
        p.write_text(sample_srt, encoding="utf-8")
        result = parse(str(p))
        assert len(result) == 3
        # Confirm it used SRT parser (end_ms from timestamp, not auto-calculated)
        assert result[0][1] == 4000

    def test_vtt_by_extension(self, tmp_path, sample_vtt):
        p = tmp_path / "test.vtt"
        p.write_text(sample_vtt, encoding="utf-8")
        result = parse(str(p))
        assert len(result) == 2

    def test_unknown_extension_raises(self, tmp_path):
        p = tmp_path / "test.xyz"
        p.write_text("some random text\n", encoding="utf-8")
        with pytest.raises(ValueError, match="Unsupported subtitle format"):
            parse(str(p))


class TestToText:
    def test_basic(self):
        subtitles = [(1000, 4000, "Hello"), (5000, 8000, "World")]
        result = to_text(subtitles)
        assert result == "[00:00:01] Hello\n[00:00:05] World"

    def test_empty(self):
        assert to_text([]) == ""


class TestFormatTimestamp:
    def test_zero(self):
        assert format_timestamp(0) == "00:00:00"

    def test_hours(self):
        assert format_timestamp(3661000) == "01:01:01"

    def test_rounds_down(self):
        assert format_timestamp(1500) == "00:00:01"
