"""Tests for commands.py — pipeline orchestration (mock pipeline stages)."""

import pytest
from commands import _run_article_pipeline, process_one, process_batch


class TestRunArticlePipeline:
    def test_full_pipeline(self, tmp_path, mocker):
        mocker.patch("pipeline.preprocess.run", return_value=str(tmp_path / "01_preprocessed.txt"))
        mocker.patch("pipeline.structure.run", return_value=str(tmp_path / "02_structure.json"))
        mocker.patch("pipeline.insights.run", return_value=str(tmp_path / "03_insights.json"))
        mock_syn = mocker.patch("pipeline.synthesize.run", return_value=str(tmp_path / "04_article.md"))

        srt = tmp_path / "test.srt"
        srt.write_text("1\n00:00:01,000 --> 00:00:02,000\nHello.\n", encoding="utf-8")

        result = _run_article_pipeline(str(srt), str(tmp_path), "best", dry_run=False)
        assert result == str(tmp_path / "04_article.md")

    def test_simple_mode(self, tmp_path, mocker):
        mock_preprocess = mocker.patch("pipeline.preprocess.run")
        mock_simple = mocker.patch("pipeline.simple.run", return_value=str(tmp_path / "04_article_simple.md"))

        srt = tmp_path / "test.srt"
        srt.write_text("1\n00:00:01,000 --> 00:00:02,000\nHello.\n", encoding="utf-8")

        result = _run_article_pipeline(str(srt), str(tmp_path), "best", dry_run=False, simple=True)
        assert result == str(tmp_path / "04_article_simple.md")
        mock_preprocess.assert_not_called()
        mock_simple.assert_called_once()

    def test_dry_run_returns_none(self, tmp_path, mocker):
        mocker.patch("pipeline.preprocess.run")
        result = _run_article_pipeline("input.srt", str(tmp_path), "best", dry_run=True)
        assert result is None


class TestProcessOne:
    def test_srt_input(self, tmp_path, mocker):
        mock_pipeline = mocker.patch("commands._run_article_pipeline", return_value=str(tmp_path / "04_article.md"))
        srt = tmp_path / "test.srt"
        srt.write_text("1\n00:00:01,000 --> 00:00:02,000\nTest.\n", encoding="utf-8")

        result = process_one(str(srt), tier="best")
        assert result == str(tmp_path / "04_article.md")
        mock_pipeline.assert_called_once()

    def test_dry_run(self, mocker):
        mock_pipeline = mocker.patch("commands._run_article_pipeline", return_value=None)
        mocker.patch("commands.detect_input_type", return_value="srt")

        result = process_one("input.srt", dry_run=True)
        assert result is None


class TestProcessBatch:
    def test_empty_inputs(self, mocker):
        mock_one = mocker.patch("commands.process_one")
        process_batch([], tier="fast")
        mock_one.assert_not_called()

    def test_processes_all_inputs(self, mocker):
        mocker.patch("commands.process_one", return_value="/out/article.md")
        process_batch(["a", "b", "c"], tier="fast")

    def test_continues_on_failure(self, mocker):
        mock_one = mocker.patch("commands.process_one", side_effect=[Exception("fail"), "/ok.md"])
        process_batch(["bad", "good"], tier="fast")
        assert mock_one.call_count == 2
