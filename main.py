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

from commands import (  # noqa: E402
    cmd_article,
    cmd_batch,
    cmd_download,
    cmd_info,
    cmd_insights,
    cmd_preprocess,
    cmd_review,
    cmd_stt,
    cmd_structure,
    cmd_synthesize,
    cmd_uploads,
)


# ── Parser setup ────────────────────────────────────────────────


def main():
    parser = argparse.ArgumentParser(
        description="video2article — 字幕/音视频/URL/ID → 文章",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    # article (unified entry — auto-detects input type)
    p = sub.add_parser("article", help="字幕/音视频/URL/ID → 文章（自动检测类型）")
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
    p = sub.add_parser("stt", help="语音转文字 -> 生成字幕文件")
    p.add_argument("video", help="视频文件路径")
    p.add_argument("--dry-run", action="store_true", help="只打印不执行")
    p.set_defaults(func=cmd_stt)

    # URL commands
    p = sub.add_parser("info", help="获取视频信息（可用字幕，标题，频道名称等）")
    p.add_argument("url", help="视频URL或ID")
    p.set_defaults(func=cmd_info)

    p = sub.add_parser("download", help="URL/ID → SRT字幕(默认) or 音视频")
    p.add_argument("url", help="视频URL或ID")
    p.add_argument("--output-dir", "-o", default=None, help="下载目录")
    p.add_argument("--dry-run", action="store_true", help="只打印不执行")
    p.add_argument("--media", choices=["video", "audio", "subtitle"], default="subtitle", help="媒体类型")
    p.set_defaults(func=cmd_download)

    p = sub.add_parser("uploads", help="查看 YouTube 频道最新视频列表")
    p.add_argument("identifier", help="频道 handle (@TED) 或频道 URL")
    p.add_argument("--limit", "-l", type=int, default=5, help="数量")
    p.set_defaults(func=cmd_uploads)

    # batch
    p = sub.add_parser("batch", help="批处理：多个 URL/文件/频道 逐个生成文章")
    p.add_argument("inputs", nargs="*", help="视频 URL/ID/字幕/媒体文件")
    p.add_argument("--file", "-f", help="包含输入列表的文本文件（每行一个输入）")
    p.add_argument("--from-channel", "-c", help="从 YouTube 频道拉取未处理的视频（handle/@/URL）")
    p.add_argument("--limit", "-l", type=int, default=20, help="总输入数量上限")
    p.add_argument("--output-dir", "-o", default=None, help="输出根目录")
    p.add_argument("--tier", choices=["fast", "best", "top"], default="best", help="模型档位")
    p.add_argument("--simple", action="store_true", help="使用快速产出模式")
    p.set_defaults(func=cmd_batch)

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
