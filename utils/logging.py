"""Centralized logging setup and utilities for video2article."""

import logging
import logging.handlers
import os

_LOG_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "logs")


def _file_handler() -> logging.Handlers:
    os.makedirs(_LOG_DIR, exist_ok=True)
    return logging.handlers.RotatingFileHandler(
        os.path.join(_LOG_DIR, "video2article.log"),
        maxBytes=10 * 1024 * 1024,
        backupCount=5,
        encoding="utf-8",
    )


def setup_logging() -> None:
    """Configure root logger with file (DEBUG) and console (INFO) handlers."""
    fh = _file_handler()
    fh.setLevel(logging.DEBUG)

    ch = logging.StreamHandler()
    ch.setLevel(logging.INFO)

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(filename)s:%(lineno)d: %(message)s",
        handlers=[ch, fh],
    )


def log_banner(stage_label: str, message: str = "") -> None:
    """Log a prominent stage separator to improve log readability."""
    log = logging.getLogger("video2article")
    sep = "=" * 55
    line = f"  {stage_label}"
    if message:
        line += f" — {message}"
    log.info("\n%s\n%s\n%s", sep, line, sep)
