"""Post-process article: insert inline citation links from search references."""

import json
import logging
import os

from llm import chat, set_log_dir

logger = logging.getLogger(__name__)

_SYSTEM_PROMPT = """你是一位精编校对。你的任务是在已有文章中添加引用链接，不改动原文内容。

## 规则
- 在文章中找到与搜索结果明显相关的短语/关键词，插入内联链接：`[词](url)`
- 方括号内只放 1-2 个词（最多 10 个字），如 `[Karpathy](url)` 或 `[深度求索](url)`
- 链接必须放在句中自然的位置
- 只有确认内容匹配时才加，不要无中生有
- 不要改变原文任何文字和标点（仅插入链接标记）
- 不要添加新的句子或改写原文
- 所有标题层级（#、##）保持不动"""


def _section_texts(article: str) -> list[tuple[str, int, int]]:
    """Split article into sections by heading lines.

    Returns ``[(text, start_line, end_line), ...]``.
    """
    lines = article.split("\n")
    sections = []
    start = 0
    for i, line in enumerate(lines):
        if line.startswith("## ") and i > 0:
            sections.append(("\n".join(lines[start:i]), start, i))
            start = i
    sections.append(("\n".join(lines[start:]), start, len(lines)))
    return sections


def run(article_path: str, references_path: str, output_dir: str, tier: str = "best") -> str:
    """Post-process article to add inline citation links.

    Reads the generated article + aggregated search references, and uses LLM
    to insert ``[word](url)`` links where relevant.

    Returns path to the linked article (overwrites original).
    """
    with open(article_path, "r", encoding="utf-8") as f:
        article = f.read()

    with open(references_path, "r", encoding="utf-8") as f:
        refs_data = json.load(f)

    refs = refs_data.get("references", [])
    if not refs:
        logger.info("No search references available, skipping link insertion")
        return article_path

    set_log_dir(os.path.join(output_dir, "llm_logs"))

    # Build a compact reference block for the LLM (top 15)
    ref_block_lines = []
    for i, r in enumerate(refs[:15], 1):
        ref_block_lines.append(f"{i}. [{r['title']}]({r['url']})")
        if r["snippet"]:
            ref_block_lines.append(f"   {r['snippet'][:300]}")
    ref_block = "\n".join(ref_block_lines)

    # Process article section by section
    sections = _section_texts(article)
    linked_lines = []

    # The first section is the title (starts with #); process it separately if needed
    for sec_text, start, end in sections:
        if not sec_text.strip():
            linked_lines.append(sec_text)
            continue

        # Skip TL;DR line and source attribution
        first_line = sec_text.split("\n")[0].strip()
        if first_line.startswith("> **TL;DR") or first_line.startswith("> 来源"):
            linked_lines.append(sec_text)
            continue

        prompt = (
            f"## 可引用的搜索结果\n{ref_block}\n\n"
            f"## 待处理段落\n{sec_text}\n\n"
            f"请在上方段落中插入引用链接，保持原文完全不变。"
        )

        result = chat(prompt, tier=tier, system=_SYSTEM_PROMPT, step=6, log_prompt=False)
        linked_lines.append(result.strip())

    linked_article = "\n".join(linked_lines)

    with open(article_path, "w", encoding="utf-8") as f:
        f.write(linked_article)

    logger.info("Link insertion complete: %s", article_path)
    return article_path
