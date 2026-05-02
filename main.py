"""CLI entry point for video2article — 字幕 → 深度文章 → 图文"""

import argparse
import logging
import logging.handlers
import os
import sys

# Add project root to path for internal imports
sys.path.insert(0, os.path.dirname(__file__))

LOG_DIR = os.path.join(os.path.dirname(__file__), "logs")
os.makedirs(LOG_DIR, exist_ok=True)

_file_handler = logging.handlers.RotatingFileHandler(
    os.path.join(LOG_DIR, "video2article.log"),
    maxBytes=10 * 1024 * 1024,
    backupCount=5,
    encoding="utf-8",
)
_file_handler.setLevel(logging.DEBUG)

_console_handler = logging.StreamHandler()
_console_handler.setLevel(logging.INFO)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(filename)s:%(lineno)d: %(message)s",
    handlers=[_console_handler, _file_handler],
)

log = logging.getLogger("video2article")


def _project_dir(filepath: str, output_dir: str | None) -> str:
    """Determine BASE project directory for one pipeline.
    1. If output_dir is provided, use it directly.
    2. If input file is under output/, use its parent directory.
    3. Otherwise, create a new directory under output/ named after the input file.
    """
    if output_dir:
        return output_dir

    abs_path = os.path.abspath(filepath)
    output_abs = os.path.join(os.path.dirname(__file__), "output")

    if abs_path.startswith(output_abs):
        return os.path.dirname(abs_path)

    name = os.path.splitext(os.path.basename(filepath))[0]
    return os.path.join(output_abs, name)



# ── Core commands ──────────────────────────────────────────────


def _run_article_pipeline(subtitle_path: str, output_dir: str, tier: str, dry_run: bool) -> str | None:
    """字幕 → 文章 pipeline。返回文章路径，dry_run 时返回 None。"""
    from pipeline import preprocess, structure, insights, synthesize
    out = _project_dir(subtitle_path, output_dir)
    log.info("Running article pipeline: %s", out)
    if dry_run:
        log.info("[dry-run] article pipeline would output to: %s", out)
        return None

    pp = preprocess.run(subtitle_path, out, tier=tier)
    st = structure.run(pp, out, tier=tier)
    ins = insights.run(st, out, tier=tier)
    syn = synthesize.run(st, ins, out, tier=tier)
    log.info("Article complete: %s", syn)
    return syn


def cmd_srtarticle(args):
    """字幕 → 文章 (Step 1 完整 pipeline)"""
    _run_article_pipeline(args.subtitle, args.output_dir, args.tier, args.dry_run)


def cmd_sttarticle(args):
    """音视频 → STT → 文章"""
    from stt.transcribe import run as stt_run

    srt_path = stt_run(args.video)
    _run_article_pipeline(srt_path, args.output_dir, args.tier, args.dry_run)

def cmd_urlarticle(args):
    """ url/video_id → (音视频 → STT) → 文章 """
    srt_path = _resolve_subtitle(args.video, args.output_dir)
    _run_article_pipeline(srt_path, args.output_dir, args.tier, args.dry_run)


# ── Single-stage debug commands ────────────────────────────────


def cmd_preprocess(args):
    from pipeline import preprocess

    out = _project_dir(args.subtitle, args.output_dir)

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

    out = os.path.dirname(os.path.abspath(args.structure))

    if args.dry_run:
        log.info("[dry-run] insights → %s", out)
        return
    ins = insights.run(args.structure, out, tier=args.tier)
    log.info("Insights complete: %s", ins)


def cmd_synthesize(args):
    from pipeline import synthesize

    out = os.path.dirname(os.path.abspath(args.structure))

    if args.dry_run:
        log.info("[dry-run] synthesize → %s", out)
        return
    syn = synthesize.run(args.structure, args.insights, out, tier=args.tier)
    log.info("Synthesize complete: %s", syn)


def cmd_review(args):
    """文章审阅与对比 (Stage 5)"""
    from pipeline.review import run as review_run

    out = os.path.dirname(os.path.abspath(args.articles[0]))

    if args.dry_run:
        log.info("[dry-run] Would review %d article(s) → %s", len(args.articles), out)
        return

    r = review_run(args.articles, out, tier=args.tier)
    log.info("Review complete: %s", r)


