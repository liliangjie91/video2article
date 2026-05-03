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

    if abs_path.startswith(output_abs) and abs_path != output_abs:
        return os.path.dirname(abs_path)

    name = os.path.splitext(os.path.basename(filepath))[0]
    return os.path.join(output_abs, name)



# ── Core commands ──────────────────────────────────────────────


def _run_article_pipeline(subtitle_path: str, output_dir: str, tier: str, dry_run: bool, simple: bool = False) -> str | None:
    """字幕 → 文章 pipeline。返回文章路径，dry_run 时返回 None。"""
    out = _project_dir(subtitle_path, output_dir)
    log.info("Running article pipeline: %s", out)
    if dry_run:
        log.info("[dry-run] article pipeline would output to: %s", out)
        return None

    if simple:
        from pipeline.simple import run as simple_run
        syn = simple_run(subtitle_path, out, tier=tier)
        log.info("Simple article complete: %s", syn)
        return syn

    from pipeline import preprocess, structure, insights, synthesize
    pp = preprocess.run(subtitle_path, out, tier=tier)
    st = structure.run(pp, out, tier=tier)
    ins = insights.run(st, out, tier=tier)
    syn = synthesize.run(st, ins, out, tier=tier)
    log.info("Article complete: %s", syn)
    return syn


def _detect_input_type(input_str: str) -> str:
    """Detect input type: ``'srt'``, ``'media'``, or ``'url'``."""
    if "youtube.com" in input_str or "youtu.be" in input_str or input_str.startswith("http"):
        return "url"
    ext = os.path.splitext(input_str)[1].lower()
    if ext in (".srt", ".vtt"):
        return "srt"
    if ext in (".mp4", ".mkv", ".m4a", ".wav", ".mp3", ".webm", ".mov", ".avi"):
        return "media"
    # Bare video ID
    return "url"


def cmd_article(args):
    """字幕/音视频/URL → 文章（自动检测输入类型）"""
    input_type = _detect_input_type(args.input)
    if input_type == "srt":
        _run_article_pipeline(args.input, args.output_dir, args.tier, args.dry_run, args.simple)
    elif input_type == "media":
        from stt.transcribe import run as stt_run
        srt_path = stt_run(args.input)
        _run_article_pipeline(srt_path, args.output_dir, args.tier, args.dry_run, args.simple)
    else:
        srt_path = _resolve_subtitle(args.input, args.output_dir)
        _run_article_pipeline(srt_path, args.output_dir, args.tier, args.dry_run, args.simple)


# ── Single-stage debug commands ────────────────────────────────


def cmd_preprocess(args):
    from pipeline import preprocess
    out = _project_dir(args.subtitle)
    pp = preprocess.run(args.subtitle, out, tier=args.tier)
    log.info("Preprocess complete: %s", pp)


def cmd_structure(args):
    from pipeline import structure
    out = os.path.dirname(os.path.abspath(args.preprocessed))
    st = structure.run(args.preprocessed, out, tier=args.tier)
    log.info("Structure complete: %s", st)


def cmd_insights(args):
    from pipeline import insights
    out = os.path.dirname(os.path.abspath(args.structure))
    ins = insights.run(args.structure, out, tier=args.tier)
    log.info("Insights complete: %s", ins)


def cmd_synthesize(args):
    from pipeline import synthesize
    out = os.path.dirname(os.path.abspath(args.structure))
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


def cmd_info(args):
    """Probe what's available for a URL (subtitles, video info)."""
    from download.handle_youtube_api import get_video_info_from_id
    video_info = get_video_info_from_id(args.url)
    log.info("Video info for %s:\n%s", args.url, '\n'.join([f"{k}: {v}" for k, v in video_info.items()]))

