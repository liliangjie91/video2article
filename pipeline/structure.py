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
- key_evidence列出本段中支撑论点的具体事例或数据"""


def run(preprocessed_path: str, output_dir: str, tier: str = "best") -> str:
    """Run Stage 2. Returns path to 02_structure.json."""
    os.makedirs(output_dir, exist_ok=True)

    with open(preprocessed_path, "r", encoding="utf-8") as f:
        text = f.read()

    set_log_dir(os.path.join(output_dir, "llm_logs"))
    prompt = f"请分析以下文稿的结构：\n\n{text}"
    raw = chat(prompt, tier=tier, system=SYSTEM_PROMPT)

    # Strip markdown code fences if present
    raw = raw.strip()
    if raw.startswith("```"):
        raw = raw.split("\n", 1)[-1]
        if raw.endswith("```"):
            raw = raw[:-3]
        raw = raw.strip()

    structure = json.loads(raw)

    output_path = os.path.join(output_dir, "02_structure.json")
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(structure, f, indent=2, ensure_ascii=False)

    logger.info("Stage 2 output: %s (%d segments)", output_path, len(structure.get("segments", [])))
    return output_path
