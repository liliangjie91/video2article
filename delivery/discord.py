"""Discord delivery via Webhook."""

import logging
import os

import requests

from ._utils import split_text

logger = logging.getLogger(__name__)

_MAX_MSG = 2000


def deliver(title: str, body: str, file_path: str | None = None) -> bool:
    """Send article to configured Discord channel via webhook.

    When *file_path* is provided, sends the file as an attachment with
    the title as the message content.  Otherwise sends the text body,
    splitting long messages at paragraph boundaries (Discord 2000-char limit).

    Reads ``DISCORD_WEBHOOK_URL`` from environment.
    """
    webhook_url = os.environ.get("DISCORD_WEBHOOK_URL")

    if not webhook_url:
        logger.error("DISCORD_WEBHOOK_URL must be set in .env")
        return False

    if file_path:
        return _send_document(webhook_url, file_path, title=title)

    text = f"{title}\n\n{body}" if title else body
    return _send_chunks(webhook_url, text)


def _send_document(webhook_url: str, file_path: str, title: str = "") -> bool:
    """Send title as message content with ``.md`` file as attachment.

    Discord webhooks support content + file in a single multipart request.
    """
    try:
        payload: dict = {}
        if title:
            payload["content"] = title

        with open(file_path, "rb") as f:
            resp = requests.post(
                webhook_url,
                data=payload,
                files={"file": (os.path.basename(file_path), f, "text/markdown")},
                timeout=60,
            )
        resp.raise_for_status()
        logger.info("Document sent: %s", file_path)
        return True
    except requests.RequestException as e:
        logger.error("Discord webhook error: %s", e)
        return False


def _send_chunks(webhook_url: str, text: str) -> bool:
    success = True

    if len(text) <= _MAX_MSG:
        return _send_text(webhook_url, text)

    chunks = split_text(text, _MAX_MSG)
    for i, chunk in enumerate(chunks, 1):
        logger.info("Sending chunk %d/%d (%d chars)", i, len(chunks), len(chunk))
        if not _send_text(webhook_url, chunk):
            success = False

    return success


def _send_text(webhook_url: str, text: str) -> bool:
    try:
        resp = requests.post(
            webhook_url, json={"content": text}, timeout=30
        )
        resp.raise_for_status()
        return True
    except requests.RequestException as e:
        logger.error("Discord webhook error: %s", e)
        return False