def cmd_download(args):
    """URL → SRT subtitle (try YouTube API first, fallback to yt-dlp + STT)."""
    if args.dry_run:
        log.info("[dry-run] Would download: %s", args.url)
        return
    if args.media != "subtitle":
        # if args.media is specified, download video or audio file, but not subtitles
        if args.media not in ("video", "audio"):
            log.error("Invalid media type: %s. Must be 'video' or 'audio'.", args.media)
            return
        from download.handle_yt_dlp import download as dl_download
        log.info("Downloading %s via yt-dlp...", args.media)
        media_path = dl_download(args.url, args.output_dir, down_type=args.media)
        log.info("Downloaded : %s", media_path)
        return
    srt_path = _resolve_subtitle(args.url, args.output_dir)
    log.info("Download complete: %s", srt_path)

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

    # article (unified entry — auto-detects input type)
    p = sub.add_parser("article", help="字幕/音视频/URL → 文章（自动检测类型）")
    p.add_argument("input", help="字幕文件(.srt/.vtt)、音视频文件(.mp4等) 或 YouTube URL/ID")
    p.add_argument("--output-dir", "-o", default=None, help="输出根目录")
    p.add_argument("--dry-run", action="store_true", help="只打印不执行")
    p.add_argument("--tier", choices=["fast", "best", "top"], default="best", help="模型档位")
    p.add_argument("--simple", action="store_true", help="使用一步到位的快速产出而非分步执行")
    p.set_defaults(func=cmd_article)

    # debug (single-stage subcommands)
    p = sub.add_parser("debug", help="单阶段调试命令")
    debug_sub = p.add_subparsers(dest="debug_command")

    pp = debug_sub.add_parser("preprocess", help="字幕预处理")
    pp.add_argument("subtitle", help="字幕文件路径")
    pp.add_argument("--tier", choices=["fast", "best", "top"], default="fast", help="模型档位")
    pp.set_defaults(func=cmd_preprocess)

    pp = debug_sub.add_parser("structure", help="结构识别")
    pp.add_argument("preprocessed", help="01_preprocessed.txt 路径")
    pp.add_argument("--tier", choices=["fast", "best", "top"], default="best", help="模型档位")
    pp.set_defaults(func=cmd_structure)

    pp = debug_sub.add_parser("insights", help="深度挖掘")
    pp.add_argument("structure", help="02_structure.json 路径")
    pp.add_argument("--tier", choices=["fast", "best", "top"], default="best", help="模型档位")
    pp.set_defaults(func=cmd_insights)

    pp = debug_sub.add_parser("synthesize", help="合成撰写")
    pp.add_argument("structure", help="02_structure.json 路径")
    pp.add_argument("insights", help="03_insights.md 路径")
    pp.add_argument("--tier", choices=["fast", "best", "top"], default="best", help="模型档位")
    pp.set_defaults(func=cmd_synthesize)

    # review
    p = sub.add_parser("review", help="文章审阅与对比 (Stage 5)")
    p.add_argument("articles", nargs="+", help="一个或多个文章 .md 路径")
    p.add_argument("--dry-run", action="store_true", help="只打印不执行")
    p.add_argument("--tier", choices=["fast", "best", "top"], default="best", help="模型档位")
    p.set_defaults(func=cmd_review)

    # stt
    p = sub.add_parser("stt", help="语音转文字")
    p.add_argument("video", help="视频文件路径")
    p.add_argument("--dry-run", action="store_true", help="只打印不执行")
    p.set_defaults(func=cmd_stt)

    # ── URL commands ──
    p = sub.add_parser("info", help="获取 URL 信息（可用字幕、标题等）")
    p.add_argument("url", help="视频 URL")
    p.set_defaults(func=cmd_info)

    p = sub.add_parser("download", help="URL → SRT 字幕（自动选择最快路径）")
    p.add_argument("url", help="视频 URL")
    p.add_argument("--output-dir", "-o", default=None, help="下载目录")
    p.add_argument("--dry-run", action="store_true", help="只打印不执行")
    p.add_argument("--force", "-f", action="store_true", help="忽略缓存，重新下载")
    p.add_argument("--media", choices=["video", "audio", "subtitle"], default="subtitle", help="媒体类型")
    p.set_defaults(func=cmd_download)

    p = sub.add_parser("uploads", help="查看 YouTube 频道最新视频列表")
    p.add_argument("identifier", help="频道 handle (@TED) 或频道 URL")
    p.add_argument("--limit", "-l", type=int, default=5, help="数量")
    p.set_defaults(func=cmd_uploads)

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()