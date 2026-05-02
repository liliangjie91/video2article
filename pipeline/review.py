"""Stage 5: 文章审阅与对比 — 主编审稿 → 资深作者定稿"""

import os
import logging
import re

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

    comments = chat(editor_input, tier=tier, system=EDITOR_PROMPT, step=5)

    comments_path = os.path.join(output_dir, "05_review_comments.md")
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

    final = chat(writer_input, tier=tier, system=WRITER_PROMPT, step=5)

    final_path = os.path.join(output_dir, "05_review_final.md")
    with open(final_path, "w", encoding="utf-8") as f:
        f.write(final)
    logger.info("Review final: %s", final_path)

    return final_path
