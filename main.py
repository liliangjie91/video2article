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
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[_console_handler, _file_handler],
)

log = logging.getLogger("video2article")


def _output_dir(source_name: str, base: str | None) -> str:
    if base:
        return os.path.join(base, source_name)
    return os.path.join("output", source_name)


# ── Core commands ──────────────────────────────────────────────


def _run_article_pipeline(subtitle_path: str, output_dir: str, tier: str, dry_run: bool) -> str | None:
    """字幕 → 文章 pipeline。返回文章路径，dry_run 时返回 None。"""
    name = os.path.splitext(os.path.basename(subtitle_path))[0]
    out = _output_dir(name, output_dir)

    if dry_run:
        log.info("[dry-run] article pipeline would output to: %s", out)
        return None

    pp = preprocess.run(subtitle_path, out, tier=tier)
    st = structure.run(pp, out, tier=tier)
    ins = insights.run(st, out, tier=tier)
    syn = synthesize.run(st, ins, out, tier=tier)
    log.info("Article complete: %s", syn)
    return syn


def cmd_article(args):
    """字幕 → 文章 (Step 1 完整 pipeline)"""
    from pipeline import preprocess, structure, insights, synthesize

    _run_article_pipeline(args.subtitle, args.output_dir, args.tier, args.dry_run)


def cmd_sttarticle(args):
    """音视频 → STT → 文章"""
    from stt.transcribe import run as stt_run

    output_base = args.output_dir or "output"
    srt_path = stt_run(args.video)
    _run_article_pipeline(srt_path, output_base, args.tier, args.dry_run)


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
    srt_path = stt_run(args.video)
    # Step 1
    pp = preprocess.run(srt_path, out, tier=args.tier)
    st = structure.run(pp, out, tier=args.tier)
    ins = insights.run(st, out, tier=args.tier)
    syn = synthesize.run(st, ins, out, tier=args.tier)
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
    srt = stt_run(args.video)
    log.info("STT complete: %s", srt)


def cmd_speak(args):
    from tts.speak import run as speak_run

    out = os.path.dirname(os.path.abspath(args.article))

    if args.dry_run:
        log.info("[dry-run] speak %s → %s", args.article, out)
        return
    sp = speak_run(args.article, out)
    log.info("Speak complete: %s", sp)

# ── URL / Download commands ──────────────────────────────────────


def _resolve_subtitle(url: str, output_dir: str, force: bool = False) -> str:
    """Try YouTube subs first, fall back to yt-dlp download + STT. Returns SRT path.

    Cache-aware: skips download if SRT/audio already exists.
    """
    from download.youtube import get_subtitle_srt, extract_video_id
    from download.media import download_audio
    from stt.transcribe import transcribe

    is_youtube = "youtube.com" in url or "youtu.be" in url

    # Cache check: predict filenames for YouTube URLs
    if is_youtube and not force:
        video_id = extract_video_id(url)
        srt_path = os.path.join(output_dir, f"{video_id}.srt")
        if os.path.exists(srt_path):
            log.info("SRT already cached: %s", srt_path)
            return srt_path

        audio_path = os.path.join(output_dir, f"{video_id}.m4a")
        if os.path.exists(audio_path):
            log.info("Audio already cached — transcribing: %s", audio_path)
            return transcribe(audio_path, output_dir)

    # Try 1: YouTube subtitles via API (zero download)
    if is_youtube:
        srt = get_subtitle_srt(url, output_dir)
        if srt is not None:
            return srt

    # Try 2: yt-dlp audio → STT
    log.info("Downloading audio via yt-dlp...")
    audio_path = download_audio(url, output_dir)
    return transcribe(audio_path, output_dir)


def cmd_probe(args):
    """Probe what's available for a URL (subtitles, video info)."""
    from download.youtube import list_transcripts, extract_video_id

    video_id = extract_video_id(args.url)
    log.info("Video ID: %s", video_id)

    subs = list_transcripts(args.url)
    if subs:
        log.info("Available subtitles (%d):", len(subs))
        for s in subs:
            tag = " (auto)" if s["is_generated"] else ""
            log.info("  %s (%s)%s", s["language"], s["language_code"], tag)
    else:
        log.info("No subtitles available — would need STT fallback")

    if args.verbose:
        from download.media import yt_dlp
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
    out = args.output_dir or os.path.join(os.path.dirname(__file__), "output", "downloads")

    if args.dry_run:
        log.info("[dry-run] Would download: %s", args.url)
        return

    srt_path = _resolve_subtitle(args.url, out, force=args.force)
    log.info("Subtitle ready: %s", srt_path)


