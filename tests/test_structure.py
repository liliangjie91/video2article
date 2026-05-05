"""Tests for pipeline/structure.py — Stage 2 (mock LLM)."""

import json
import pytest
from pipeline import structure

VALID_STRUCTURE = json.dumps(
    {
        "overall_thesis": "Test thesis",
        "segments": [
            {
                "id": 1,
                "topic": "Intro",
                "relation_to_prev": "新话题引入",
                "main_claim": "This is the intro",
                "key_points": ["Point 1"],
                "sentences": ["Hello."],
            },
            {
                "id": 2,
                "topic": "Body",
                "relation_to_prev": "递进",
                "main_claim": "This is the body",
                "key_points": ["Point 2"],
                "sentences": ["World."],
            },
            {
                "id": 3,
                "topic": "Conclusion",
                "relation_to_prev": "承接上文",
                "main_claim": "This is the end",
                "key_points": ["Point 3"],
                "sentences": ["Done."],
            },
        ],
    }
)


@pytest.fixture
def preprocessed_file(tmp_path):
    p = tmp_path / "01_preprocessed.txt"
    p.write_text("Some preprocessed text.\n", encoding="utf-8")
    return p


class TestRun:
    def test_creates_output(self, tmp_path, preprocessed_file, mocker):
        mocker.patch("pipeline.structure.chat", return_value=VALID_STRUCTURE)
        out = structure.run(str(preprocessed_file), str(tmp_path), tier="fast")
        assert out == str(tmp_path / "02_structure.json")
        data = json.loads((tmp_path / "02_structure.json").read_text(encoding="utf-8"))
        assert data["overall_thesis"] == "Test thesis"
        assert len(data["segments"]) == 3

    def test_skip_if_output_exists(self, tmp_path, preprocessed_file, mocker):
        mock_chat = mocker.patch("pipeline.structure.chat")
        (tmp_path / "02_structure.json").write_text("{}", encoding="utf-8")
        structure.run(str(preprocessed_file), str(tmp_path), tier="fast")
        mock_chat.assert_not_called()

    def test_invalid_json_raises(self, tmp_path, preprocessed_file, mocker):
        mocker.patch("pipeline.structure.chat", return_value="not valid json")
        with pytest.raises(json.JSONDecodeError):
            structure.run(str(preprocessed_file), str(tmp_path), tier="fast")

    def test_strips_markdown_fence(self, tmp_path, preprocessed_file, mocker):
        mocker.patch("pipeline.structure.chat", return_value=f"```json\n{VALID_STRUCTURE}\n```")
        out = structure.run(str(preprocessed_file), str(tmp_path), tier="fast")
        data = json.loads((tmp_path / "02_structure.json").read_text(encoding="utf-8"))
        assert data["overall_thesis"] == "Test thesis"


class TestRetry:
    def test_retry_when_too_few_segments(self, tmp_path, preprocessed_file, mocker):
        too_few = json.dumps({"overall_thesis": "x", "segments": [{"id": 1, "topic": "A", "relation_to_prev": "新话题引入", "main_claim": "x", "key_points": [], "sentences": ["a"]}]})
        mock_chat = mocker.patch("pipeline.structure.chat", side_effect=[too_few, VALID_STRUCTURE])
        out = structure.run(str(preprocessed_file), str(tmp_path), tier="fast")
        assert mock_chat.call_count == 2
        data = json.loads((tmp_path / "02_structure.json").read_text(encoding="utf-8"))
        assert len(data["segments"]) == 3

    def test_retry_when_too_many_segments(self, tmp_path, preprocessed_file, mocker):
        many_segs = [{"id": i, "topic": f"S{i}", "relation_to_prev": "递进" if i > 1 else "新话题引入", "main_claim": "x", "key_points": [], "sentences": ["x"]} for i in range(1, 10)]
        too_many = json.dumps({"overall_thesis": "x", "segments": many_segs})
        mock_chat = mocker.patch("pipeline.structure.chat", side_effect=[too_many, VALID_STRUCTURE])
        out = structure.run(str(preprocessed_file), str(tmp_path), tier="fast")
        assert mock_chat.call_count == 2

    def test_retry_still_fails_if_second_also_bad(self, tmp_path, preprocessed_file, mocker):
        bad = json.dumps({"overall_thesis": "x", "segments": [{"id": 1, "topic": "A", "relation_to_prev": "新话题引入", "main_claim": "x", "key_points": [], "sentences": ["a"]}]})
        mock_chat = mocker.patch("pipeline.structure.chat", side_effect=[bad, bad])
        out = structure.run(str(preprocessed_file), str(tmp_path), tier="fast")
        # Accepts whatever we got after retry (no 3rd attempt)
        data = json.loads((tmp_path / "02_structure.json").read_text(encoding="utf-8"))
        assert len(data["segments"]) == 1