def cmd_simple(args):
    """字幕 → 文章 (一步到位，用于快速产出或对比)"""
    from pipeline.simple import run as simple_run
    
    out = _project_dir(args.subtitle, args.output_dir)

    if args.dry_run:
        log.info("[dry-run] simple %s → %s", args.subtitle, out)
        return

    r = simple_run(args.subtitle, out, tier=args.tier)
    log.info("Simple article complete: %s", r)



# ── Peripheral commands ─────────────────────────────────────────

def cmd_stt(args):
    from stt.transcribe import run as stt_run
    if args.dry_run:
        log.info("[dry-run] stt %s → same folder", args.video)
        return
    srt = stt_run(args.video)
    log.info("STT complete: %s", srt)


# ── URL / Download commands ──────────────────────────────────────


def _resolve_subtitle(url: str, output_dir: str | None) -> str:
    """Try YouTube subs first, fall back to yt-dlp download + STT. Returns SRT path.

    Cache-aware: skips download if SRT/audio already exists.
    """
    # modify output_dir
    default_output = os.path.join(os.path.dirname(__file__), "output")
    output_dir = output_dir or default_output

    # Try 1: YouTube subtitles via API (zero download)
    from download.handle_youtube_api import get_subtitle_srt
    srt = get_subtitle_srt(url, output_dir)
    if srt is not None:
        return srt
    
    # Try 2: yt-dlp audio → STT
    from download.handle_yt_dlp import download as dl_download
    from stt.transcribe import run as stt_run

    log.info("Downloading audio via yt-dlp...")
    audio_path = dl_download(url, output_dir, down_type="audio")
    return stt_run(audio_path)


def cmd_probe(args):
    """Probe what's available for a URL (subtitles, video info)."""
    from download.handle_youtube_api import list_transcripts, extract_video_id

    video_id = extract_video_id(args.url)
    log.info("Video ID: %s", video_id)

    subs = list_transcripts(args.url)
    if subs:
        log.info("Available subtitles (%d):", len(subs))
        for s in subs:
            tag = " (auto)" if s["is_generated"] else " (manual)"
            log.info("  %s (%s)%s", s["language"], s["language_code"], tag)
    else:
        log.info("No subtitles available — would need STT fallback")

    if args.verbose:
        import yt_dlp
        with yt_dlp.YoutubeDL({"quiet": True}) as ydl:
            try:
                info = ydl.extract_info(args.url, download=False)
                log.info("Title: %s", info.get("title"))
                log.info("Duration: %s s", info.get("duration"))
                log.info("Uploader: %s", info.get("uploader"))
            except Exception as e:
                log.warning("Could not fetch video info: %s", e)


def cmd_download(args):
    """URL → SRT subtitle (try YouTube API first, fallback to yt-dlp + STT)."""
    if args.dry_run:
        log.info("[dry-run] Would download: %s", args.url)
        return
    srt_path = _resolve_subtitle(args.url, args.output_dir)

def cmd_uploads(args):
    """List recent uploads from a YouTube channel."""
    from download.handle_youtube_api import get_channel_uploads

    uploads = get_channel_uploads(args.identifier, max_results=args.limit)
    if not uploads:
        log.info("No uploads found for: %s", args.identifier)
        return

    infos = []
    for i, ups in enumerate(uploads, 1):
        infos.append(' | '.join([f"{v}" for v in ups.values()]))
    log.info("Recent uploads for %s:\n%s", args.identifier, "\n".join(infos))

# ── Parser setup ────────────────────────────────────────────────


