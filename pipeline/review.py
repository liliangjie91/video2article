"""Stage 6: 文章审阅与对比 — 主编审稿 → 资深作者定稿 / 交互式逐段审阅"""

import json
import os
import logging
import re
from datetime import datetime

from llm import chat, set_log_dir

logger = logging.getLogger(__name__)

EDITOR_PROMPT = """你是一位资深主编，在严肃媒体有 20 年从业经验。你的审阅以专业、具体、一针见血著称。

审阅时从以下维度展开：
- **文章结构**：逻辑脉络是否清晰、段落衔接是否自然、开头是否抓人、结尾是否有力
- **论证质量**：论据是否充分、推理是否严密、有无逻辑跳跃或循环论证
- **语言质感**：句式是否单调、用词是否精准、有没有滥用套话或陈词滥调
- **内容深度**：是否有真知灼见、还是浮于表面的复述

## 风格要求
- 具体到问题段落和句子，不要泛泛而谈
- 优点和缺点都要直说，不用铺垫客套话
- 指出问题后要给出明确的修改方向，而不是只抛出问题
- **避免以下 AI 模板词**：首先/其次/最后/总的来说/值得注意的是/不可否认/毋庸置疑

## 输出内容
只输出修改建议，不要重写文章，也不要输出"终稿"或"修改版"。"""

WRITER_PROMPT = """你是一位顶尖的非虚构写作者，以文字精准、见解独到著称。你的任务是接收一篇原文和主编的修改建议，产出一篇更好的文章。

## 写作原则
- **保持信息密度**：保留原文的所有实质性内容，不删减核心观点和论据
- **语言朴实自然**：用干净的中文写作，偶尔可用精妙的比喻或警句点缀，但通篇必须朴实有力
- **去除 AI 痕迹**：不使用首先/其次/最后/总的来说/值得注意的是/不可否认/毋庸置疑/在这个意义上等模板词汇。避免"总分总"的八股结构，段落之间要有自然的逻辑流动
- **尊重编辑意见**：认真对待主编提出的每一条修改建议，但不机械执行——如果认为编辑的判断有问题，可以坚持自己的写法
- **字数一致**：终稿字数与原文基本保持一致

## 格式规范
- 使用 Markdown 格式输出，标题用 `#` 或 `##`
- 段落不宜过长，每段控制在 10 句以内
- 避免连续的多重复合长句，长短句交错，读起来有节奏感
- 开篇要有力度：第一段就点出文章的核心张力或引人思考的矛盾，不要铺垫太多背景
- 结尾要有回响：最后一句话让人读完有余韵，不要用"总之""综上所述"收束

## 输出内容
只输出修改后的完整文章，不要输出修改说明或备注。"""


def _read_article(path: str) -> tuple[str, str]:
    with open(path, "r", encoding="utf-8") as f:
        content = f.read()
    title_match = re.search(r"^#\s+(.+)", content, re.MULTILINE)
    title = title_match.group(1).strip() if title_match else os.path.basename(path)
    return title, content


