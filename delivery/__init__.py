"""Delivery dispatch — sends articles through configured channels.

Each channel module exposes ``deliver(title, body) -> bool``.
"""

import logging
import os

from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)

_CHANNEL_MODULES = {
    "telegram": "delivery.telegram",
    "discord": "delivery.discord",
}
# Public list of all available channel names
CHANNELS: list[str] = list(_CHANNEL_MODULES.keys())


def deliver_article(
    article_path: str, channels: list[str] | None = None, as_text: bool = False
) -> dict[str, bool]:
    """Deliver *article_path* through each channel in *channels*.

    If *channels* is ``None``, defaults to ``["telegram"]``.
    By default sends the ``.md`` file as a document with a title message.
    Pass ``as_text=True`` to send the article body as formatted text instead.

    Returns ``{channel_name: success}``.
    """
    if channels is None:
        channels = ["telegram"]

    with open(article_path, "r", encoding="utf-8") as f:
        text = f.read()

    title, body = _parse_article(text)

    results: dict[str, bool] = {}
    for ch in channels:
        mod_path = _CHANNEL_MODULES.get(ch)
        if mod_path is None:
            logger.error("Unknown delivery channel: %s", ch)
            results[ch] = False
            continue

        import importlib

        mod = importlib.import_module(mod_path)
        try:
            kwargs = {"file_path": article_path} if not as_text else {}
            ok = mod.deliver(title, body, **kwargs)
        except Exception as e:
            logger.error("Delivery to %s failed: %s", ch, e)
            ok = False
        results[ch] = ok

    return results


def _parse_article(text: str) -> tuple[str, str]:
    """Extract title (first ``# `` line) and body from markdown article."""
    lines = text.split("\n")
    title = ""
    body_lines: list[str] = []
    for line in lines:
        if line.startswith("# ") and not title:
            title = line[2:].strip()
        else:
            body_lines.append(line)
    body = "\n".join(body_lines).strip()
    return title, body
