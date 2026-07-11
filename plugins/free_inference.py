"""Free inference fallback using multiple free providers (Groq, GitHub Models, etc.)"""
import json
import os
from typing import List, Dict, Optional, Any

try:
    import aiohttp
except ImportError:
    aiohttp = None


# ==================== Provider Configurations ====================
# Each provider: (name, env_var, base_url, models, default_model)

PROVIDERS = [
    {
        "name": "groq",
        "env_var": "GROQ_API_KEY",
        "base_url": "https://api.groq.com/openai/v1/chat/completions",
        "models": ["llama-3.3-70b-versatile", "llama-3.1-8b-instant", "mixtral-8x7b-32768"],
        "default": "llama-3.3-70b-versatile",
    },
    {
        "name": "github_models",
        "env_var": "GITHUB_TOKEN",
        "base_url": "https://models.inference.ai.azure.com/chat/completions",
        "models": ["gpt-4o-mini", "meta-llama-3.1-8b-instruct", "mistral-large-2407"],
        "default": "gpt-4o-mini",
        "alt_env": "GH_TOKEN",
    },
]

DEFAULT_MODEL = os.environ.get("FREE_INFERENCE_MODEL", "")


def _get_token(cfg: dict) -> str:
    token = os.environ.get(cfg["env_var"], "")
    alt = cfg.get("alt_env", "")
    if alt:
        token = token or os.environ.get(alt, "")
    return token


def is_available():
    if not aiohttp:
        return False
    for cfg in PROVIDERS:
        if _get_token(cfg):
            return True
    return False


async def _call_provider(cfg: dict, model: str, messages: List[Dict],
                         temperature: float, max_tokens: int) -> Dict:
    """Try a single model call for a given provider."""
    token = _get_token(cfg)
    headers = {"Content-Type": "application/json", "Authorization": f"Bearer {token}"}
    payload = {
        "model": model,
        "messages": messages,
        "temperature": temperature,
        "max_tokens": max_tokens,
        "stream": False,
    }
    async with aiohttp.ClientSession() as session:
        async with session.post(cfg["base_url"], json=payload, headers=headers,
                                timeout=aiohttp.ClientTimeout(total=60)) as resp:
            if resp.status == 200:
                data = await resp.json()
                return {
                    "choices": data.get("choices", []),
                    "provider": cfg["name"],
                    "model": model,
                }
            if resp.status in (401, 403):
                raise PermissionError(f"{cfg['name']} token invalid for {model}")
            text = await resp.text()
            raise Exception(f"{cfg['name']}/{model} returned {resp.status}: {text[:200]}")


async def chat_completion(
    messages: List[Dict],
    model: str = DEFAULT_MODEL,
    temperature: float = 0.7,
    max_tokens: int = 1024,
) -> Dict[str, Any]:
    """Try each configured provider in order, then fall through models."""
    if not aiohttp:
        raise RuntimeError("aiohttp is required")

    last_error = None

    for cfg in PROVIDERS:
        token = _get_token(cfg)
        if not token:
            continue

        models_to_try = [cfg["default"]]
        if model and model != cfg["default"]:
            models_to_try.append(model)
        for m in cfg["models"]:
            if m not in models_to_try:
                models_to_try.append(m)

        for m in models_to_try:
            try:
                return await _call_provider(cfg, m, messages, temperature, max_tokens)
            except PermissionError:
                continue
            except Exception as e:
                last_error = e
                continue

    raise Exception(f"All free providers failed. Last error: {last_error}")
