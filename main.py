"""CLI entry point for video2article — 字幕 → 深度文章 → 图文"""

import argparse
import logging
import os
import sys

# Add project root to path for internal imports
sys.path.insert(0, os.path.dirname(__file__))

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)

log = logging.getLogger("video2article")


def _output_dir(source_name: str, base: str | None) -> str:
    if base:
        return os.path.join(base, source_name)
    return os.path.join("output", source_name)


# ── Core commands ──────────────────────────────────────────────


def cmd_article(args):
    """字幕 → 文章 (Step 1 完整 pipeline)"""
    from pipeline import preprocess, structure, insights, synthesize

    name = os.path.splitext(os.path.basename(args.subtitle))[0]
    out = _output_dir(name, args.output_dir)

    if args.dry_run:
        log.info("[dry-run] Would create output in: %s", out)
        return

    pp = preprocess.run(args.subtitle, out, tier=args.tier)
    st = structure.run(pp, out, tier=args.tier)
    ins = insights.run(pp, st, out, tier=args.tier)
    syn = synthesize.run(pp, st, ins, out, tier=args.tier)
    log.info("Article complete: %s", syn)


def cmd_illustrate(args):
    """文章 + 视频截图 → 图文 (Step 2)"""
    from image.screenshot import extract_screenshots, synthesize_illustrated

    article_dir = os.path.dirname(os.path.abspath(args.article))
    ss_dir = os.path.join(article_dir, "screenshots")
    structure_path = os.path.join(article_dir, "02_structure.json")

    if not os.path.exists(structure_path):
        log.error("structure.json not found at %s — run Step 1 first", structure_path)
        sys.exit(1)

    if args.dry_run:
        log.info("[dry-run] Would extract screenshots from %s", args.video)
        return

    ss_list = extract_screenshots(args.video, structure_path, ss_dir)
    out = synthesize_illustrated(args.article, ss_list, structure_path, article_dir)
    log.info("Illustrated article complete: %s", out)


def cmd_full(args):
    """全流程: 视频 → 字幕 → 文章 → 图文"""
    from stt.transcribe import run as stt_run
    from pipeline import preprocess, structure, insights, synthesize
    from image.screenshot import extract_screenshots, synthesize_illustrated

    name = os.path.splitext(os.path.basename(args.video))[0]
    out = _output_dir(name, args.output_dir)

    if args.dry_run:
        log.info("[dry-run] Would process %s → %s", args.video, out)
        return

    # STT
    srt_path = stt_run(args.video, out)
    # Step 1
    pp = preprocess.run(srt_path, out, tier=args.tier)
    st = structure.run(pp, out, tier=args.tier)
    ins = insights.run(pp, st, out, tier=args.tier)
    syn = synthesize.run(pp, st, ins, out, tier=args.tier)
    # Step 2
    ss_dir = os.path.join(out, "screenshots")
    ss_list = extract_screenshots(args.video, st, ss_dir)
    ill = synthesize_illustrated(syn, ss_list, st, out)
    log.info("Full pipeline complete: %s", ill)


# ── Single-stage debug commands ────────────────────────────────


def cmd_preprocess(args):
    from pipeline import preprocess

    name = os.path.splitext(os.path.basename(args.subtitle))[0]
    out = _output_dir(name, args.output_dir)

    if args.dry_run:
        log.info("[dry-run] preprocess %s → %s", args.subtitle, out)
        return
    pp = preprocess.run(args.subtitle, out, tier=args.tier)
    log.info("Preprocess complete: %s", pp)


def cmd_structure(args):
    from pipeline import structure

    out = os.path.dirname(os.path.abspath(args.preprocessed))

    if args.dry_run:
        log.info("[dry-run] structure %s → %s", args.preprocessed, out)
        return
    st = structure.run(args.preprocessed, out, tier=args.tier)
    log.info("Structure complete: %s", st)


def cmd_insights(args):
    from pipeline import insights

    out = os.path.dirname(os.path.abspath(args.preprocessed))

    if args.dry_run:
        log.info("[dry-run] insights → %s", out)
        return
    ins = insights.run(args.preprocessed, args.structure, out, tier=args.tier)
    log.info("Insights complete: %s", ins)


def cmd_synthesize(args):
    from pipeline import synthesize

    out = os.path.dirname(os.path.abspath(args.preprocessed))

    if args.dry_run:
        log.info("[dry-run] synthesize → %s", out)
        return
    syn = synthesize.run(args.preprocessed, args.structure, args.insights, out, tier=args.tier)
    log.info("Synthesize complete: %s", syn)


def cmd_simple(args):
    """字幕 → 文章 (一步到位，用于快速产出或对比)"""
    from pipeline.simple import run as simple_run

    name = os.path.splitext(os.path.basename(args.subtitle))[0]
    out = _output_dir(name, args.output_dir)

    if args.dry_run:
        log.info("[dry-run] simple %s → %s", args.subtitle, out)
        return

    r = simple_run(args.subtitle, out, tier=args.tier)
    log.info("Simple article complete: %s", r)


def cmd_review(args):
    """文章审阅与对比 (Stage 5)"""
    from pipeline.review import run as review_run

    out = args.output_dir or os.path.dirname(os.path.abspath(args.articles[0]))

    if args.dry_run:
        log.info("[dry-run] Would review %d article(s) → %s", len(args.articles), out)
        return

    r = review_run(args.articles, out, tier=args.tier)
    log.info("Review complete: %s", r)


# ── Peripheral commands ─────────────────────────────────────────


