"""Post-process article: insert inline citation links from search references."""

import json
import logging
import os
import re

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
- 所有标题层级（#、##）保持不动
- **以下链接和锚文本在本段落之前已经使用过，请勿重复使用**
	- 同一个关键词在一篇文章中只应添加一次链接（无论链接到哪个 URL）"""


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


def _extract_used_urls(text: str) -> set[str]:
    """Extract all markdown link URLs from text."""
    return set(re.findall(r'\]\(([^)]+)\)', text))


def _extract_linked_words(text: str) -> set[str]:
    """Extract all markdown link anchor text from text."""
    return set(re.findall(r'\[([^\]]+)\]\(', text))


def _append_references(article: str, url_title_map: dict[str, str], used_urls: set[str]) -> str:
    """Append a ``参考资料`` section listing all cited URLs."""
    cited = [(url, url_title_map.get(url, url)) for url in used_urls if url]
    if not cited:
        return article

    ref_lines = ["", "", "## 参考资料"]
    for i, (url, title) in enumerate(cited, 1):
        ref_lines.append(f"{i}. [{title}]({url})")

    return article + "\n".join(ref_lines)


def run(article_path: str, references_path: str, output_dir: str, tier: str = "best") -> str:
    """Post-process article to add inline citation links.

    Reads the generated article + aggregated search references, and uses LLM
    to insert ``[word](url)`` links where relevant.  Tracks used URLs across
    sections to avoid duplicate links.  Appends a ``参考资料`` section at end.

    Returns path to the linked article (overwrites original).
    """
    from pipeline._utils import log_banner
    log_banner("引用链接插入", "Link Insertion")

    with open(article_path, "r", encoding="utf-8") as f:
        article = f.read()

    with open(references_path, "r", encoding="utf-8") as f:
        refs_data = json.load(f)

    refs = refs_data.get("references", [])
    if not refs:
        logger.info("No search references available, skipping link insertion")
        return article_path

    # Build URL → title mapping (for references section)
    url_title = {r["url"]: r["title"] for r in refs if r.get("url")}

    set_log_dir(os.path.join(output_dir, "llm_logs"))

    # Build reference block (top 15)
    ref_block_lines = []
    for i, r in enumerate(refs[:15], 1):
        ref_block_lines.append(f"{i}. [{r['title']}]({r['url']})")
        if r.get("snippet"):
            ref_block_lines.append(f"   {r['snippet'][:300]}")
    ref_block = "\n".join(ref_block_lines)

    # Process article section by section, tracking used URLs and linked words
    sections = _section_texts(article)
    linked_lines = []
    used_urls: set[str] = set()
    linked_words: set[str] = set()

    for sec_text, start, end in sections:
        if not sec_text.strip():
            linked_lines.append(sec_text)
            continue

        # Skip TL;DR line and source attribution
        first_line = sec_text.split("\n")[0].strip()
        if first_line.startswith("> **TL;DR") or first_line.startswith("> 来源"):
            linked_lines.append(sec_text)
            continue

        # Warn LLM about already-used URLs and linked words
        used_hint = ""
        if used_urls or linked_words:
            parts = []
            if used_urls:
                ulist = "\n".join(f"  - {url_title.get(u, u)}" for u in sorted(used_urls))
                parts.append(f"已用过的链接（请勿重复）：\n{ulist}")
            if linked_words:
                wlist = "\n".join(f"  - {w}" for w in sorted(linked_words))
                parts.append(f"已链接过的词（请勿再次添加链接）：\n{wlist}")
            used_hint = "\n\n" + "\n\n".join(parts)

        prompt = (
            f"## 可引用的搜索结果\n{ref_block}\n\n"
            f"## 待处理段落\n{sec_text}{used_hint}\n\n"
            f"请在上方段落中插入引用链接，保持原文完全不变。"
        )

        result = chat(prompt, tier=tier, system=_SYSTEM_PROMPT, step=6)
        linked_lines.append(result.strip())

        # Track any new URLs and linked words inserted in this section
        used_urls |= _extract_used_urls(result)
        linked_words |= _extract_linked_words(result)

    linked_article = "\n".join(linked_lines)

    # Append references section
    linked_article = _append_references(linked_article, url_title, used_urls)

    with open(article_path, "w", encoding="utf-8") as f:
        f.write(linked_article)

    logger.info("Link insertion complete: %s (%d unique URLs cited)", article_path, len(used_urls))
    return article_path