def run(article_paths: list[str], output_dir: str, tier: str = "best") -> str:
    """Review one or more articles. Returns path to review_final.md."""
    os.makedirs(output_dir, exist_ok=True)
    set_log_dir(os.path.join(output_dir, "llm_logs"))

    articles = [_read_article(p) for p in article_paths]

    # ── Round 1: Editor reviews ──────────────────────────────────
    if len(articles) == 1:
        title, content = articles[0]
        editor_input = f"请审阅以下文章：\n\n# {title}\n\n{content}"
    else:
        parts = [f"## 文章{i}：{title}\n\n{content}" for i, (title, content) in enumerate(articles, 1)]
        editor_input = (
            f"以下有 {len(articles)} 篇文章需要对比审阅。\n\n"
            + "\n---\n".join(parts)
            + "\n\n请逐篇分析优缺点，并做横向对比。"
        )

    comments = chat(editor_input, tier=tier, system=EDITOR_PROMPT, step=6)

    comments_path = os.path.join(output_dir, "06_review_comments.md")
    with open(comments_path, "w", encoding="utf-8") as f:
        f.write(comments)
    logger.info("Review comments: %s", comments_path)

    # ── Round 2: Writer produces final draft ─────────────────────
    if len(articles) == 1:
        title, content = articles[0]
        writer_input = (
            f"原文：\n\n# {title}\n\n{content}\n\n"
            f"主编修改建议：\n\n{comments}\n\n"
            f"请根据以上原文和修改建议，输出修改后的终稿。"
        )
    else:
        parts = [f"## 文章{i}：{title}\n\n{content}" for i, (title, content) in enumerate(articles, 1)]
        all_articles = "\n---\n".join(parts)
        writer_input = (
            f"以下是多篇文章的综合材料：\n\n{all_articles}\n\n"
            f"主编对比分析：\n\n{comments}\n\n"
            f"请综合各篇文章的优点，输出一篇更优秀的文章。"
        )

    final = chat(writer_input, tier=tier, system=WRITER_PROMPT, step=6)

    final_path = os.path.join(output_dir, "06_review_final.md")
    with open(final_path, "w", encoding="utf-8") as f:
        f.write(final)
    logger.info("Review final: %s", final_path)

    return final_path


# ── Interactive review ────────────────────────────────────────────────────────


import difflib


_REWRITE_SYSTEM_PROMPT = """你是一位资深编辑，正在对一篇深度文章进行逐段精修。你的任务是针对当前段落提出具体的修改建议并输出修改后的版本。

## 你的优势
你已阅读整篇文章的结构分析和深度挖掘笔记，理解全文的论证脉络和背景知识。在修改时应确保：
1. 段落内部的逻辑更清晰、表达更有力
2. 与全文的论证脉络保持一致
3. 充分利用深度挖掘笔记中的背景知识和延伸关联

## 输出要求
只输出修改后的段落文本，不要输出标题、说明或备注。
保持 Markdown 格式，段落内可分段。"""


def _parse_article(content: str) -> dict:
    """Parse article markdown into segments.

    Returns:
        dict with keys: title, lead (text before first H2),
        segments (list of dicts with heading + body).
    """
    lines = content.split("\n")
    title = ""
    rest_start = 0

    for i, line in enumerate(lines):
        m = re.match(r"^#\s+(.+)", line)
        if m:
            title = m.group(1).strip()
            rest_start = i + 1
            break

    rest = "\n".join(lines[rest_start:])
    # Allow optional whitespace between \n and ##
    parts = re.split(r"\n\s*(?=##\s+)", rest)

    segments = []
    lead = ""
    for part in parts:
        part = part.strip()
        if not part:
            continue
        m = re.match(r"^##\s+(.+?)(?:\n|$)", part)
        if m:
            body = part[m.end():].strip()
            segments.append({"heading": m.group(1).strip(), "body": body})
        elif not segments:
            lead = part

    return {"title": title, "lead": lead, "segments": segments}


def _find_auxiliary_files(article_dir: str) -> tuple[str | None, str | None]:
    """Look for 02_structure.json and 03_insights.json in article directory."""
    structure_path = os.path.join(article_dir, "02_structure.json")
    insights_path = os.path.join(article_dir, "03_insights.json")
    structure = None
    insights = None
    if os.path.exists(structure_path):
        with open(structure_path, "r", encoding="utf-8") as f:
            structure = f.read()
    if os.path.exists(insights_path):
        with open(insights_path, "r", encoding="utf-8") as f:
            insights = f.read()
    return structure, insights


def _build_context_prompt(structure: str | None, insights: str | None) -> str:
    """Build context block from auxiliary files."""
    parts = []
    if structure:
        parts.append(f"## 文章结构\n{structure}")
    if insights:
        parts.append(f"## 深度挖掘笔记\n{insights}")
    if parts:
        return "\n\n".join(parts)
    return ""


