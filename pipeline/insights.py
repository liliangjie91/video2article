"""Stage 3: 文本 + 骨架 → 深度挖掘笔记 (核心)"""

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

## 关键约束
- 禁止复述原文内容，必须在原文之上增加新价值
- 每个维度写1-3句话即可，但要具体有料
- 背景知识不确定时标注[推测]
- 使用Markdown格式，以"## 段落 N: [主题]\"开头"""


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


def run(structure_path: str, output_dir: str, tier: str = "best") -> str:
    """Run Stage 3. Returns path to 03_insights.md."""
    output_path = os.path.join(output_dir, "03_insights.md")
    if os.path.exists(output_path):
        logger.info("Stage 3 output already exists, skipping: %s", output_path)
        return output_path

    os.makedirs(output_dir, exist_ok=True)

    with open(structure_path, "r", encoding="utf-8") as f:
        structure = json.load(f)

    set_log_dir(os.path.join(output_dir, "llm_logs"))
    segments = structure.get("segments", [])
    parts = []

    for i, seg in enumerate(segments):
        logger.info("Analyzing segment %d/%d: %s", seg["id"], len(segments), seg.get("topic", ""))
        prompt_parts = [
            f"以下是一个视频文稿的深度分析任务。",
            f"全文核心论点: {structure.get('overall_thesis', '未知')}",
            "",
            "当前需要分析的段落：",
            _build_segment_prompt(seg),
            "",
            "请从五个维度（核心提炼、隐含假设、背景补充、延伸关联、批判追问）分析这段话。",
        ]
        prompt = "\n".join(prompt_parts)

        raw = chat(prompt, tier=tier, system=SYSTEM_PROMPT, step=3)
        parts.append(raw)

        if i < len(segments) - 1:
            parts.append("\n---\n")

    output = "\n".join(parts)

    with open(output_path, "w", encoding="utf-8") as f:
        f.write(output)

    logger.info("Stage 3 output: %s", output_path)
    return output_path
