"""Tests for pipeline/insights.py — Stage 3 (mock LLM)."""

import json
import pytest
from pipeline import insights

SAMPLE_STRUCTURE = {
    "overall_thesis": "Test thesis",
    "segments": [
        {
            "id": 1,
            "topic": "Intro",
            "relation_to_prev": "新话题引入",
            "main_claim": "Intro claim",
            "key_points": ["Point A"],
            "sentences": ["Sentence 1."],
        },
        {
            "id": 2,
            "topic": "Body",
            "relation_to_prev": "递进",
            "main_claim": "Body claim",
            "key_points": ["Point B"],
            "sentences": ["Sentence 2."],
        },
    ],
}


@pytest.fixture
def structure_file(tmp_path):
    p = tmp_path / "02_structure.json"
    p.write_text(json.dumps(SAMPLE_STRUCTURE, indent=2), encoding="utf-8")
    return p


class TestRun:
    def test_creates_output(self, tmp_path, structure_file, mocker):
        mocker.patch("pipeline.insights.chat", return_value="## Segment insight content")
        out = insights.run(str(structure_file), str(tmp_path), tier="best")
        assert out == str(tmp_path / "03_insights.md")
        content = (tmp_path / "03_insights.md").read_text(encoding="utf-8")
        assert "## Segment insight content" in content

    def test_calls_llm_per_segment(self, tmp_path, structure_file, mocker):
        mock_chat = mocker.patch("pipeline.insights.chat", return_value="Insight.")
        insights.run(str(structure_file), str(tmp_path), tier="best")
        assert mock_chat.call_count == 2

    def test_separates_segments_with_divider(self, tmp_path, structure_file, mocker):
        mocker.patch("pipeline.insights.chat", side_effect=["First insight.", "Second insight."])
        out = insights.run(str(structure_file), str(tmp_path), tier="best")
        content = (tmp_path / "03_insights.md").read_text(encoding="utf-8")
        assert "First insight." in content
        assert "Second insight." in content

    def test_skip_if_output_exists(self, tmp_path, structure_file, mocker):
        mock_chat = mocker.patch("pipeline.insights.chat")
        (tmp_path / "03_insights.md").write_text("existing", encoding="utf-8")
        insights.run(str(structure_file), str(tmp_path), tier="best")
        mock_chat.assert_not_called()

    def test_passes_structure_context_in_prompt(self, tmp_path, structure_file, mocker):
        mock_chat = mocker.patch("pipeline.insights.chat", return_value="Insight.")
        insights.run(str(structure_file), str(tmp_path), tier="best")
        # First call should include Intro, second call Body
        prompt0 = mock_chat.call_args_list[0][0][0]
        assert "Test thesis" in prompt0
        assert "Intro" in prompt0
        prompt1 = mock_chat.call_args_list[1][0][0]
        assert "Body" in prompt1