def _show_diff(original: str, modified: str):
    """Show a colored unified diff between two texts."""
    if original == modified:
        print("  (无改动)")
        return
    orig_lines = original.splitlines()
    mod_lines = modified.splitlines()
    diff = list(difflib.unified_diff(orig_lines, mod_lines, lineterm=""))
    # Skip the ---/+++ header lines
    for line in diff[2:]:
        if line.startswith("+"):
            print(f"\033[92m{line}\033[0m")
        elif line.startswith("-"):
            print(f"\033[91m{line}\033[0m")
        elif line.startswith("@@"):
            print(f"\033[36m{line}\033[0m")
        else:
            print(line)


def _log_interactive(llm_log_dir: str, timestamp: str, segment_id: int, kind: str, content: str):
    """Append to combined LLM log for interactive review."""
    os.makedirs(llm_log_dir, exist_ok=True)
    log_path = os.path.join(llm_log_dir, f"step6_interactive_review_{timestamp}.log")
    with open(log_path, "a", encoding="utf-8") as f:
        f.write(f"\n=== {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} {kind} (segment {segment_id}) ===\n")
        f.write(content.strip())
        f.write("\n")


def _suggest_improvement(segment: dict, context_prompt: str, tier: str) -> str:
    """Call LLM to proactively suggest an improved version of a segment."""
    prompt_parts = [context_prompt, f"请审阅并改进以下段落：\n\n## {segment['heading']}\n\n{segment['body']}"]
    prompt = "\n\n".join(prompt_parts)
    return chat(prompt, tier=tier, system=_REWRITE_SYSTEM_PROMPT, step=6)


def _rewrite_with_instruction(segment: dict, instruction: str, context_prompt: str, tier: str) -> str:
    """Call LLM to rewrite a segment following user instruction."""
    prompt_parts = [
        context_prompt,
        f"## {segment['heading']}\n\n{segment['body']}",
        f"修改要求：{instruction}",
    ]
    prompt = "\n\n".join(prompt_parts)
    return chat(prompt, tier=tier, system=_REWRITE_SYSTEM_PROMPT, step=6)