def main():
    parser = argparse.ArgumentParser(
        description="video2article — 字幕 → 文章",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    # article
    p = sub.add_parser("srtarticle", help="字幕 → 文章 (Step 1)")
    p.add_argument("subtitle", help="字幕文件路径 (.srt/.vtt)")
    p.add_argument("--output-dir", "-o", default=None, help="输出根目录")
    p.add_argument("--dry-run", action="store_true", help="只打印不执行")
    p.add_argument("--tier", choices=["fast", "best", "top"], default="best", help="模型档位")
    p.set_defaults(func=cmd_srtarticle)

    # sttarticle
    p = sub.add_parser("sttarticle", help="音视频 → 字幕 → 文章")
    p.add_argument("video", help="音视频文件路径")
    p.add_argument("--output-dir", "-o", default=None, help="输出根目录")
    p.add_argument("--dry-run", action="store_true", help="只打印不执行")
    p.add_argument("--tier", choices=["fast", "best", "top"], default="best", help="模型档位")
    p.set_defaults(func=cmd_sttarticle)

    # urlarticle
    p = sub.add_parser("urlarticle", help="全流程: 视频 → 字幕 → 文章 → 图文")
    p.add_argument("video", help="视频ID或URL")
    p.add_argument("--output-dir", "-o", default=None, help="输出根目录")
    p.add_argument("--dry-run", action="store_true", help="只打印不执行")
    p.add_argument("--tier", choices=["fast", "best", "top"], default="best", help="模型档位")
    p.set_defaults(func=cmd_urlarticle)

    # preprocess
    p = sub.add_parser("preprocess", help="[单阶段] 字幕预处理")
    p.add_argument("subtitle", help="字幕文件路径")
    p.add_argument("--output-dir", "-o", default=None, help="输出根目录")
    p.add_argument("--dry-run", action="store_true", help="只打印不执行")
    p.add_argument("--tier", choices=["fast", "best", "top"], default="fast", help="模型档位")
    p.set_defaults(func=cmd_preprocess)

    # structure
    p = sub.add_parser("structure", help="[单阶段] 结构识别")
    p.add_argument("preprocessed", help="01_preprocessed.txt 路径")
    p.add_argument("--dry-run", action="store_true", help="只打印不执行")
    p.add_argument("--tier", choices=["fast", "best", "top"], default="best", help="模型档位")
    p.set_defaults(func=cmd_structure)

    # insights
    p = sub.add_parser("insights", help="[单阶段] 深度挖掘")
    p.add_argument("structure", help="02_structure.json 路径")
    p.add_argument("--dry-run", action="store_true", help="只打印不执行")
    p.add_argument("--tier", choices=["fast", "best", "top"], default="best", help="模型档位")
    p.set_defaults(func=cmd_insights)

    # synthesize
    p = sub.add_parser("synthesize", help="[单阶段] 合成撰写")
    p.add_argument("structure", help="02_structure.json 路径")
    p.add_argument("insights", help="03_insights.md 路径")
    p.add_argument("--dry-run", action="store_true", help="只打印不执行")
    p.add_argument("--tier", choices=["fast", "best", "top"], default="best", help="模型档位")
    p.set_defaults(func=cmd_synthesize)

    # review
    p = sub.add_parser("review", help="文章审阅与对比 (Stage 5)")
    p.add_argument("articles", nargs="+", help="一个或多个文章 .md 路径")
    p.add_argument("--dry-run", action="store_true", help="只打印不执行")
    p.add_argument("--tier", choices=["fast", "best", "top"], default="best", help="模型档位")
    p.set_defaults(func=cmd_review)

    # simple
    p = sub.add_parser("simple", help="字幕 → 文章 (一步到位，快速产出)")
    p.add_argument("subtitle", help="字幕文件路径 (.srt/.vtt)")
    p.add_argument("--output-dir", "-o", default=None, help="输出根目录")
    p.add_argument("--dry-run", action="store_true", help="只打印不执行")
    p.add_argument("--tier", choices=["fast", "best", "top"], default="best", help="模型档位")
    p.set_defaults(func=cmd_simple)    

    # stt
    p = sub.add_parser("stt", help="语音转文字")
    p.add_argument("video", help="视频文件路径")
    p.add_argument("--output-dir", "-o", default=None, help="输出根目录")
    p.add_argument("--dry-run", action="store_true", help="只打印不执行")
    p.set_defaults(func=cmd_stt)

    # ── URL commands ──
    p = sub.add_parser("probe", help="探测 URL 信息（字幕、标题、时长等）")
    p.add_argument("url", help="视频 URL")
    p.add_argument("--verbose", "-v", action="store_true", help="显示详细信息")
    p.set_defaults(func=cmd_probe)

    p = sub.add_parser("download", help="URL → SRT 字幕（自动选择最快路径）")
    p.add_argument("url", help="视频 URL")
    p.add_argument("--output-dir", "-o", default=None, help="下载目录")
    p.add_argument("--dry-run", action="store_true", help="只打印不执行")
    p.add_argument("--force", "-f", action="store_true", help="忽略缓存，重新下载")
    p.set_defaults(func=cmd_download)

    p = sub.add_parser("uploads", help="查看 YouTube 频道最新视频列表")
    p.add_argument("identifier", help="频道 handle (@TED) 或频道 URL")
    p.add_argument("--limit", "-l", type=int, default=5, help="数量")
    p.set_defaults(func=cmd_uploads)

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
