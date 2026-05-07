"""Simple mode: 字幕 → 文章 (一步到位，跳过中间中间产物)"""

import os
import logging
from utils.parser import parse, to_text
from llm import chat, set_log_dir

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """你是一位优秀的非虚构长文作者。你的任务是将视频字幕直接转化为一篇完整的深度文章，不需要经过中间步骤。

## 处理流程（你需自动完成）
1. **口语清理**：将碎片字幕合并为完整语句，去除填充词，书面化改写
2. **主题分段**：识别自然主题段落，梳理论证逻辑线
3. **深度挖掘**：在关键论点处自然融入背景知识和延伸分析
4. **文章撰写**：输出一篇有观点、有信息量、结构完整的文章

## 写作要求
- 字数控制在 4000-5000 字（根据字幕丰度自适应）
- 标题用 `#`，小标题用 `##`，Markdown 格式
- 标题控制在10-15个汉字，不要有特殊字符、空格、英文引号，要吸引眼球
- 语言流畅自然，有杂志长文质感
- 避免"首先/其次/最后/总的来说"等 AI 模板词
- 段落不宜过长，每段 10 句以内"""


def run(subtitle_path: str, output_dir: str, tier: str = "best") -> str:
    """Simple mode: parse subtitle → one-shot LLM call → article. Returns path."""
    output_path = os.path.join(output_dir, "04_article_simple.md")
    if os.path.exists(output_path):
        logger.info("Simple article already exists, skipping: %s", output_path)
        return output_path

    os.makedirs(output_dir, exist_ok=True)
    set_log_dir(os.path.join(output_dir, "llm_logs"))

    subtitles = parse(subtitle_path)
    raw_text = to_text(subtitles)
    logger.info("Parsed %d subtitle entries", len(subtitles))

    prompt = f"以下是视频字幕内容，请直接输出一篇完整的深度文章。\n\n{raw_text}"
    result = chat(prompt, tier=tier, system=SYSTEM_PROMPT, step=0)

    with open(output_path, "w", encoding="utf-8") as f:
        f.write(result)

    logger.info("Simple article output: %s", output_path)
    return output_path
