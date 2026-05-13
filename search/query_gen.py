"""Filter and refine outline search queries based on article context."""

import json
import logging
import os

from llm import chat

logger = logging.getLogger(__name__)

_SYSTEM = """你是一位搜索词优化编辑。你的任务是根据文章主题对候选搜索词进行筛选和优化。

## 规则
1. **去重过滤** — 删除意思重复的词，删除与文章主题明显无关的词（如广告词、不相关插播内容中的词）
2. **长度控制** — 每个词保持 2-5 个汉字，过长的词要精简，过短的词需结合上下文判断
3. **贴合主题** — 只保留对理解文章核心内容有检索价值的词
4. **适度修改** — 如有必要可对检索词做简单修改（删字、加字、换词），但不要过度改写
5. **数量控制** - 最终输出控制在5-7个词以内，不要只保留前面的而舍弃后面的词。

## 输出格式
纯文本，每行一个词，不要编号之外的任何格式：
1. 词1
2. 词2"""


def run(outline_path: str, tier: str = "fast") -> str:
    """Filter and refine ``search_queries`` in the outline JSON in-place.

    Reads ``04_outline.json``, sends its ``search_queries`` + article context
    to LLM for filtering/refinement, and writes the result back to the same file.

    Returns the (same) *outline_path*.
    """
    from utils.logging import log_banner
    log_banner("搜索词筛选", "Query Gen")

    with open(outline_path, "r", encoding="utf-8") as f:
        outline = json.load(f)

    queries = outline.get("search_queries", [])
    if not queries:
        logger.info("No search_queries to filter")
        return outline_path

    # Build context: title + section headings
    title = outline.get("meta", {}).get("title", "")
    headings = [s.get("heading", "") for s in outline.get("outline", []) if s.get("heading")]

    prompt_parts = [f"## 文章标题\n{title}\n"]
    if headings:
        prompt_parts.append("## 文章章节\n" + "\n".join(f"- {h}" for h in headings))
    prompt_parts.append("\n## 候选检索词（请逐条评估）")
    for i, q in enumerate(queries, 1):
        prompt_parts.append(f"{i}. {q}")
    prompt_parts.append("\n请筛选并优化以上检索词，保留贴合文章主题且有检索价值的词。")

    raw = chat("\n".join(prompt_parts), tier=tier, system=_SYSTEM, step=0)

    refined = _parse_output(raw)

    if not refined:
        logger.info("LLM returned empty result, keeping original queries")
        return outline_path

    logger.info("Refined %d queries → %d", len(queries), len(refined))
    outline["search_queries"] = refined

    with open(outline_path, "w", encoding="utf-8") as f:
        json.dump(outline, f, indent=2, ensure_ascii=False)

    return outline_path


def _parse_output(raw: str) -> list[str]:
    """Parse LLM numbered-list output into a list of query strings."""
    results: list[str] = []
    for line in raw.strip().splitlines():
        line = line.strip()
        # Match "1. xxx" or "1、xxx" or "- xxx"
        text = line
        for sep in (". ", "、", ".", ") "):
            parts = line.split(sep, 1)
            if parts[0].isdigit() and len(parts) > 1:
                text = parts[1].strip()
                break
        if line.startswith("- "):
            text = line[2:].strip()
        if text and text != line:
            results.append(text)
    return results
