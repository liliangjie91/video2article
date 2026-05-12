"""Dispatch logic for article delivery."""

import importlib
import logging
import os
import re

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

    Channel resolution priority (highest first):
      1. *channels* argument (from CLI ``--channel`` / ``--all``)
      2. ``config.ini`` section ``[delivery]``, key ``default_channels``
      3. Hard-coded fallback ``["telegram"]``

    By default sends the ``.md`` file as a document with a title message.
    Pass ``as_text=True`` to send the article body as formatted text instead.

    Returns ``{channel_name: success}``.
    """
    if channels is None:
        channels = _default_channels()

    # Prefer 05_article_link.md (with citation links) over the bare article
    base, name = os.path.split(article_path)
    link_path = os.path.join(base, "05_article_link.md")
    if name == "05_article.md" and os.path.exists(link_path):
        article_path = link_path
        logger.info("Found linked article, delivering %s instead", link_path)

    with open(article_path, "r", encoding="utf-8") as f:
        text = f.read()

    title, body = _parse_article(text)

    results: dict[str, bool] = {}
    display_filename = f"{_sanitize_filename(title)}.md" if title else None
    for ch in channels:
        mod_path = _CHANNEL_MODULES.get(ch)
        if mod_path is None:
            logger.error("Unknown delivery channel: %s", ch)
            results[ch] = False
            continue

        mod = importlib.import_module(mod_path)
        try:
            kwargs = {"file_path": article_path} if not as_text else {}
            if display_filename:
                kwargs["display_filename"] = display_filename
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


def _sanitize_filename(title: str) -> str:
    """Strip special characters from *title* for safe use as a filename."""
    name = re.sub(r'[\\/:*?"<>|]', "", title)  # remove OS-forbidden chars
    name = name.replace('"', "").replace("'", "")  # remove English quotes
    name = re.sub(r"\s+", "", name)  # remove all whitespace
    name = name.strip(". ")
    return name[:50] or "article"


def _default_channels() -> list[str]:
    """Read default channels from config.ini, fall back to ``["telegram"]``."""
    try:
        from config import get_config

        cfg = get_config()
        raw = cfg.get("delivery", "default_channels", fallback="telegram")
        channels = [ch.strip() for ch in raw.split(",") if ch.strip()]
        return channels or ["telegram"]
    except Exception:
        return ["telegram"]
