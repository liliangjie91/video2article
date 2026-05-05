"""Telegram delivery via Bot API."""

import logging
import os

import requests

logger = logging.getLogger(__name__)

_API_BASE = "https://api.telegram.org/bot{token}"
_MAX_MSG = 4096


def deliver(title: str, body: str, file_path: str | None = None) -> bool:
    """Send article to configured Telegram chat.

    When *file_path* is provided, sends the file as a document via
    :meth:`sendDocument`.  Otherwise sends the text via :meth:`sendMessage`,
    splitting long messages at paragraph boundaries (Telegram 4096-char limit).

    Reads ``TELEGRAM_BOT_TOKEN`` and ``TELEGRAM_CHAT_ID`` from environment.
    """
    token = os.environ.get("TELEGRAM_BOT_TOKEN")
    chat_id = os.environ.get("TELEGRAM_CHAT_ID")

    if not token or not chat_id:
        logger.error(
            "TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID must be set in .env"
        )
        return False

    if file_path:
        return _send_document(token, chat_id, file_path, title=title)

    text = f"{title}\n\n{body}" if title else body
    return _send_chunks(token, chat_id, text)


def _send_document(token: str, chat_id: str, file_path: str, title: str = "") -> bool:
    """Send title as text message, then upload ``.md`` file as document."""
    msg_url = f"{_API_BASE.format(token=token)}/sendMessage"

    # Send title first for identification
    if title:
        try:
            requests.post(
                msg_url, json={"chat_id": chat_id, "text": title}, timeout=15
            )
        except requests.RequestException:
            pass  # non-critical, document is the main payload

    # Send file
    doc_url = f"{_API_BASE.format(token=token)}/sendDocument"
    try:
        with open(file_path, "rb") as f:
            resp = requests.post(
                doc_url,
                data={"chat_id": chat_id},
                files={"document": (os.path.basename(file_path), f, "text/markdown")},
                timeout=60,
            )
        resp.raise_for_status()
        logger.info("Document sent: %s", file_path)
        return True
    except requests.RequestException as e:
        logger.error("Telegram sendDocument error: %s", e)
        return False


def _send_chunks(token: str, chat_id: str, text: str) -> bool:
    url = f"{_API_BASE.format(token=token)}/sendMessage"
    success = True

    if len(text) <= _MAX_MSG:
        return _send_text(url, chat_id, text)

    chunks = _split(text)
    for i, chunk in enumerate(chunks, 1):
        logger.info("Sending chunk %d/%d (%d chars)", i, len(chunks), len(chunk))
        if not _send_text(url, chat_id, chunk):
            success = False

    return success


def _split(text: str) -> list[str]:
    """Split text into ≤4096-char chunks at paragraph boundaries."""
    chunks: list[str] = []
    current: list[str] = []
    current_len = 0

    for para in text.split("\n\n"):
        para_len = len(para) + 2  # +2 for the "\n\n" separator
        if current_len + para_len > _MAX_MSG:
            if current:
                chunks.append("\n\n".join(current))
            current = [para]
            current_len = len(para)
        else:
            current.append(para)
            current_len += para_len

    if current:
        chunks.append("\n\n".join(current))

    return chunks


def _send_text(url: str, chat_id: str, text: str) -> bool:
    try:
        resp = requests.post(
            url, json={"chat_id": chat_id, "text": text}, timeout=30
        )
        resp.raise_for_status()
        return True
    except requests.RequestException as e:
        logger.error("Telegram API error: %s", e)
        return False
