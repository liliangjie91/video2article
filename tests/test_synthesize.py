"""Tests for pipeline/synthesize.py — Stage 4 (mock LLM)."""

import json
import pytest
from pipeline import synthesize

SAMPLE_STRUCTURE = {
    "overall_thesis": "Test thesis",
    "segments": [
        {
            "id": 1,
            "topic": "Intro",
            "relation_to_prev": "新话题引入",
            "main_claim": "This is the intro",
            "key_points": ["Point 1"],
            "sentences": ["Hello world."],
        }
    ],
}

SAMPLE_INSIGHTS = "## Paragraph 1: Intro\nSome deep analysis here."


@pytest.fixture
def structure_file(tmp_path):
    p = tmp_path / "02_structure.json"
    p.write_text(json.dumps(SAMPLE_STRUCTURE, indent=2), encoding="utf-8")
    return p


@pytest.fixture
def insights_file(tmp_path):
    p = tmp_path / "03_insights.md"
    p.write_text(SAMPLE_INSIGHTS, encoding="utf-8")
    return p


class TestRun:
    def test_creates_output(self, tmp_path, structure_file, insights_file, mocker):
        mocker.patch("pipeline.synthesize.chat", return_value="# Final article\n\nContent here.")
        out = synthesize.run(str(structure_file), str(insights_file), str(tmp_path), tier="best")
        assert out == str(tmp_path / "04_article.md")
        content = (tmp_path / "04_article.md").read_text(encoding="utf-8")
        assert "# Final article" in content

    def test_skip_if_output_exists(self, tmp_path, structure_file, insights_file, mocker):
        mock_chat = mocker.patch("pipeline.synthesize.chat")
        (tmp_path / "04_article.md").write_text("existing", encoding="utf-8")
        synthesize.run(str(structure_file), str(insights_file), str(tmp_path), tier="best")
        mock_chat.assert_not_called()

    def test_includes_both_inputs_in_prompt(self, tmp_path, structure_file, insights_file, mocker):
        mock_chat = mocker.patch("pipeline.synthesize.chat", return_value="# Article")
        synthesize.run(str(structure_file), str(insights_file), str(tmp_path), tier="best")
        prompt = mock_chat.call_args[0][0]
        assert "Test thesis" in prompt
        assert "Some deep analysis" in prompt
