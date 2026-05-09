"""Aggregate search results from insights JSON into clean deduplicated references."""

import json
import logging
import os

logger = logging.getLogger(__name__)

_SEARCH_FROM_OUTLINE_PROMPT = """基于以下文章大纲段落，生成1-2个搜索查询，用于查找相关的背景信息和扩展阅读资料。

大纲标题：{heading}
关键论点：{key_points}

## 要求
- 每个查询用简短短语或短句（10-30字），像搜索引擎里会打的内容
- 聚焦于大纲中特有的概念、事件、人物或观点
- 如果有多个查询，它们必须从**不同角度**出发，内容不能相似
- 不要废话，不要完整长句

## 输出格式
每行一个查询，不要编号、不要前缀。"""


def search_from_outline(outline_path: str, output_dir: str, tier: str) -> str | None:
    """Generate search queries from outline headings, execute searches, then integrate.

    Reads ``04_outline.json``, generates 1-2 queries per outline section, executes
    them, aggregates and deduplicates via :func:`run`, and writes
    ``search_references.json``.

    Returns path to ``search_references.json``, or ``None`` if no engines configured.
    """
    from search import get_configured_engines, search as do_search
    from llm import chat

    engines = get_configured_engines()
    if not engines:
        logger.info("No search engines configured, skipping outline search")
        return None

    with open(outline_path, "r", encoding="utf-8") as f:
        outline = json.load(f)

    all_raw: list[dict] = []
    for sec in outline.get("outline", []):
        heading = sec.get("heading", "")
        key_points = sec.get("key_points", [])
        kp_text = "；".join(key_points) if key_points else "（无）"
        logger.info("Generating search queries for: %s", heading)

        raw = chat(
            _SEARCH_FROM_OUTLINE_PROMPT.format(heading=heading, key_points=kp_text),
            tier=tier,
            system="你是一位研究助手，负责生成精准的搜索查询。",
            step=0,
            log_prompt=False,
        )
        queries = [q.strip() for q in raw.strip().split("\n") if q.strip() and not q.startswith(("-", "•"))]
        queries = queries[:2]

        for q in queries:
            results = do_search(q, engines, num_results=5)
            all_raw.append({
                "queries": q,
                "results": [
                    {"title": r.title, "url": r.url, "snippet": (r.snippet or "")[:1000]}
                    for r in results
                ],
            })

    if not all_raw:
        logger.info("No search results collected from outline")
        return None

    # Wrap raw results into a temporary insights-like structure for run()
    temp_data = {"segments": [{"id": 0, "insight": {"web_search": {"qr": all_raw}}}]}
    temp_path = os.path.join(output_dir, ".search_raw.json")
    with open(temp_path, "w", encoding="utf-8") as f:
        json.dump(temp_data, f, indent=2, ensure_ascii=False)

    refs = run(temp_path, output_dir)
    os.remove(temp_path)
    return refs


def run(insights_path: str, output_dir: str) -> str:
    """Aggregate and deduplicate search results from all segments.

    Reads ``03_insights.json``, collects every ``web_search`` entry across all
    segments, deduplicates by URL (keeping the richest snippet), and writes a
    flat ``search_references.json`` sorted by relevance.

    Returns path to ``search_references.json``.
    """
    output_path = os.path.join(output_dir, "search_references.json")

    with open(insights_path, "r", encoding="utf-8") as f:
        insights = json.load(f)

    # Collect all results, dedup by URL with best snippet
    pool: dict[str, dict] = {}
    for seg in insights.get("segments", []):
        seg_id = seg.get("id")
        web_search = seg.get("insight", {}).get("web_search", {})
        for qr_item in web_search.get("qr", []):
            query = qr_item.get("queries", "")
            for r in qr_item.get("results", []):
                url = r["url"]
                if url in pool:
                    existing = pool[url]
                    # Keep longer snippet
                    if len(r.get("snippet", "") or "") > len(existing.get("snippet", "") or ""):
                        existing["snippet"] = r.get("snippet", "")
                    if seg_id is not None and seg_id not in existing["segment_ids"]:
                        existing["segment_ids"].append(seg_id)
                    if query and query not in existing["queries"]:
                        existing["queries"].append(query)
                else:
                    pool[url] = {
                        "title": r.get("title", ""),
                        "url": url,
                        "snippet": r.get("snippet", ""),
                        "segment_ids": [seg_id] if seg_id is not None else [],
                        "queries": [query] if query else [],
                    }

    # Sort: more segments referencing → higher rank, then by snippet length
    refs = sorted(
        pool.values(),
        key=lambda x: (len(x["segment_ids"]), len(x.get("snippet", "") or "")),
        reverse=True,
    )

    output = {"references": refs, "total": len(refs)}
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(output, f, indent=2, ensure_ascii=False)

    logger.info("Search references: %d unique URLs → %s", len(refs), output_path)
    return output_path
