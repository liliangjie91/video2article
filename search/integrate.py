"""Aggregate search results into clean deduplicated references."""

import json
import logging
import os

from utils import extract_json, safe_parse_json

logger = logging.getLogger(__name__)

_DEDUP_SYSTEM = """你是一名搜索结果整合专家。你的任务是对原始搜索结果进行清洗和整合。

## 要求
1. **去重**：根据标题和摘要的语义相似度合并重复条目，保留信息最完整的版本
2. **过滤**：剔除低质量内容（如论坛灌水、明显不相关的内容、聚合页、商业推广页、SEO 垃圾站）
3. **权威优先**：优先保留百科类结果（如知乎、维基百科、百度百科、36氪、财新、新华社、人民日报、学术论文、政府/机构官网等）
4. **时效把关**：剔除明显过时的文章（2 年以上的旧闻），除非百科类
5. **关键词**：为每个结果提取 2-4 个核心关键词-只能从query和title中提取，不可发散。
6. **排序**：按综合质量从高到低排列（高权威 + 高时效 + 高相关优先）
7. **精简输出**：每个检索，最多只保留最优的1条内容。严格遵守

## 输出格式
输出纯 JSON 数组，每个元素包含query、title、url、snippet、keywords 五个字段，其中query即检索词，其他内容为检索结果及拆分：
```json
[
  {"query": "...", "title": "...", "url": "...", "snippet": "...", "keywords": ["关键词1", "关键词2"]}
]
```"""


def _parse_llm_output(raw: str) -> list[dict]:
    """Try to parse LLM JSON output, with basic cleanup."""
    raw = extract_json(raw)
    result = safe_parse_json(raw)
    if not isinstance(result, list):
        raise ValueError("LLM output not a list")
    return result


def integrate_search_res(raw_path: str, output_dir: str, tier: str = "fast") -> str:
    """Deduplicate, filter and rank raw search results using LLM.

    Reads a JSON file of raw results (flat ``[{"title", "url", "snippet"}, ...]``),
    sends them to LLM for dedup/filter/rank, and writes ``search_references.json``
    with enriched entries (title, url, snippet, keywords).

    Returns path to ``search_references.json``.
    """
    from utils.logging import log_banner
    log_banner("搜索结果整合", "Search Integrate")
    from llm import chat

    output_path = os.path.join(output_dir, "search_references.json")
    if os.path.exists(output_path):
        logger.info("Stage search integrate output already exists, skipping: %s", output_path)
        return output_path
    logger.info("start integeate search res file %s", raw_path)
    with open(raw_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    raw_results = data if isinstance(data, list) else data.get("results", [])
    if not raw_results:
        logger.info("No search results to process")
        output = {"references": [], "total": 0}
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(output, f, indent=2, ensure_ascii=False)
        return output_path

    lines = [f"以下是从搜索引擎收集到的 {len(raw_results)} 条原始结果，请整合去重：", ""]
    for i, r in enumerate(raw_results, 1):
        lines.append(f"[{i}] Query: {r['query']}")
        lines.append(f"    Title: {r['title']}")
        lines.append(f"    URL: {r['url']}")
        if r.get("snippet"):
            lines.append(f"    摘要: {r['snippet'][:600]}")
    prompt = "\n".join(lines)

    raw_output = chat(prompt, tier=tier, system=_DEDUP_SYSTEM, step=0)
    try:
        refs = _parse_llm_output(raw_output)
        if not isinstance(refs, list):
            raise ValueError("LLM output not a list")
    except Exception as e:
        logger.warning("LLM dedup failed (%s), falling back to rule-based", e)
        seen: set[str] = set()
        refs = []
        for r in raw_results:
            if r["url"] not in seen:
                seen.add(r["url"])
                r["keywords"] = []
                refs.append(r)

    logger.info("LLM integrated %d raw results → %d references", len(raw_results), len(refs))
    output = {"references": refs, "total": len(refs)}
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(output, f, indent=2, ensure_ascii=False)
    return output_path


def search_from_outline(outline_path: str, output_dir: str, tier: str) -> str | None:
    """Execute searches from outline's preselected queries.

    Reads ``04_outline.json``, takes its ``search_queries``, executes them,
    and writes raw results to ``search_raw.json`` (flat list of results).

    Returns path to ``search_raw.json``, or ``None`` if no queries or engines.
    """
    from utils.logging import log_banner
    log_banner("联网搜索", "Web Search")
    raw_search_path = os.path.join(output_dir, "search_raw.json")
    if os.path.exists(raw_search_path):
        logger.info("Stage search raw output already exists, skipping: %s", raw_search_path)
        return raw_search_path

    from search import get_configured_engines, search as do_search

    engines = get_configured_engines()
    if not engines:
        logger.info("No search engines configured, skipping outline search")
        return None

    with open(outline_path, "r", encoding="utf-8") as f:
        outline = json.load(f)

    queries = outline.get("search_queries", [])
    if not queries:
        logger.info("No search queries in outline, skipping search")
        return None

    logger.info("Executing %d search queries from outline", len(queries))

    seen_urls: set[str] = set()
    all_raw: list[dict] = []
    for q in queries:
        q = q + " 百科" if len(q)<=8 else q # 尽量搜索百科类内容
        results = do_search(q, engines, num_results=3)
        for r in results:
            if r.url and r.url not in seen_urls:
                seen_urls.add(r.url)
                all_raw.append({
                    "query": q,
                    "title": r.title,
                    "url": r.url,
                    "snippet": (r.snippet or "")[:500],
                })

    if not all_raw:
        logger.info("No search results collected from outline")
        return None

    with open(raw_search_path, "w", encoding="utf-8") as f:
        json.dump(all_raw, f, indent=2, ensure_ascii=False)

    logger.info("Collected %d raw search results → %s", len(all_raw), raw_search_path)
    return raw_search_path
