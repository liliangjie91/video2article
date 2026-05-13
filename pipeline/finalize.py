"""Post-process article: insert inline citation links and TL;DR."""

import json
import logging
import os
import re

from llm import chat, set_log_dir

logger = logging.getLogger(__name__)

_COMBINED_SYSTEM = """你是一位精编校对。你的任务是在已有文章中插入引用链接和TL;DR摘要，不改动原文其他内容。

## 链接规则
- 遍历每条搜索结果，在文章中找到与之相关的内容，插入内联链接：`[词](url)`
- 方括号内只放 1-2 个词（最多 10 个字），如 `[Karpathy](url)` 或 `[深度求索](url)`
- 链接必须放在句中自然的位置
- 对每一条搜索结果，如果文章中存在与之相关的话题或关键词，**必须添加链接**
- **格式要求**：`[词]` 后面必须紧跟 `(url)`，不允许出现 `[词]` 不带 `(url)` 的情况
- 不要改变原文任何文字和标点（仅插入链接标记），不要添加新句子
- 所有标题层级（#、##）保持不动
- 同一关键词在一篇文章中只应添加一次链接

## TL;DR 要求
- 在标题（`# ...`）下方另起一行插入 `> **TL;DR** ...`
- 用一段话概括全文核心内容，200字以内
- 不要添加额外标题或说明

## 输出要求
输出完整的文章（包含所有插入的链接和TL;DR）。"""


def _generate_tldr(article_text: str, tier: str) -> str:
    """Generate a brief TL;DR of the full article (≤300 chars)."""
    prompt = (
        f"请用一段话概括以下文章的核心内容，200字以内，不要加标题或前缀：\n\n"
        f"{article_text}"
    )
    tl_dr = chat(prompt, tier=tier, system="你是一位精炼的摘要写手。", step=5)
    tl_dr = tl_dr.strip()
    was_truncated = len(tl_dr) > 200
    tl_dr = tl_dr[:200]
    for sep in ("。", "！", "？"):
        idx = tl_dr.rfind(sep)
        if idx > 20:
            tl_dr = tl_dr[: idx + 1]
            break
    if was_truncated:
        tl_dr += "……"
    return tl_dr


def _insert_tldr(article: str, tl_dr: str) -> str:
    """Insert ``> **TL;DR** ...`` after the first ``# `` title line."""
    lines = article.split("\n")
    for i, line in enumerate(lines):
        if line.startswith("# "):
            tl_dr_line = f"> **TL;DR** {tl_dr}"
            insert_at = i + 1
            if insert_at < len(lines) and lines[insert_at] == "":
                insert_at += 1
            lines.insert(insert_at, "")
            lines.insert(insert_at, tl_dr_line)
            break
    return "\n".join(lines)


def _extract_used_urls(text: str) -> set[str]:
    """Extract all markdown link URLs from text."""
    return set(re.findall(r'\]\(([^)]+)\)', text))


def _append_references(article: str, url_title_map: dict[str, str], used_urls: set[str]) -> str:
    """Append a ``参考资料`` section listing all cited URLs."""
    cited = [(url, url_title_map.get(url, url)) for url in used_urls if url]
    if not cited:
        return article

    ref_lines = ["", "", "## 参考资料"]
    for i, (url, title) in enumerate(cited, 1):
        ref_lines.append(f"{i}. [{title}]({url})")

    return article + "\n".join(ref_lines)


def run(
    article_path: str, output_dir: str, tier: str = "best",
    references_path: str | None = None,
) -> str:
    """Post-process article: add TL;DR, and optionally insert citation links.

    When *references_path* is provided, inserts links + TL;DR in a single LLM
    call and appends a ``参考资料`` section.  Otherwise only generates TL;DR.

    Always writes ``05_article_link.md`` (does NOT overwrite the original).
    Returns path to ``05_article_link.md``.
    """
    from utils.logging import log_banner
    label = "引用链接 + TL;DR" if references_path else "TL;DR 生成"
    log_banner(label, "Link & TL;DR" if references_path else "TL;DR")

    output_path = os.path.join(output_dir, "05_article_link.md")
    if os.path.exists(output_path):
        logger.info("Linked article already exists, skipping: %s", output_path)
        return output_path

    with open(article_path, "r", encoding="utf-8") as f:
        article = f.read()

    set_log_dir(os.path.join(output_dir, "llm_logs"))

    used_urls: set[str] = set()
    url_title: dict[str, str] = {}

    if references_path:
        with open(references_path, "r", encoding="utf-8") as f:
            refs_data = json.load(f)

        refs = refs_data.get("references", [])
        if refs:
            url_title = {r["url"]: r["title"] for r in refs if r.get("url")}

            ref_lines = []
            for i, r in enumerate(refs[:15], 1):
                ref_lines.append(f"{i}. [{r['title']}]({r['url']})")
                if r.get("snippet"):
                    ref_lines.append(f"   {r['snippet'][:200]}")
            ref_block = "\n".join(ref_lines)

            prompt = (
                f"## 可引用的搜索结果\n{ref_block}\n\n"
                f"## 全文\n{article}\n\n"
                f"请对上文中所有与搜索结果相关的内容添加链接，并在标题下生成TL;DR。"
                f"每条搜索结果至少添加一个链接，确保所有链接格式为 [词](url)。"
            )
            result = chat(prompt, tier=tier, system=_COMBINED_SYSTEM, step=6)
            article = result.strip()
            used_urls = _extract_used_urls(article)
            logger.info("Combined processing: %d unique URLs cited, TL;DR inserted", len(used_urls))
        else:
            logger.info("No search references available, skipping link insertion")

    # ── TL;DR-only path (no references) ────────────────────────────
    if not references_path:
        tl_dr = _generate_tldr(article, tier)
        article = _insert_tldr(article, tl_dr)
        logger.info("TL;DR generated and inserted")

    # ── References section ─────────────────────────────────────────
    if used_urls:
        article = _append_references(article, url_title, used_urls)

    with open(output_path, "w", encoding="utf-8") as f:
        f.write(article)

    logger.info("Link article complete: %s", output_path)
    return output_path
