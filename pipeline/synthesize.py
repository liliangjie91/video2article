"""Stage 5: 大纲 + 材料 → 逐段合成文章"""

import json
import os
import logging
from llm import chat, set_log_dir

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """你是一位优秀的非虚构长文作者，擅长撰写知识性和观点性兼备的文章。

## 写作任务
根据提供的大纲段落定义和相关的分析材料，撰写该段落的内容。

## 要求
- 输出必须以 `## {段落标题}` 开头，后续内容为该段落的正文
- 中文书面语，表达克制，简介有力，避免口语化和冗余修辞
- 不得直接复用原文中的句子（连续15字以上视为复用）
- 保留核心事实，但表达方式要寻求改变
- 严格遵守字数预算

输出只包含段落正文内容，不要输出"段落标题"、不要输出额外说明。"""


def _find_source_url(output_dir: str) -> str | None:
    """Try to find source URL from srt filename in output directory."""
    try:
        for fname in os.listdir(output_dir):
            if fname.endswith(".srt") and not fname.startswith("01_"):
                base = os.path.splitext(fname)[0]
                if len(base) > 5:  # reasonable video ID
                    return f"https://youtu.be/{base}"
    except OSError:
        pass
    return None


def run(insights_path: str, outline_path: str, output_dir: str, tier: str = "best") -> str:
    """Run Stage 5 (outline-driven synthesis). Returns path to 05_article.md."""
    output_path = os.path.join(output_dir, "05_article.md")
    if os.path.exists(output_path):
        logger.info("Stage 5 output already exists, skipping: %s", output_path)
        return output_path

    os.makedirs(output_dir, exist_ok=True)

    with open(outline_path, "r", encoding="utf-8") as f:
        outline_data = json.load(f)
    with open(insights_path, "r", encoding="utf-8") as f:
        insights_data = json.load(f)

    set_log_dir(os.path.join(output_dir, "llm_logs"))

    meta = outline_data.get("meta", {})
    title = meta.get("title", "")
    outline_segments = outline_data.get("outline", [])
    all_segments = insights_data.get("segments", [])
    seg_map = {s.get("id"): s for s in all_segments}

    # Title
    article_parts = [f"# {title}"] if title else []

    # Segments
    for i, oseg in enumerate(outline_segments):
        logger.info(
            "Writing outline segment %d/%d: %s",
            i + 1, len(outline_segments), oseg.get("heading", ""),
        )

        # Collect context from referenced source segments
        context_parts = []
        for sid in oseg.get("source_segment_ids", []):
            seg = seg_map.get(sid)
            if seg:
                insight = seg.get("insight", {})
                context_parts.append(
                    f"## 原文段落 {sid}：{seg.get('topic', '')}\n"
                    f"核心主张：{seg.get('main_claim', '')}\n"
                    f"原文：{' '.join(seg.get('sentences', []))}\n"
                    f"---\n"
                    f"深度分析：{insight.get('core_summary', '')}\n"
                    f"背景补充：{insight.get('background', '')}\n"
                    f"延伸关联：{insight.get('connections', '')}"
                )

        prompt_parts = [
            f"全文核心论点：{insights_data.get('overall_thesis', '未知')}",
            "",
            "## 参考材料",
            "\n\n".join(context_parts),
            "",
            f"## 当前写作任务：{oseg.get('heading', '')}",
            f"**严格遵守字数预算**：{oseg.get('word_count_estimate', 500)} 字",
            f"关键论点：{'；'.join(oseg.get('key_points', []))}",
            "",
            "请根据以上大纲和参考材料，撰写此段落。",
        ]
        prompt = "\n".join(prompt_parts)

        result = chat(prompt, tier=tier, system=SYSTEM_PROMPT, step=5)
        article_parts.extend(["", result])
    
    # Source attribution
    source_url = _find_source_url(output_dir)
    if source_url:
        article_parts.append(f"\n> 来源：{source_url}")

    article_text = "\n".join(article_parts)
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(article_text)

    logger.info("Stage 5 output: %s (%d segments)", output_path, len(outline_segments))
    return output_path
