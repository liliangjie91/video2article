"""Stage 3: 文本 + 骨架 → 深度挖掘笔记 (核心) — JSON 输出"""

import json
import os
import logging
from llm import chat, set_log_dir

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """你是一位资深杂志主编，你的独特能力是从看似平常的叙述中挖掘深层价值。你的读者是受过良好教育、对相关领域有基础了解的群体，他们不满足于"复述"，而是希望读到原文之外的东西。

对下面提供的文本段落，请从五个维度进行深度分析。每个维度的回答必须具体、有信息量，不能泛泛而谈。

## 分析维度

### 1. 核心提炼
用一句话精确概括本段的核心主张或信息要点。要求：精准、不含糊、抓住本质。

### 2. 隐含假设
说话者默认了什么前提或预设？有哪些"没有明说但默认听众已经接受"的观点？这些隐含假设是否经得起推敲？

### 3. 背景补充
有哪些相关的历史、科学或文化背景知识，可以帮助读者更深入地理解这段话？请提供具体的信息，而非"需要了解相关背景"这样的空话。如果某个背景知识你不完全确定，请在后面标注[推测]。

### 4. 延伸关联
这段话的内容和其他已知事件、理论、现象、人物有什么关联？可以是横向关联（同一时期/同一领域）、纵向关联（历史脉络中的前后影响）、或跨领域关联。

### 5. 批判追问
如果从不同立场或视角看这个问题，会得出什么不同的结论？说话者的论证是否存在局限、遗漏或值得商榷之处？提出1-2个真正值得追问的问题。

## 输出格式（必须严格 JSON）
```json
{
  "segment_id": 1,
  "topic": "段落主题",
  "core_summary": "核心提炼内容",
  "implicit_assumptions": "隐含假设内容",
  "background": "背景补充内容",
  "connections": "延伸关联内容",
  "critical_questions": "批判追问内容"
}
```

严格遵守：
- 输出必须是 **完整的纯 JSON 格式**，必须能被标准解析器正确解析
- 不要添加任何解释、注释或额外文本
- 背景知识不确定时在内容中标注[推测]"""


def _build_segment_prompt(segment: dict) -> str:
    topic = segment.get("topic", "未命名")
    sentences = segment.get("sentences", [])
    text = "\n".join(sentences)

    main_claim = segment.get("main_claim", "")
    key_points = segment.get("key_points", [])
    ref = ""
    if main_claim or key_points:
        lines = []
        if main_claim:
            lines.append(f"核心主张: {main_claim}")
        if key_points:
            for kp in key_points:
                lines.append(f"- {kp}")
        ref = "\n结构参考:\n" + "\n".join(lines)

    return f"## 段落 {segment['id']}: {topic}\n\n原文文本:\n{text}{ref}"


def _extract_json(raw: str) -> str:
    """Strip markdown fences and extract raw JSON string."""
    raw = raw.strip()
    if raw.startswith("```"):
        raw = raw.split("\n", 1)[-1]
        if raw.endswith("```"):
            raw = raw[:-3]
        raw = raw.strip()
    return raw


def _validate_insight(insight: dict) -> list[str]:
    """Return list of missing fields if any."""
    required = ["segment_id", "topic", "core_summary", "implicit_assumptions", "background", "connections", "critical_questions"]
    return [f for f in required if f not in insight]


def run(structure_path: str, output_dir: str, tier: str = "best") -> str:
    """Run Stage 3. Returns path to 03_insights.json."""
    output_path = os.path.join(output_dir, "03_insights.json")
    if os.path.exists(output_path):
        logger.info("Stage 3 output already exists, skipping: %s", output_path)
        return output_path

    os.makedirs(output_dir, exist_ok=True)

    with open(structure_path, "r", encoding="utf-8") as f:
        structure = json.load(f)

    set_log_dir(os.path.join(output_dir, "llm_logs"))
    segments = structure.get("segments", [])
    insights = []

    for i, seg in enumerate(segments):
        logger.info("Analyzing segment %d/%d: %s", seg["id"], len(segments), seg.get("topic", ""))
        prompt_parts = [
            f"以下是一个视频文稿的深度分析任务。",
            f"全文核心论点: {structure.get('overall_thesis', '未知')}",
            "",
            "当前需要分析的段落：",
            _build_segment_prompt(seg),
            "",
            "请从五个维度分析这段话，输出 JSON。",
        ]
        prompt = "\n".join(prompt_parts)

        raw = chat(prompt, tier=tier, system=SYSTEM_PROMPT, step=3)
        raw = _extract_json(raw)
        try:
            insight = json.loads(raw)
        except json.JSONDecodeError:
            debug_path = os.path.join(output_dir, "..", "tmp", f"insights_raw_seg{seg['id']}.json")
            os.makedirs(os.path.dirname(os.path.abspath(debug_path)), exist_ok=True)
            with open(debug_path, "w", encoding="utf-8") as f:
                f.write(raw)
            logger.error("Invalid JSON from LLM for segment %d. Raw saved to %s", seg["id"], debug_path)
            raise

        missing = _validate_insight(insight)
        if missing:
            logger.warning("Segment %d missing fields: %s", seg["id"], missing)

        insights.append(insight)

    # Merge each insight back into its structure segment
    merged_segments = []
    for seg in segments:
        seg_id = seg.get("id")
        matched = next((ins for ins in insights if ins.get("segment_id") == seg_id), {})
        merged = dict(seg)  # copy structure fields
        merged["insight"] = {
            "core_summary": matched.get("core_summary", ""),
            "implicit_assumptions": matched.get("implicit_assumptions", ""),
            "background": matched.get("background", ""),
            "connections": matched.get("connections", ""),
            "critical_questions": matched.get("critical_questions", ""),
        }
        merged_segments.append(merged)

    output = {
        "overall_thesis": structure.get("overall_thesis", ""),
        "segments": merged_segments,
    }
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(output, f, indent=2, ensure_ascii=False)

    logger.info("Stage 3 output: %s (%d segments)", output_path, len(insights))
    return output_path
