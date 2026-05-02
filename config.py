import configparser
import os

os.environ.setdefault("LITELLM_LOCAL_MODEL_COST_MAP", "True")
import litellm

_config = None


class ConfigError(ValueError):
    pass


def get_config():
    global _config
    if _config is None:
        _config = configparser.ConfigParser()
        _config.read(os.path.join(os.path.dirname(__file__), "config.ini"))
    return _config


def get_client_config(tier: str) -> dict:
    """Return model config for a given tier ('fast'|'best')."""
    cfg = get_config()
    model = cfg[tier]["model"]
    provider = model.split("/", 1)[0] if "/" in model else "openai"

    result: dict = {"model": model, "provider": provider}

    if provider not in litellm.LITELLM_CHAT_PROVIDERS:
        _apply_custom_provider(result, provider)

    if cfg.has_option(tier, "fallback"):
        result["fallback"] = cfg[tier]["fallback"]

    return result


def _apply_custom_provider(result: dict, provider: str):
    """Try to resolve a custom provider via convention-based env vars."""
    prefix = provider.upper()
    api_key = os.environ.get(f"{prefix}_API_KEY")
    base_url = os.environ.get(f"{prefix}_BASE_URL")

    if not api_key or not base_url:
        raise ConfigError(
            f"Unknown provider '{provider}' — litellm does not support it natively.\n"
            f"  To register, set in .env:\n"
            f"    {prefix}_API_KEY=sk-...\n"
            f"    {prefix}_BASE_URL=https://...\n"
            f"    {prefix}_API_PROTOCOL=openai   (default, for OpenAI-compatible APIs)\n"
            f"    {prefix}_API_PROTOCOL=anthropic (for Anthropic-format APIs)"
        )

    protocol = os.environ.get(f"{prefix}_API_PROTOCOL", "openai")
    result["model"] = f"{protocol}/{model_name(result['model'])}"
    result["provider"] = protocol
    result["api_key"] = api_key
    result["api_base"] = base_url


def model_name(model: str) -> str:
    """Extract the model name part from 'provider/name'. If no slash, return as-is."""
    return model.split("/", 1)[1] if "/" in model else model