def interactive_run(article_path: str, output_dir: str, tier: str = "best", dry_run: bool = False) -> str | None:
    """Interactive per-segment review of an article.

    For each segment, LLM proactively suggests improvements shown as a diff.
    User can accept, reject, give custom instructions, skip, or quit.
    Returns path to the final reviewed article.
    """
    os.makedirs(output_dir, exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    llm_log_dir = os.path.join(output_dir, "llm_logs")

    with open(article_path, "r", encoding="utf-8") as f:
        content = f.read()

    article = _parse_article(content)
    segments = article["segments"]

    if not segments:
        logger.warning("No segments found in article (no ## headings)")
        return article_path

    # Find auxiliary files for context
    article_dir = os.path.dirname(os.path.abspath(article_path))
    structure, insights = _find_auxiliary_files(article_dir)
    if structure or insights:
        logger.info("Found auxiliary files: structure=%s, insights=%s", structure is not None, insights is not None)
    context_prompt = _build_context_prompt(structure, insights)

    logger.info("Interactive review: %d segments in '%s'", len(segments), article["title"])
    if dry_run:
        logger.info("[dry-run] Would enter interactive review for %d segments", len(segments))
        return None

    review_record = {
        "title": article["title"],
        "source": article_path,
        "timestamp": ts,
        "has_structure": structure is not None,
        "has_insights": insights is not None,
        "segments": [],
    }

    output_segments = []

    for idx, seg in enumerate(segments, 1):
        print(f"\n{'=' * 50}")
        print(f"段落 {idx}/{len(segments)}: {seg['heading']}")
        print(f"{'=' * 50}")

        # Step 1: LLM proactively suggests improvement
        logger.info("Getting improvement suggestion for segment %d...", idx)
        suggested = _suggest_improvement(seg, context_prompt, tier)
        _log_interactive(llm_log_dir, ts, idx, "REQUEST (auto-suggest)",
                         f"SYSTEM:\n{_REWRITE_SYSTEM_PROMPT}\n\nCONTEXT:\n{context_prompt}\n\nSEGMENT:\n{seg['body']}")
        _log_interactive(llm_log_dir, ts, idx, "RESPONSE (auto-suggest)", suggested)

        # Step 2: Show diff
        if suggested.strip() != seg["body"].strip():
            print("\n修改建议（- 原文, + 建议）:")
            _show_diff(seg["body"], suggested)
        else:
            print("\n  LLM 认为此段无需修改。")

        # Step 3: User decides
        action = None
        final_body = seg["body"]

        while action is None:
            print()
            choice = input(f"[{idx}/{len(segments)}] [y]接受建议  [n]自己修改  [k]保留原文  [q]退出 → ").strip().lower()

            if choice == "y":
                action = "accepted"
                final_body = suggested
                review_record["segments"].append({
                    "id": idx, "heading": seg["heading"],
                    "action": "accepted_suggestion",
                })
                output_segments.append({"heading": seg["heading"], "body": suggested})
                print("  ✓ 已接受修改建议")

            elif choice == "n":
                instruction = input("  修改要求: ").strip()
                if not instruction:
                    print("  ! 要求不能为空")
                    continue
                result = _rewrite_with_instruction(seg, instruction, context_prompt, tier)
                _log_interactive(llm_log_dir, ts, idx, "REQUEST (custom)", instruction)
                _log_interactive(llm_log_dir, ts, idx, "RESPONSE (custom)", result)

                print("\n  ── 修改结果（- 原文, + 修改版）──")
                _show_diff(seg["body"], result)

                sub = input("\n  [y]接受  [n]继续修改  [k]放弃保留原文 → ").strip().lower()
                if sub == "y":
                    action = "accepted"
                    final_body = result
                    review_record["segments"].append({
                        "id": idx, "heading": seg["heading"],
                        "action": "custom_modified", "instruction": instruction,
                    })
                    output_segments.append({"heading": seg["heading"], "body": result})
                    print("  ✓ 已接受修改")
                elif sub == "k":
                    action = "kept"
                    review_record["segments"].append({
                        "id": idx, "heading": seg["heading"],
                        "action": "kept_original",
                    })
                    output_segments.append(seg)
                    print("  ○ 已保留原文")

            elif choice == "k":
                action = "kept"
                review_record["segments"].append({
                    "id": idx, "heading": seg["heading"],
                    "action": "kept_original",
                })
                output_segments.append(seg)
                print("  ○ 已保留原文")

            elif choice == "q":
                review_record["interrupted_at"] = idx
                _save_interactive_output(output_dir, ts, article, output_segments, review_record)
                logger.info("Progress saved at segment %d/%d", idx, len(segments))
                return None

    # All done
    _save_interactive_output(output_dir, ts, article, output_segments, review_record)
    final_path = os.path.join(output_dir, "06_interactive_article.md")
    logger.info("Interactive review complete: %s", final_path)
    return final_path


def _save_interactive_output(output_dir: str, ts: str, article: dict, output_segments: list, review_record: dict):
    """Assemble reviewed article and save outputs."""
    lines = [f"# {article['title']}"]
    if article["lead"]:
        lines.extend(["", article["lead"]])
    for seg in output_segments:
        lines.extend(["", f"## {seg['heading']}", "", seg["body"]])
    article_text = "\n".join(lines)

    article_path = os.path.join(output_dir, "06_interactive_article.md")
    with open(article_path, "w", encoding="utf-8") as f:
        f.write(article_text)

    record_path = os.path.join(output_dir, "06_interactive_review.json")
    with open(record_path, "w", encoding="utf-8") as f:
        json.dump(review_record, f, indent=2, ensure_ascii=False)

    logger.info("Saved: %s", article_path)
    logger.info("Saved: %s", record_path)
