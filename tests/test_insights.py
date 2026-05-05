"""Tests for pipeline/insights.py — Stage 3 (mock LLM, JSON output)."""

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

VALID_INSIGHT = json.dumps({
    "segment_id": 1,
    "topic": "Intro",
    "core_summary": "Summary here",
    "implicit_assumptions": "Assumption here",
    "background": "Background here",
    "connections": "Connection here",
    "critical_questions": "Question here",
})


@pytest.fixture
def structure_file(tmp_path):
    p = tmp_path / "02_structure.json"
    p.write_text(json.dumps(SAMPLE_STRUCTURE, indent=2), encoding="utf-8")
    return p


class TestRun:
    def test_creates_json_output(self, tmp_path, structure_file, mocker):
        mocker.patch("pipeline.insights.chat", return_value=VALID_INSIGHT)
        out = insights.run(str(structure_file), str(tmp_path), tier="best")
        assert out == str(tmp_path / "03_insights.json")
        data = json.loads((tmp_path / "03_insights.json").read_text(encoding="utf-8"))
        assert "segments" in data
        assert data["segments"][0]["core_summary"] == "Summary here"

    def test_calls_llm_per_segment(self, tmp_path, structure_file, mocker):
        mock_chat = mocker.patch("pipeline.insights.chat", return_value=VALID_INSIGHT)
        insights.run(str(structure_file), str(tmp_path), tier="best")
        assert mock_chat.call_count == 2

    def test_collects_all_segments(self, tmp_path, structure_file, mocker):
        seg1 = json.dumps({"segment_id": 1, "topic": "Intro", "core_summary": "S1", "implicit_assumptions": "", "background": "", "connections": "", "critical_questions": ""})
        seg2 = json.dumps({"segment_id": 2, "topic": "Body", "core_summary": "S2", "implicit_assumptions": "", "background": "", "connections": "", "critical_questions": ""})
        mocker.patch("pipeline.insights.chat", side_effect=[seg1, seg2])
        insights.run(str(structure_file), str(tmp_path), tier="best")
        data = json.loads((tmp_path / "03_insights.json").read_text(encoding="utf-8"))
        assert len(data["segments"]) == 2

    def test_skip_if_output_exists(self, tmp_path, structure_file, mocker):
        mock_chat = mocker.patch("pipeline.insights.chat")
        (tmp_path / "03_insights.json").write_text("{}", encoding="utf-8")
        insights.run(str(structure_file), str(tmp_path), tier="best")
        mock_chat.assert_not_called()

    def test_passes_structure_context_in_prompt(self, tmp_path, structure_file, mocker):
        mock_chat = mocker.patch("pipeline.insights.chat", return_value=VALID_INSIGHT)
        insights.run(str(structure_file), str(tmp_path), tier="best")
        prompt0 = mock_chat.call_args_list[0][0][0]
        assert "Test thesis" in prompt0
        assert "Intro" in prompt0
        prompt1 = mock_chat.call_args_list[1][0][0]
        assert "Body" in prompt1

    def test_invalid_json_raises(self, tmp_path, structure_file, mocker):
        mocker.patch("pipeline.insights.chat", return_value="not valid json")
        with pytest.raises(json.JSONDecodeError):
            insights.run(str(structure_file), str(tmp_path), tier="best")

    def test_strips_markdown_fence(self, tmp_path, structure_file, mocker):
        mocker.patch("pipeline.insights.chat", return_value=f"```json\n{VALID_INSIGHT}\n```")
        out = insights.run(str(structure_file), str(tmp_path), tier="best")
        data = json.loads((tmp_path / "03_insights.json").read_text(encoding="utf-8"))
        assert data["segments"][0]["core_summary"] == "Summary here"