def cmd_stt(args):
    from stt.transcribe import run as stt_run

    name = os.path.splitext(os.path.basename(args.video))[0]
    out = _output_dir(name, args.output_dir)

    if args.dry_run:
        log.info("[dry-run] stt %s → %s", args.video, out)
        return
    srt = stt_run(args.video, out)
    log.info("STT complete: %s", srt)


def cmd_speak(args):
    from tts.speak import run as speak_run

    out = os.path.dirname(os.path.abspath(args.article))

    if args.dry_run:
        log.info("[dry-run] speak %s → %s", args.article, out)
        return
    sp = speak_run(args.article, out)
    log.info("Speak complete: %s", sp)

# ── Parser setup ────────────────────────────────────────────────


def main():
    parser = argparse.ArgumentParser(
        description="video2article — 字幕 → 深度文章 → 图文",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    # article
    p = sub.add_parser("article", help="字幕 → 文章 (Step 1)")
    p.add_argument("subtitle", help="字幕文件路径 (.srt/.vtt)")
    p.add_argument("--output-dir", "-o", default=None, help="输出根目录")
    p.add_argument("--dry-run", action="store_true", help="只打印不执行")
    p.add_argument("--tier", choices=["fast", "best", "top"], default="best", help="模型档位")
    p.set_defaults(func=cmd_article)

    # illustrate
    p = sub.add_parser("illustrate", help="文章 + 视频截图 → 图文 (Step 2)")
    p.add_argument("article", help="04_article.md 路径")
    p.add_argument("--video", "-v", required=True, help="视频文件路径")
    p.add_argument("--dry-run", action="store_true", help="只打印不执行")
    p.set_defaults(func=cmd_illustrate)

    # full
    p = sub.add_parser("full", help="全流程: 视频 → 字幕 → 文章 → 图文")
    p.add_argument("video", help="视频文件路径")
    p.add_argument("--output-dir", "-o", default=None, help="输出根目录")
    p.add_argument("--dry-run", action="store_true", help="只打印不执行")
    p.add_argument("--tier", choices=["fast", "best", "top"], default="best", help="模型档位")
    p.set_defaults(func=cmd_full)

    # preprocess
    p = sub.add_parser("preprocess", help="[单阶段] 字幕预处理")
    p.add_argument("subtitle", help="字幕文件路径")
    p.add_argument("--output-dir", "-o", default=None, help="输出根目录")
    p.add_argument("--dry-run", action="store_true", help="只打印不执行")
    p.add_argument("--tier", choices=["fast", "best", "top"], default="best", help="模型档位")
    p.set_defaults(func=cmd_preprocess)

    # structure
    p = sub.add_parser("structure", help="[单阶段] 结构识别")
    p.add_argument("preprocessed", help="01_preprocessed.txt 路径")
    p.add_argument("--dry-run", action="store_true", help="只打印不执行")
    p.add_argument("--tier", choices=["fast", "best", "top"], default="best", help="模型档位")
    p.set_defaults(func=cmd_structure)

    # insights
    p = sub.add_parser("insights", help="[单阶段] 深度挖掘")
    p.add_argument("preprocessed", help="01_preprocessed.txt 路径")
    p.add_argument("structure", help="02_structure.json 路径")
    p.add_argument("--dry-run", action="store_true", help="只打印不执行")
    p.add_argument("--tier", choices=["fast", "best", "top"], default="best", help="模型档位")
    p.set_defaults(func=cmd_insights)

    # synthesize
    p = sub.add_parser("synthesize", help="[单阶段] 合成撰写")
    p.add_argument("preprocessed", help="01_preprocessed.txt 路径")
    p.add_argument("structure", help="02_structure.json 路径")
    p.add_argument("insights", help="03_insights.md 路径")
    p.add_argument("--dry-run", action="store_true", help="只打印不执行")
    p.add_argument("--tier", choices=["fast", "best", "top"], default="best", help="模型档位")
    p.set_defaults(func=cmd_synthesize)

    # stt
    p = sub.add_parser("stt", help="语音转文字")
    p.add_argument("video", help="视频文件路径")
    p.add_argument("--output-dir", "-o", default=None, help="输出根目录")
    p.add_argument("--dry-run", action="store_true", help="只打印不执行")
    p.set_defaults(func=cmd_stt)

    # speak
    p = sub.add_parser("speak", help="文章转语音 (stub)")
    p.add_argument("article", help="文章 .md 路径")
    p.add_argument("--dry-run", action="store_true", help="只打印不执行")
    p.set_defaults(func=cmd_speak)

    # simple
    p = sub.add_parser("simple", help="字幕 → 文章 (一步到位，快速产出)")
    p.add_argument("subtitle", help="字幕文件路径 (.srt/.vtt)")
    p.add_argument("--output-dir", "-o", default=None, help="输出根目录")
    p.add_argument("--dry-run", action="store_true", help="只打印不执行")
    p.add_argument("--tier", choices=["fast", "best", "top"], default="best", help="模型档位")
    p.set_defaults(func=cmd_simple)

    # review
    p = sub.add_parser("review", help="文章审阅与对比 (Stage 5)")
    p.add_argument("articles", nargs="+", help="一个或多个文章 .md 路径")
    p.add_argument("--output-dir", "-o", default=None, help="输出目录")
    p.add_argument("--dry-run", action="store_true", help="只打印不执行")
    p.add_argument("--tier", choices=["fast", "best", "top"], default="best", help="模型档位")
    p.set_defaults(func=cmd_review)

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
