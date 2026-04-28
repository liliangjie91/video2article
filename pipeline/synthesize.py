"""Stage 4: 所有材料 → 最终文章"""

import os
import logging
from llm import chat, set_log_dir

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """你是一位优秀的非虚构长文作者，擅长撰写知识性和观点性兼备的文章。你的文章有深度、有观点、读起来流畅自然。

## 写作任务

你将收到以下材料：
1. 视频字幕的预处理文稿
2. 文稿的结构分析（主题分段、论证骨架）
3. 深度挖掘笔记（每段的深层分析）

请基于这些材料撰写一篇完整的文章。

## 写作要求

**风格**：根据内容类型选择——
- 科普类（科学、技术、自然）：解释性报道风格，清晰、准确、引人入胜
- 历史类（历史事件、人物、文化）：叙事评论风格，有故事感、有历史纵深

**结构**：
- 一个吸引人的标题（用 # 标记）
- 开头段落点出文章的核心问题或引人思考的矛盾，不要平铺直叙
- 用 ## 小标题组织文章主干
- 结尾要有总结性和留给人思考的空间

**深度融入**：
- 将挖掘笔记中的洞见自然融入文章，不要生硬地写成"补充说明"或"背景知识"栏目
- 背景知识应该在叙述中被自然带出，观点应该在分析中流露

**字数**：2000-4000字（根据材料丰度自适应，不要强行凑字数）

**语言**：中文书面语，流畅自然，有杂志长文质感"""


def run(preprocessed_path: str, structure_path: str, insights_path: str, output_dir: str, tier: str = "best") -> str:
    """Run Stage 4. Returns path to 04_article.md."""
    output_path = os.path.join(output_dir, "04_article.md")
    if os.path.exists(output_path):
        logger.info("Stage 4 output already exists, skipping: %s", output_path)
        return output_path

    os.makedirs(output_dir, exist_ok=True)

    with open(preprocessed_path, "r", encoding="utf-8") as f:
        preprocessed = f.read()
    with open(structure_path, "r", encoding="utf-8") as f:
        structure = f.read()
    with open(insights_path, "r", encoding="utf-8") as f:
        insights = f.read()

    prompt_parts = [
        "## 预处理后的文稿",
        preprocessed,
        "",
        "## 结构分析",
        structure,
        "",
        "## 深度挖掘笔记",
        insights,
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
