"""Tests for pipeline/simple.py — quick mode (mock LLM)."""

from pipeline import simple


def test_run_creates_output(tmp_path, mocker):
    mock_chat = mocker.patch("pipeline.simple.chat", return_value="# Quick article\n\nContent.")
    srt = tmp_path / "test.srt"
    srt.write_text("1\n00:00:01,000 --> 00:00:02,000\nHello.\n", encoding="utf-8")

    out = simple.run(str(srt), str(tmp_path), tier="best")

    assert out == str(tmp_path / "04_article_simple.md")
    assert (tmp_path / "04_article_simple.md").read_text(encoding="utf-8") == "# Quick article\n\nContent."
    mock_chat.assert_called_once()


def test_skip_if_output_exists(tmp_path, mocker):
    mock_chat = mocker.patch("pipeline.simple.chat")
    (tmp_path / "04_article_simple.md").write_text("existing", encoding="utf-8")

    simple.run(str(tmp_path / "nothing.srt"), str(tmp_path), tier="best")

    mock_chat.assert_not_called()


def test_passes_subtitle_to_llm(tmp_path, mocker):
    mock_chat = mocker.patch("pipeline.simple.chat", return_value="# Article")
    srt = tmp_path / "test.srt"
    srt.write_text("1\n00:00:01,000 --> 00:00:02,000\nHello world.\n", encoding="utf-8")

    simple.run(str(srt), str(tmp_path), tier="best")

    prompt = mock_chat.call_args[0][0]
    assert "Hello world" in prompt
