"""Stage 2: 书面文本 → 论证骨架 JSON"""

import json
import os
import logging
from llm import chat, set_log_dir
from utils import safe_parse_json, extract_json

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """你是一名文本结构分析专家。你的任务是将一组已经清洗过的句子，按照“语义主题”进行分段，并提取每段的关键信息。

【输入】
一组按时间顺序排列的段落/句子（已去除口语和噪声）。

【任务要求】
1. 按“语义主题”分段，而不是按句子数量或时间均分
2. 每个分段必须满足：
   - 语义上属于同一主题
   - 内部句子之间有逻辑连续性
3. 当出现以下情况时必须切分：
   - 话题发生变化
   - 从观点切换到例子
   - 从解释切换到新结论
4. 每个分段需要输出的字段见下方输出格式要求
5. 分段数量控制在 3~8 段之间（根据内容合理调整）
6. 不允许删除任何句子，所有句子必须被分配到某个分段
7. 保持原始句子内容，不得改写

【输出格式（必须严格JSON）】
{
  "overall_thesis": "全文核心论点（一句话概括）",
  "segments": [
    {
      "id": 1,
      "topic": "本段主题（5-10字）",
      "relation_to_prev": "承接上文 | 转折 | 递进 | 新话题引入",
      "main_claim": "这段话的核心主张是什么（50-100字）",
      "key_points": ["本段的关键点1", "本段的关键点2"],
      "sentences": ["原文句子1", "原文句子2"]
    }
  ]
}

分析要求：
- 每个segment覆盖一个独立主题段落
- 识别说话者的论证逻辑线：是用因果分析、对比论证、层层递进、还是举例说明？
- relation_to_prev描述本段和前一段的逻辑关系
- 第一个segment的relation_to_prev填"新话题引入"

严格遵守：
- 输出必须是**完整的纯JSON格式**，必须能被标准解析器正确解析,不要添加任何解释、注释或文本
- segment数量控制在3-6个，过多或过少都不符合要求
- **字段内容中使用引号时，务必使用中文引号「」代替英文双引号，防止JSON解析失败**

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


def _validate_segments(structure: dict, min_seg: int = 3, max_seg: int = 6) -> int | None:
    """Return None if valid, or 'too_few'/'too_many' hint string."""
    segments = structure.get("segments", [])
    n = len(segments)
    if min_seg <= n <= max_seg:
        return None
    return n


def _call_llm(prompt: str, tier: str, debug_label: str) -> dict:
    """Call LLM, extract JSON, parse it. Saves raw output to tmp/ on failure."""
    raw = chat(prompt, tier=tier, system=SYSTEM_PROMPT, step=2)
    raw = extract_json(raw)
    try:
        return safe_parse_json(raw)
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

    logger.warning("Stage 2: %d segments out of range (3-6), retrying once", n)
    direction = "增加" if n < 3 else "减少"
    retry_prompt = (
        f"请重新分析以下文稿的结构。\n\n"
        f"原文：\n{text}\n\n"
        f"你之前生成的结果 segments 数量为 {n}，不符合 3-6 个的要求，请{direction}segment 数量至 3-6 个。\n"
        f"之前输出的内容供参考（仅参考segments数量，不要直接复制）：\n"
        f"{json.dumps(structure, indent=2, ensure_ascii=False)}"
    )
    return _call_llm(retry_prompt, tier, "retry")
