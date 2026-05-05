"""Stage 4: 所有材料 → 最终文章"""

import json
import os
import logging
from llm import chat, set_log_dir

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """
你是一位优秀的非虚构长文作者，擅长撰写知识性和观点性兼备的文章。

## 写作任务
基于提供的结构分析与深度挖掘笔记，撰写完整文章。

---

## 【硬性字数限制（必须严格遵守）】
- 最终全文字数必须在 4000–6000 字之间
- 不得低于 3800 字，不得超过 6200 字
- 若超过上限，必须压缩表达后再输出

---

## 【原创性与改写约束（必须严格执行）】
1. 不得直接复用输入中的原句（连续15字以上视为复用）
2. 必须对所有内容进行“重写表达”（同义改写 + 结构重组）
3. 保留核心事实，但表达方式要寻求改变
4. 与输入文本的整体重复度不得超过 50%
5. 优先使用：
   - 句式重构（长句→短句 / 逻辑重排）
   - 概念归纳（多句→一句总结）
   - 视角转换（叙述→分析）

---

## 【写作策略（必须执行）】
在写作前进行字数预算：
- 引言：300–400字
- 每个小节：400–700字
- 结尾：300–400字

---

## 【信息压缩原则】
当信息过多时：
1. 合并重复观点
2. 案例最多保留1个
3. 删除非必要背景
4. 禁止对同一概念重复解释

---

## 【结构要求】
- 使用 # 标题
- 开头提出问题或矛盾
- 使用 ## 小标题组织
- 结尾总结并留有思考空间

---

## 【语言要求】
中文书面语，表达克制，避免口语化和冗余修辞

---

## 【输出前强制自检（必须执行）】
1. 统计全文字数：
   - >6000：压缩
   - <4000：补充
2. 检查是否存在连续复用原文（>15字）：
   - 如存在，必须改写
3. 检查重复表达：
   - 删除或合并
4. 确保整体重复度 < 50%

---
"""


def _extract_sentences(structure: dict) -> str:
    """Extract and join all sentences from structure segments."""
    segments = structure.get("segments", [])
    lines = []
    for seg in segments:
        lines.extend(seg.get("sentences", []))
    return "\n".join(lines)


def run(structure_path: str, insights_path: str, output_dir: str, tier: str = "best") -> str:
    """Run Stage 4. Returns path to 04_article.md."""
    output_path = os.path.join(output_dir, "04_article.md")
    if os.path.exists(output_path):
        logger.info("Stage 4 output already exists, skipping: %s", output_path)
        return output_path

    os.makedirs(output_dir, exist_ok=True)

    with open(structure_path, "r", encoding="utf-8") as f:
        structure_data = json.load(f)
    with open(insights_path, "r", encoding="utf-8") as f:
        insights = json.load(f)
    insights_raw = json.dumps(insights, indent=2, ensure_ascii=False)

    structure_raw = json.dumps(structure_data, indent=2, ensure_ascii=False)

    prompt_parts = [
        "## 结构分析，内含原文：sentences",
        structure_raw,
        "",
        "## 深度挖掘笔记（JSON）",
        insights_raw,
        "",
        "请基于以上所有材料，撰写一篇完整的文章。",
    ]
    set_log_dir(os.path.join(output_dir, "llm_logs"))
    prompt = "\n\n".join(prompt_parts)

    result = chat(prompt, tier=tier, system=SYSTEM_PROMPT, step=4)

    with open(output_path, "w", encoding="utf-8") as f:
        f.write(result)

    logger.info("Stage 4 output: %s", output_path)
    return output_path
