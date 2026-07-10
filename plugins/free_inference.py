"""Free inference fallback using GitHub Models (free with GitHub token)"""
import json
import os
from typing import List, Dict, Optional, Any

try:
    import aiohttp
except ImportError:
    aiohttp = None

GITHUB_TOKEN = os.environ.get("GITHUB_TOKEN", "") or os.environ.get("GH_TOKEN", "")
API_URL = "https://models.inference.ai.azure.com/chat/completions"

# Free models sorted by capability (best first)
FREE_MODELS = [
    "gpt-4o-mini",
    "meta-llama-3.1-8b-instruct",
    "mistral-large-2407",
    "AI21-Jamba-Instruct",
    "Cohere-command-r-plus-08-2024",
]

DEFAULT_MODEL = os.environ.get("FREE_INFERENCE_MODEL", "gpt-4o-mini")


def _headers() -> dict:
    h = {"Content-Type": "application/json"}
    if GITHUB_TOKEN:
        h["Authorization"] = f"Bearer {GITHUB_TOKEN}"
    return h


def is_available():
    return aiohttp is not None and bool(GITHUB_TOKEN)


async def _call_model(model: str, messages: List[Dict], temperature: float, max_tokens: int) -> Optional[Dict]:
    """Try a single model call via GitHub Models."""
    payload = {
        "model": model,
        "messages": messages,
        "temperature": temperature,
        "max_tokens": max_tokens,
        "stream": False,
    }
    async with aiohttp.ClientSession() as session:
        async with session.post(API_URL, json=payload, headers=_headers(),
                                timeout=aiohttp.ClientTimeout(total=60)) as resp:
            if resp.status == 200:
                data = await resp.json()
                return {
                    "choices": data.get("choices", []),
                    "provider": "github_models",
                    "model": model,
                }
            if resp.status in (401, 403):
                raise PermissionError(f"GitHub token invalid or insufficient for {model}")
            text = await resp.text()
            raise Exception(f"Model {model} returned {resp.status}: {text[:200]}")


async def chat_completion(
    messages: List[Dict],
    model: str = DEFAULT_MODEL,
    temperature: float = 0.7,
    max_tokens: int = 1024,
) -> Dict[str, Any]:
    """Call GitHub Models free inference, falling back through model list."""
    if not aiohttp:
        raise RuntimeError("aiohttp is required")
    if not GITHUB_TOKEN:
        raise RuntimeError("GITHUB_TOKEN not set. Create a free token at github.com/settings/tokens")

    models_to_try = [model] + [m for m in FREE_MODELS if m != model]
    last_error = None

    for m in models_to_try:
        try:
            return await _call_model(m, messages, temperature, max_tokens)
        except PermissionError:
            continue
        except Exception as e:
            last_error = e
            continue

    raise Exception(f"All free inference models failed. Last error: {last_error}")
