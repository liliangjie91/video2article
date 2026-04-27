"""Text to speech: Markdown 文章 → 音频文件

Stub implementation. Real TTS requires an API (e.g. OpenAI TTS, Edge TTS).
"""

import os
import logging

logger = logging.getLogger(__name__)


def run(article_path: str, output_dir: str) -> str:
    """Convert article to speech. Stub — override with real TTS API call."""
    os.makedirs(output_dir, exist_ok=True)

    with open(article_path, "r", encoding="utf-8") as f:
        text = f.read()

    # Strip markdown for cleaner TTS input
    # Stub: just save the text that would be spoken
    output_path = os.path.join(output_dir, "article_tts.txt")
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(text)

    logger.warning("TTS is a stub — saved speakable text to %s", output_path)
    logger.info("To enable TTS, wire in an API call (e.g. OpenAI Audio, Edge TTS) in tts/speak.py")
    return output_path