def cmd_article_from_url(args):
    """URL → article (Step 1). YouTube subs fast path when available."""
    from pipeline import preprocess, structure, insights, synthesize

    if args.dry_run:
        log.info("[dry-run] Would process URL: %s", args.url)
        return

    dl_dir = os.path.join(os.path.dirname(__file__), "output", "downloads")
    srt_path = _resolve_subtitle(args.url, dl_dir)
    _run_article_pipeline(srt_path, args.output_dir, args.tier, args.dry_run)


def cmd_full_from_url(args):
    """URL → article + screenshots (full pipeline)."""
    from download.media import download_video
    from stt.transcribe import run as stt_run
    from pipeline import preprocess, structure, insights, synthesize
    from image.screenshot import extract_screenshots, synthesize_illustrated

    if args.dry_run:
        log.info("[dry-run] Would full-process URL: %s", args.url)
        return

    dl_dir = os.path.join(os.path.dirname(__file__), "output", "downloads")

    # Try YouTube subs first (fast path)
    srt_path = None
    video_path = None
    try:
        from download.youtube import get_subtitle_srt
        srt_path = get_subtitle_srt(args.url, dl_dir)
    except ImportError:
        pass

    if srt_path:
        # Subs obtained via API — download video separately for screenshots
        log.info("Subtitles obtained via API — downloading video for screenshots...")
        video_path = download_video(args.url, dl_dir)
    else:
        # No subs — download video, STT extracts audio internally
        log.info("Downloading video for STT + screenshots...")
        video_path = download_video(args.url, dl_dir)
        srt_path = stt_run(video_path)

    name = os.path.splitext(os.path.basename(video_path))[0]
    out = _output_dir(name, args.output_dir)

    pp = preprocess.run(srt_path, out, tier=args.tier)
    st = structure.run(pp, out, tier=args.tier)
    ins = insights.run(st, out, tier=args.tier)
    syn = synthesize.run(st, ins, out, tier=args.tier)
    ss_dir = os.path.join(out, "screenshots")
    ss_list = extract_screenshots(video_path, st, ss_dir)
    ill = synthesize_illustrated(syn, ss_list, st, out)
    log.info("Full pipeline from URL complete: %s", ill)


def cmd_uploads(args):
    """List recent uploads from a YouTube channel."""
    from download.youtube import get_channel_uploads

    uploads = get_channel_uploads(args.identifier, max_results=args.limit)
    if uploads is None:
        log.error("YOUTUBE_API_KEY not set in .env — can't fetch channel uploads")
        return

    if not uploads:
        log.info("No uploads found for: %s", args.identifier)
        return

    log.info("Recent uploads for %s:", args.identifier)
    for i, v in enumerate(uploads, 1):
        url = f"https://youtube.com/watch?v={v['video_id']}"
        log.info("%d. %s", i, v["title"])
        log.info("   %s", url)
        log.info("   %s", v["published_at"][:10])


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

    # sttarticle
    p = sub.add_parser("sttarticle", help="音视频 → 字幕 → 文章")
    p.add_argument("video", help="音视频文件路径")
    p.add_argument("--output-dir", "-o", default=None, help="输出根目录")
    p.add_argument("--dry-run", action="store_true", help="只打印不执行")
    p.add_argument("--tier", choices=["fast", "best", "top"], default="best", help="模型档位")
    p.set_defaults(func=cmd_sttarticle)

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

    p = sub.add_parser("article-from-url", help="URL → 文章 (YouTube 字幕直取 / yt-dlp+STT 兜底)")
    p.add_argument("url", help="视频 URL")
    p.add_argument("--output-dir", "-o", default=None, help="输出根目录")
    p.add_argument("--dry-run", action="store_true", help="只打印不执行")
    p.add_argument("--tier", choices=["fast", "best", "top"], default="best", help="模型档位")
    p.set_defaults(func=cmd_article_from_url)

    p = sub.add_parser("full-from-url", help="URL → 文章 + 截图 (全流程)")
    p.add_argument("url", help="视频 URL")
    p.add_argument("--output-dir", "-o", default=None, help="输出根目录")
    p.add_argument("--dry-run", action="store_true", help="只打印不执行")
    p.add_argument("--tier", choices=["fast", "best", "top"], default="best", help="模型档位")
    p.set_defaults(func=cmd_full_from_url)

    p = sub.add_parser("uploads", help="查看 YouTube 频道最新视频列表")
    p.add_argument("identifier", help="频道 handle (@TED) 或频道 URL")
    p.add_argument("--limit", "-l", type=int, default=10, help="数量")
    p.set_defaults(func=cmd_uploads)

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
