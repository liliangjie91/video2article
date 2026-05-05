"""Stage 4: 结构+深度挖掘 → 写作大纲 — JSON 输出"""

import json
import os
import logging
from llm import chat, set_log_dir
from utils import safe_parse_json, extract_json

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """你是一位资深杂志主编，负责为深度文章制定写作大纲。你的大纲需要将分析材料转化为有说服力、有节奏感的文章结构。

## 任务
基于提供的视频文稿结构分析与深度挖掘笔记，设计一份详细的写作大纲。你需要：
1. 决定哪些分析段落需要合并、拆分或调整顺序，以形成更好的叙事逻辑
2. 为每个大纲段落设定明确的写作目标和字数预算
3. 通过 `source_segment_ids` 标注每个大纲段落来源自哪些原始分析段落
4. 确保整篇文章覆盖所有重要观点，同时避免重复

## 输出格式（必须严格 JSON）
```json
{
  "meta": {
    "title": "建议的文章标题",
    "word_count_target": 5000,
    "style": "深度分析",
    "tone": "严肃"
  },
  "outline": [
    {
      "id": 1,
      "heading": "段落标题",
      "source_segment_ids": [1],
      "word_count_estimate": 800,
      "key_points": ["核心论点1", "核心论点2"],
      "sources": [
        {"source_segment_id": 1, "relevance": "核心来源"}
      ]
    }
  ]
}

严格遵守：
- 输出必须是 **完整的纯 JSON 格式**，必须能被标准解析器正确解析
- **字段内容中使用引号时，务必使用中文引号「」代替英文双引号，防止JSON解析失败**
- 不要添加任何解释、注释或额外文本
- 大纲段落数量控制在 4-6 个之间
- 所有 source_segment_ids 必须在输入材料的 segments 中存在"""


def run(insights_path: str, output_dir: str, tier: str = "best",
        word_count: int = 5000, style: str = "深度分析") -> str:
    """Run Stage 4 (outline). Returns path to 04_outline.json."""
    output_path = os.path.join(output_dir, "04_outline.json")
    if os.path.exists(output_path):
        logger.info("Stage 4 output already exists, skipping: %s", output_path)
        return output_path

    os.makedirs(output_dir, exist_ok=True)

    with open(insights_path, "r", encoding="utf-8") as f:
        insights_data = json.load(f)

    set_log_dir(os.path.join(output_dir, "llm_logs"))

    # Build prompt from merged insights data
    prompt_parts = [
        "以下是一段视频文稿的结构分析与深度挖掘笔记，请基于这些材料设计一份写作大纲。",
        f"\n## 全文核心论点\n{insights_data.get('overall_thesis', '未知')}",
        f"\n## 宏观参数\n- 目标字数：{word_count} 字\n- 风格：{style}",
        "\n## 分析段落详情",
    ]
    for seg in insights_data.get("segments", []):
        insight = seg.get("insight", {})
        prompt_parts.append(
            f"\n### 段落 {seg.get('id')}：{seg.get('topic', '未知')}\n"
            f"核心主张：{seg.get('main_claim', '')}\n"
            f"关键论点：{'；'.join(seg.get('key_points', []))}\n"
            f"原文：{' '.join(seg.get('sentences', []))}\n"
            f"--- 深度分析 ---\n"
            f"核心提炼：{insight.get('core_summary', '')}\n"
            f"隐含假设：{insight.get('implicit_assumptions', '')}\n"
            f"背景补充：{insight.get('background', '')}\n"
            f"延伸关联：{insight.get('connections', '')}\n"
            f"批判追问：{insight.get('critical_questions', '')}"
        )

    prompt_parts.append("\n请基于以上材料，输出写作大纲 JSON。")
    prompt = "\n".join(prompt_parts)

    raw = chat(prompt, tier=tier, system=SYSTEM_PROMPT, step=4)
    raw = extract_json(raw)

    try:
        outline = safe_parse_json(raw)
    except json.JSONDecodeError:
        debug_path = os.path.join(output_dir, "..", "tmp", "outline_raw.json")
        os.makedirs(os.path.dirname(os.path.abspath(debug_path)), exist_ok=True)
        with open(debug_path, "w", encoding="utf-8") as f:
            f.write(raw)
        logger.error("Invalid JSON from LLM for outline. Raw saved to %s", debug_path)
        raise

    # Validate
    if "outline" not in outline or not isinstance(outline["outline"], list):
        raise ValueError("LLM output missing 'outline' array")

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(outline, f, indent=2, ensure_ascii=False)

    count = len(outline.get("outline", []))
    logger.info("Stage 4 output: %s (%d outline segments)", output_path, count)
    return output_path
