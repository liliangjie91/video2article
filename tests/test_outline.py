"""Tests for pipeline/outline.py — Stage 4 (mock LLM)."""

import json
import pytest
from pipeline import outline

SAMPLE_INSIGHTS = {
    "overall_thesis": "Test thesis for outline",
    "segments": [
        {
            "id": 1,
            "topic": "Intro",
            "main_claim": "Intro claim",
            "key_points": ["Point A"],
            "sentences": ["Sentence one."],
            "insight": {
                "core_summary": "Summary of intro",
                "implicit_assumptions": "Assumption",
                "background": "Background",
                "connections": "Connections",
                "critical_questions": "Questions",
            },
        },
        {
            "id": 2,
            "topic": "Body",
            "main_claim": "Body claim",
            "key_points": ["Point B"],
            "sentences": ["Sentence two."],
            "insight": {
                "core_summary": "Summary of body",
                "implicit_assumptions": "Assumption",
                "background": "Background",
                "connections": "Connections",
                "critical_questions": "Questions",
            },
        },
    ],
}

VALID_OUTLINE = json.dumps({
    "meta": {
        "title": "Test Article",
        "word_count_target": 5000,
        "style": "深度分析",
        "tone": "严肃",
    },
    "outline": [
        {
            "id": 1,
            "heading": "引言",
            "source_segment_ids": [1],
            "word_count_estimate": 800,
            "key_points": ["Intro point"],
            "sources": [{"source_segment_id": 1, "relevance": "核心来源"}],
        },
        {
            "id": 2,
            "heading": "主体分析",
            "source_segment_ids": [2],
            "word_count_estimate": 1200,
            "key_points": ["Body point"],
            "sources": [{"source_segment_id": 2, "relevance": "核心来源"}],
        },
    ],
})


@pytest.fixture
def insights_file(tmp_path):
    p = tmp_path / "03_insights.json"
    p.write_text(json.dumps(SAMPLE_INSIGHTS, indent=2), encoding="utf-8")
    return p


class TestRun:
    def test_creates_outline_json(self, tmp_path, insights_file, mocker):
        mocker.patch("pipeline.outline.chat", return_value=VALID_OUTLINE)
        out = outline.run(str(insights_file), str(tmp_path), tier="best")
        assert out == str(tmp_path / "04_outline.json")
        data = json.loads((tmp_path / "04_outline.json").read_text(encoding="utf-8"))
        assert "meta" in data
        assert "outline" in data
        assert data["meta"]["title"] == "Test Article"
        assert len(data["outline"]) == 2

    def test_outline_has_required_fields(self, tmp_path, insights_file, mocker):
        mocker.patch("pipeline.outline.chat", return_value=VALID_OUTLINE)
        outline.run(str(insights_file), str(tmp_path), tier="best")
        data = json.loads((tmp_path / "04_outline.json").read_text(encoding="utf-8"))
        for seg in data["outline"]:
            assert "id" in seg
            assert "heading" in seg
            assert "source_segment_ids" in seg
            assert "word_count_estimate" in seg
            assert "key_points" in seg

    def test_skip_if_output_exists(self, tmp_path, insights_file, mocker):
        mock_chat = mocker.patch("pipeline.outline.chat")
        (tmp_path / "04_outline.json").write_text("{}", encoding="utf-8")
        outline.run(str(insights_file), str(tmp_path), tier="best")
        mock_chat.assert_not_called()

    def test_passes_insights_context_in_prompt(self, tmp_path, insights_file, mocker):
        mock_chat = mocker.patch("pipeline.outline.chat", return_value=VALID_OUTLINE)
        outline.run(str(insights_file), str(tmp_path), tier="best")
        prompt = mock_chat.call_args[0][0]
        assert "Test thesis for outline" in prompt
        assert "Intro" in prompt
        assert "Body" in prompt
        assert "Summary of intro" in prompt

    def test_invalid_json_raises(self, tmp_path, insights_file, mocker):
        mocker.patch("pipeline.outline.chat", return_value="not valid json")
        with pytest.raises(json.JSONDecodeError):
            outline.run(str(insights_file), str(tmp_path), tier="best")

    def test_missing_outline_array_raises(self, tmp_path, insights_file, mocker):
        mocker.patch("pipeline.outline.chat", return_value=json.dumps({"meta": {}}))
        with pytest.raises(ValueError, match="outline"):
            outline.run(str(insights_file), str(tmp_path), tier="best")

    def test_strips_markdown_fence(self, tmp_path, insights_file, mocker):
        mocker.patch("pipeline.outline.chat", return_value=f"```json\n{VALID_OUTLINE}\n```")
        outline.run(str(insights_file), str(tmp_path), tier="best")
        data = json.loads((tmp_path / "04_outline.json").read_text(encoding="utf-8"))
        assert len(data["outline"]) == 2
