"""Internal helpers for pipeline stages."""

import logging

logger = logging.getLogger("video2article")


def log_banner(stage_label: str, message: str = "") -> None:
    """Log a prominent stage separator to improve log readability."""
    sep = "=" * 55
    line = f"  {stage_label}"
    if message:
        line += f" — {message}"
    logger.info("%s\n%s\n%s", sep, line, sep)
