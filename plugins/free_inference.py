"""Free inference fallback using HuggingFace Inference API (token optional)"""
import json
import os
from typing import List, Dict, Optional, Any

try:
    import aiohttp
except ImportError:
    aiohttp = None

# Models that work with free Inference API (gated models marked with *)
HF_MODELS = [
    "HuggingFaceH4/zephyr-7b-beta",
    "google/gemma-2-2b-it",
    "microsoft/Phi-3-mini-4k-instruct",
    "Qwen/Qwen2.5-1.5B-Instruct",
]

DEFAULT_MODEL = os.environ.get("HF_INFERENCE_MODEL", "HuggingFaceH4/zephyr-7b-beta")
HF_TOKEN = os.environ.get("HF_TOKEN", "") or os.environ.get("HUGGINGFACE_TOKEN", "")


def _headers() -> dict:
    h = {"Content-Type": "application/json"}
    if HF_TOKEN:
        h["Authorization"] = f"Bearer {HF_TOKEN}"
    return h


def is_available():
    return aiohttp is not None


def format_messages(messages: List[Dict]) -> str:
    prompt = ""
    for msg in messages:
        role = msg.get("role", "user")
        content = msg.get("content", "")
        if role == "system":
            prompt += f"System: {content}\n"
        elif role == "user":
            prompt += f"User: {content}\n"
        elif role == "assistant":
            prompt += f"Assistant: {content}\n"
    prompt += "Assistant: "
    return prompt


async def _call_hf_model(model: str, prompt: str, temperature: float, max_tokens: int) -> Optional[Dict]:
    """Try a single HF model call."""
    url = f"https://api-inference.huggingface.co/models/{model}"
    payload = {
        "inputs": prompt,
        "parameters": {
            "temperature": temperature,
            "max_new_tokens": max_tokens,
            "return_full_text": False,
        },
    }
    async with aiohttp.ClientSession() as session:
        async with session.post(url, json=payload, headers=_headers(), timeout=aiohttp.ClientTimeout(total=120)) as resp:
            if resp.status == 200:
                data = await resp.json()
                if isinstance(data, list) and len(data) > 0:
                    text = data[0].get("generated_text", "")
                    return {"choices": [{"message": {"role": "assistant", "content": text}}], "provider": "huggingface_free", "model": model}
                return {"choices": [{"message": {"role": "assistant", "content": str(data)}}], "provider": "huggingface_free", "model": model}
            if resp.status in (401, 403):
                raise PermissionError(f"Model {model} requires auth or is gated")
            text = await resp.text()
            raise Exception(f"Model {model} returned {resp.status}: {text[:200]}")


async def chat_completion(
    messages: List[Dict],
    model: str = DEFAULT_MODEL,
    temperature: float = 0.7,
    max_tokens: int = 1024,
) -> Dict[str, Any]:
    """Call HuggingFace Inference API, falling back through model list."""
    if not aiohttp:
        raise RuntimeError("aiohttp is required")

    prompt = format_messages(messages)
    models_to_try = [model] + [m for m in HF_MODELS if m != model]

    last_error = None
    for m in models_to_try:
        try:
            return await _call_hf_model(m, prompt, temperature, max_tokens)
        except PermissionError:
            continue
        except Exception as e:
            last_error = e
            continue

    raise Exception(f"All HF models failed. Last error: {last_error}")
