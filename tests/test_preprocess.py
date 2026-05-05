"""Tests for pipeline/preprocess.py — Stage 1 (mock LLM)."""

from pipeline import preprocess
from utils.parser import parse


def test_run_creates_output(tmp_path, mocker):
    mock_chat = mocker.patch("pipeline.preprocess.chat", return_value="Cleaned text.")
    srt = tmp_path / "test.srt"
    srt.write_text("1\n00:00:01,000 --> 00:00:02,000\nHello.\n", encoding="utf-8")

    out = preprocess.run(str(srt), str(tmp_path), tier="fast")

    assert out == str(tmp_path / "01_preprocessed.txt")
    assert (tmp_path / "01_preprocessed.txt").read_text(encoding="utf-8") == "Cleaned text."
    mock_chat.assert_called_once()


def test_skip_if_output_exists(tmp_path, mocker):
    mock_chat = mocker.patch("pipeline.preprocess.chat")
    (tmp_path / "01_preprocessed.txt").write_text("existing", encoding="utf-8")

    out = preprocess.run(str(tmp_path / "nothing.srt"), str(tmp_path), tier="fast")

    assert out == str(tmp_path / "01_preprocessed.txt")
    mock_chat.assert_not_called()


def test_passes_subtitle_text_to_llm(tmp_path, mocker):
    mock_chat = mocker.patch("pipeline.preprocess.chat", return_value="Cleaned.")
    srt = tmp_path / "test.srt"
    srt.write_text("1\n00:00:01,000 --> 00:00:02,000\nHello world.\n", encoding="utf-8")

    preprocess.run(str(srt), str(tmp_path), tier="fast")

    # Verify LLM received the parsed text
    call_kwargs = mock_chat.call_args[1]
    assert "Hello world" in mock_chat.call_args[0][0] or "Hello world" in str(mock_chat.call_args)


def test_run_with_different_tier(tmp_path, mocker):
    mock_chat = mocker.patch("pipeline.preprocess.chat", return_value="Cleaned.")
    srt = tmp_path / "test.srt"
    srt.write_text("1\n00:00:01,000 --> 00:00:02,000\nTest.\n", encoding="utf-8")

    preprocess.run(str(srt), str(tmp_path), tier="best")

    assert mock_chat.call_args[1]["tier"] == "best"
