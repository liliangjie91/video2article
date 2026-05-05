"""Tests for pipeline/synthesize.py — Stage 5 (mock LLM)."""

import json
import pytest
from pipeline import synthesize

SAMPLE_INSIGHTS = {
    "overall_thesis": "Test thesis",
    "segments": [
        {
            "id": 1,
            "topic": "Intro",
            "relation_to_prev": "新话题引入",
            "main_claim": "This is the intro",
            "key_points": ["Point 1"],
            "sentences": ["Hello world."],
            "insight": {
                "core_summary": "Deep analysis",
                "implicit_assumptions": "Assumption",
                "background": "Background",
                "connections": "Connections",
                "critical_questions": "Questions",
            },
        }
    ],
}

SAMPLE_OUTLINE = {
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
        }
    ],
}


@pytest.fixture
def insights_file(tmp_path):
    p = tmp_path / "03_insights.json"
    p.write_text(json.dumps(SAMPLE_INSIGHTS, indent=2), encoding="utf-8")
    return p


@pytest.fixture
def outline_file(tmp_path):
    p = tmp_path / "04_outline.json"
    p.write_text(json.dumps(SAMPLE_OUTLINE, indent=2), encoding="utf-8")
    return p


class TestRun:
    def test_creates_output(self, tmp_path, insights_file, outline_file, mocker):
        mocker.patch("pipeline.synthesize.chat", return_value="Content here.")
        out = synthesize.run(str(insights_file), str(outline_file), str(tmp_path), tier="best")
        assert out == str(tmp_path / "05_article.md")
        content = (tmp_path / "05_article.md").read_text(encoding="utf-8")
        assert "# Test Article" in content

    def test_skip_if_output_exists(self, tmp_path, insights_file, outline_file, mocker):
        mock_chat = mocker.patch("pipeline.synthesize.chat")
        (tmp_path / "05_article.md").write_text("existing", encoding="utf-8")
        synthesize.run(str(insights_file), str(outline_file), str(tmp_path), tier="best")
        mock_chat.assert_not_called()

    def test_passes_outline_context_in_prompt(self, tmp_path, insights_file, outline_file, mocker):
        mock_chat = mocker.patch("pipeline.synthesize.chat", return_value="# Article")
        synthesize.run(str(insights_file), str(outline_file), str(tmp_path), tier="best")
        prompt = mock_chat.call_args[0][0]
        assert "Test thesis" in prompt
        assert "引言" in prompt
        assert "Hello world" in prompt
