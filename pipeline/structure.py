"""Stage 2: 书面文本 → 论证骨架 JSON"""

import json
import os
import logging
from llm import chat, set_log_dir

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """你是一位专业的文本结构分析师。分析以下预处理后的视频文稿，提取其论证骨架。

你需要输出严格的JSON格式，不要输出任何其他内容：

{
  "overall_thesis": "全文核心论点（一句话概括）",
  "segments": [
    {
      "id": 1,
      "time_range": "原始文本中标记的时间戳范围，如 00:00-05:30",
      "topic": "本段主题（5-10字）",
      "main_claim": "这段话的核心主张是什么",
      "support_type": "因果分析 | 对比论证 | 层层递进 | 举例说明",
      "key_evidence": ["关键论据或事例1", "关键论据或事例2"],
      "relation_to_prev": "承接上文 | 转折 | 递进 | 新话题引入"
    }
  ]
}

分析要求：
- segment数量控制在3-8个，每个segment覆盖一个独立主题段落
- 识别说话者的论证逻辑线：是用因果分析、对比论证、层层递进、还是举例说明？
- relation_to_prev描述本段和前一段的逻辑关系
- 第一个segment的relation_to_prev填"新话题引入"
- key_evidence列出本段中支撑论点的具体事例或数据

严格遵守：
- 输出必须是**完整的纯JSON格式**，必须能被标准解析器正确解析,不要添加任何解释、注释或文本
- segment数量控制在3-8个，过多或过少都不符合要求

"""


def run(preprocessed_path: str, output_dir: str, tier: str = "fast") -> str:
    """Run Stage 2. Returns path to 02_structure.json."""
    output_path = os.path.join(output_dir, "02_structure.json")
    if os.path.exists(output_path):
        logger.info("Stage 2 output already exists, skipping: %s", output_path)
        return output_path

    os.makedirs(output_dir, exist_ok=True)

    with open(preprocessed_path, "r", encoding="utf-8") as f:
        text = f.read()

    set_log_dir(os.path.join(output_dir, "llm_logs"))

    structure = _generate_structure(text, tier)

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(structure, f, indent=2, ensure_ascii=False)

    logger.info("Stage 2 output: %s (%d segments)", output_path, len(structure.get("segments", [])))
    return output_path


def _extract_json(raw: str) -> str:
    """Strip markdown fences and extract raw JSON string."""
    raw = raw.strip()
    if raw.startswith("```"):
        raw = raw.split("\n", 1)[-1]
        if raw.endswith("```"):
            raw = raw[:-3]
        raw = raw.strip()
    return raw


def _validate_segments(structure: dict, min_seg: int = 3, max_seg: int = 8) -> int | None:
    """Return None if valid, or 'too_few'/'too_many' hint string."""
    segments = structure.get("segments", [])
    n = len(segments)
    if min_seg <= n <= max_seg:
        return None
    return n


def _call_llm(prompt: str, tier: str, debug_label: str) -> dict:
    """Call LLM, extract JSON, parse it. Saves raw output to tmp/ on failure."""
    raw = chat(prompt, tier=tier, system=SYSTEM_PROMPT, step=2)
    raw = _extract_json(raw)
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        debug_path = os.path.join(os.path.dirname(__file__), "..", "tmp", f"structure_raw_{debug_label}.md")
        os.makedirs(os.path.dirname(debug_path), exist_ok=True)
        with open(debug_path, "w", encoding="utf-8") as f:
            f.write(raw)
        logger.error("Stage 2: LLM returned invalid JSON. Raw saved to %s", debug_path)
        raise


def _generate_structure(text: str, tier: str) -> dict:
    """Call LLM and retry once if segment count is out of range."""
    structure = _call_llm(f"请分析以下文稿的结构：\n\n{text}", tier, "first")

    n = _validate_segments(structure)
    if n is None:
        return structure

    logger.warning("Stage 2: %d segments out of range (3-8), retrying once", n)
    direction = "增加" if n < 3 else "减少"
    retry_prompt = (
        f"请重新分析以下文稿的结构。\n\n"
        f"原文：\n{text}\n\n"
        f"你之前生成的结果 segments 数量为 {n}，不符合 3-8 个的要求，请{direction}segment 数量至 3-8 个。\n"
        f"之前输出的内容供参考（仅参考segments数量，不要直接复制）：\n"
        f"{json.dumps(structure, indent=2, ensure_ascii=False)}"
    )
    return _call_llm(retry_prompt, tier, "retry")
