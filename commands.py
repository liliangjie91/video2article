"""Command handlers and core processing logic for video2article."""

import logging
import os

from utils import detect_input_type, project_dir

log = logging.getLogger("video2article")
_SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))


# ── Pipeline core ──────────────────────────────────────────────


def _run_article_pipeline(
    subtitle_path: str, output_dir: str, tier: str, dry_run: bool, simple: bool = False
) -> str | None:
    """字幕 → 文章 pipeline。返回文章路径，dry_run 时返回 None。"""
    out = project_dir(subtitle_path, output_dir)
    log.info("Running article pipeline: %s", out)
    if dry_run:
        log.info("[dry-run] article pipeline would output to: %s", out)
        return None

    if simple:
        from pipeline.simple import run as simple_run

        syn = simple_run(subtitle_path, out, tier=tier)
        log.info("Simple article complete: %s", syn)
        return syn

    from pipeline import insights, preprocess, structure, synthesize

    pp = preprocess.run(subtitle_path, out, tier=tier)
    st = structure.run(pp, out, tier=tier)
    ins = insights.run(st, out, tier=tier)
    syn = synthesize.run(st, ins, out, tier=tier)
    log.info("Article complete: %s", syn)
    return syn


# ── Public API ─────────────────────────────────────────────────


def process_one(
    input_str: str,
    output_dir: str | None = None,
    tier: str = "best",
    dry_run: bool = False,
    simple: bool = False,
) -> str | None:
    """Process a single input through the full pipeline.

    Args:
        input_str: SRT path, media path, YouTube URL, or video ID.
        output_dir: Output root directory (auto-detected if None).
        tier: Model tier (``'fast'`` / ``'best'`` / ``'top'``).
        dry_run: If True, log what would happen without executing.
        simple: If True, use quick one-step pipeline instead of staged.

    Returns:
        Path to the final article, or None if dry_run.
    """
    input_type = detect_input_type(input_str)
    if input_type == "srt":
        return _run_article_pipeline(input_str, output_dir, tier, dry_run, simple)
    if input_type == "media":
        from stt.transcribe import run as stt_run

        srt_path = stt_run(input_str)
        return _run_article_pipeline(srt_path, output_dir, tier, dry_run, simple)
    srt_path = _resolve_subtitle(input_str, output_dir)
    return _run_article_pipeline(srt_path, output_dir, tier, dry_run, simple)


def process_batch(
    inputs: list[str],
    output_dir: str | None = None,
    tier: str = "best",
    simple: bool = False,
) -> None:
    """批量处理多个输入的核心循环"""
    if not inputs:
        log.error("No inputs to process")
        return

    log.info("Batch processing %d input(s)...", len(inputs))
    for i, inp in enumerate(inputs, 1):
        log.info("[batch %d/%d] %s", i, len(inputs), inp)
        try:
            article = process_one(inp, output_dir, tier, False, simple)
            log.info("  \u2713 %s", article)
        except Exception as e:
            log.error("  \u2717 %s", e)

    finished = len(inputs)
    log.info("Batch complete: %d/%d done", finished, finished)


# ── URL / Download helpers ─────────────────────────────────────


def _resolve_subtitle(url: str, output_dir: str | None) -> str:
    """Return SRT path for a URL. Uses YouTube API first, falls back to yt-dlp+STT.

    For non-YouTube URLs (bilibili, etc.), skips YouTube API and goes directly to yt-dlp.
    """
    default_output = os.path.join(_SCRIPT_DIR, "output")
    output_dir = output_dir or default_output

    from download import is_youtube_url

    if is_youtube_url(url):
        from download.handle_youtube_api import get_subtitle_srt

        srt = get_subtitle_srt(url, output_dir)
        if srt is not None:
            return srt
        log.info("No YouTube subtitles, falling back to yt-dlp...")
    else:
        log.info("Non-YouTube URL, using yt-dlp directly...")

    from download.handle_yt_dlp import download as dl_download
    from stt.transcribe import run as stt_run

    log.info("Downloading audio via yt-dlp...")
    audio_path = dl_download(url, output_dir, down_type="audio")
    return stt_run(audio_path)


# ── Command handlers ───────────────────────────────────────────


def cmd_article(args):
    """字幕/音视频/URL → 文章（自动检测输入类型）"""
    process_one(args.input, args.output_dir, args.tier, args.dry_run, args.simple)


def cmd_preprocess(args):
    from pipeline import preprocess

    out = project_dir(args.subtitle)
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
        log.info("[dry-run] Would review %d article(s) \u2192 %s", len(args.articles), out)
        return

    if args.interactive:
        from pipeline.review import interactive_run

        interactive_run(args.articles[0], out, tier=args.tier, dry_run=args.dry_run)
        return

    r = review_run(args.articles, out, tier=args.tier)
    log.info("Review complete: %s", r)


def cmd_stt(args):
    from stt.transcribe import run as stt_run

    if args.dry_run:
        log.info("[dry-run] stt %s \u2192 same folder", args.video)
        return
    srt = stt_run(args.video)
    log.info("STT complete: %s", srt)


def cmd_info(args):
    """Probe what's available for a URL (subtitles, video info)."""
    from download.handle_youtube_api import get_video_info_from_id

    video_info = get_video_info_from_id(args.url)
    log.info(
        "Video info for %s:\n%s",
        args.url,
        "\n".join([f"{k}: {v}" for k, v in video_info.items()]),
    )


def cmd_download(args):
    """URL \u2192 SRT subtitle (try YouTube API first, fallback to yt-dlp + STT)."""
    if args.dry_run:
        log.info("[dry-run] Would download: %s", args.url)
        return
    if args.media != "subtitle":
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
    for ups in uploads:
        infos.append(" | ".join([f"{v}" for v in ups.values()]))
    log.info("Recent uploads for %s:\n%s", args.identifier, "\n".join(infos))


def cmd_batch(args):
    """批处理：多个输入逐个生成文章"""
    inputs: list[str] = list(args.inputs or [])
    limit = min(args.limit, 100)
    if args.file:
        with open(args.file, "r", encoding="utf-8") as f:
            inputs.extend(line.strip() for line in f if line.strip())

    if args.from_channel:
        from download.handle_youtube_api import get_channel_uploads

        uploads = get_channel_uploads(args.from_channel, max_results=limit)
        if uploads:
            inputs.extend(ups["video_id"] for ups in uploads)
        else:
            log.warning("No uploads found for channel: %s", args.from_channel)

    if limit and len(inputs) > limit:
        inputs = inputs[:limit]

    process_batch(inputs, args.output_dir, args.tier, args.simple)
