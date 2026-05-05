"""Article delivery — Telegram, Discord, and more.

Each channel module exposes ``deliver(title, body, file_path=None) -> bool``.
"""

import logging
import os

from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)
