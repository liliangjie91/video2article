"""Unified LLM interface — delegates to litellm for all providers."""

import logging
import os
from datetime import datetime

from dotenv import load_dotenv
from litellm import completion

from config import get_client_config

load_dotenv()

logger = logging.getLogger(__name__)

_log_dir = None
_call_counters: dict[int, int] = {}
_current_step = 0


def set_log_dir(path: str):
    global _log_dir
    _log_dir = path
    os.makedirs(path, exist_ok=True)


def chat(prompt: str, tier: str = "fast", system: str = "You are a helpful assistant.", step: int = 0) -> str:
    """Send a prompt and return the text response. Auto-fallback on failure."""
    cfg = get_client_config(tier)
    try:
        return _do_chat(prompt, cfg, system, step)
    except Exception as e:
        if fallback := cfg.get("fallback"):
            logger.warning(
                "[LLM] %s failed (%s), falling back to %s", cfg["model"], e, fallback
            )
            fb_cfg = {"model": fallback, "provider": fallback.split("/", 1)[0] if "/" in fallback else "openai"}
            return _do_chat(prompt, fb_cfg, system, step)
        raise


def _do_chat(prompt: str, cfg: dict, system: str, step: int) -> str:
    global _current_step, _call_counters
    _current_step = step
    counter = _call_counters.get(step, 0) + 1
    _call_counters[step] = counter
    call_id = counter
    model = cfg["model"]

    logger.info("[LLM call step%d #%d] model=%s", step, call_id, model)
    _log_conversation(step, call_id, "request", f"SYSTEM:\n{system}\n\nUSER:\n{prompt}")

    kwargs = {
        "model": model,
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": prompt},
        ],
    }
    if "api_key" in cfg:
        kwargs["api_key"] = cfg["api_key"]
    if "api_base" in cfg:
        kwargs["api_base"] = cfg["api_base"]

    response = completion(**kwargs)
    result = response.choices[0].message.content

    _log_conversation(step, call_id, "response", result)
    logger.info("[LLM call step%d #%d] response length: %d chars", step, call_id, len(result))
    return result


def _log_conversation(step: int, call_id: int, kind: str, content: str):
    if not _log_dir:
        return
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"step{step}_{call_id:03d}_{kind}_{timestamp}.txt"
    filepath = os.path.join(_log_dir, filename)
    with open(filepath, "w", encoding="utf-8") as f:
        f.write(content)
