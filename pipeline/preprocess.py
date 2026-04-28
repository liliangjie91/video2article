"""Stage 1: 口语字幕 → 书面文本段落"""

import os
import logging
from utils.parser import parse, to_text
from llm import chat, set_log_dir

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """
你是一位字幕数据清洗专家。你的任务是将原始视频字幕（ASR 转录文本）整理为结构清晰、表达通顺但信息完全等价的文本。

核心原则（必须严格遵守）：

1. 信息完整性优先：不得删除任何独立信息点（观点、事实、例子、数据、因果关系等）；不得因合并而造成信息损失；宁可略显冗余，也不能遗漏信息
2. 禁止总结与改写：不得对内容进行概括、总结或压缩表达；不得改变信息粒度（不能把多句话提炼为一句）；不得引入原文没有的新表达或新结构
3. 仅允许轻度编辑：只允许在不改变原意的前提下进行最小限度的整理

处理规则：

1. 断句合并：将碎片字幕拼接为完整句子或自然段落
2. 文本去噪：删除语气词、杂音文本和无意义重复
3. 去重限制：仅删除完全重复内容；存在任何信息差异的表达必须保留
4. 表达修复：只修复不重写，保持原有信息密度与表达结构
5. 段落划分：按语义自然分段，在保证信息清晰的前提下尽量合并段落，避免过度切分
6. 段落数量限制：最终输出段落总数不得超过15个；如原内容分散，应优先合并相邻同主题内容，而不是增加段落数量
7. 缺失注明：仅在有充分依据判断文本存在缺失时，才添加“<文本可能部分缺失>”，不得滥用

输出格式：

* 输出为纯文本段落
* 段落内的句子使用回车换行分隔
* 段落之间空一行
* 去除时间标记
* 不得添加标题或任何额外说明文字

行为边界：
你是在修复和整理字幕，而不是进行内容创作；只能整理表达，不得提炼或改写内容。
"""


def run(subtitle_path: str, output_dir: str, tier: str = "fast") -> str:
    """Run Stage 1. Returns path to 01_preprocessed.txt."""
    output_path = os.path.join(output_dir, "01_preprocessed.txt")
    if os.path.exists(output_path):
        logger.info("Stage 1 output already exists, skipping: %s", output_path)
        return output_path

    os.makedirs(output_dir, exist_ok=True)

    subtitles = parse(subtitle_path)
    raw_text = to_text(subtitles)
    logger.info("Parsed %d subtitle entries", len(subtitles))

    set_log_dir(os.path.join(output_dir, "llm_logs"))
    prompt = f"以下是需要整理的视频字幕：\n\n{raw_text}"
    result = chat(prompt, tier=tier, system=SYSTEM_PROMPT, step=1)

    with open(output_path, "w", encoding="utf-8") as f:
        f.write(result)

    logger.info("Stage 1 output: %s", output_path)
    return output_path
