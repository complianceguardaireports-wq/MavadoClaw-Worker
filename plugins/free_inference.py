"""Free inference fallback using HuggingFace Inference API (no key required)"""
import json
from typing import List, Dict, Optional, Any

try:
    import aiohttp
except ImportError:
    aiohttp = None

# Free HuggingFace models that don't require an API key
FREE_CHAT_MODELS = {
    "phi3": "microsoft/Phi-3-mini-4k-instruct",
    "llama3.2": "meta-llama/Llama-3.2-3B-Instruct",
    "gemma2": "google/gemma-2-2b-it",
    "qwen2": "Qwen/Qwen2.5-1.5B-Instruct",
}

DEFAULT_MODEL = "microsoft/Phi-3-mini-4k-instruct"

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

async def chat_completion(
    messages: List[Dict],
    model: str = DEFAULT_MODEL,
    temperature: float = 0.7,
    max_tokens: int = 1024,
) -> Dict[str, Any]:
    """Call HuggingFace free Inference API."""
    if not aiohttp:
        raise RuntimeError("aiohttp is required")

    prompt = format_messages(messages)
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
        async with session.post(url, json=payload, timeout=aiohttp.ClientTimeout(total=60)) as resp:
            if resp.status == 200:
                data = await resp.json()
                if isinstance(data, list) and len(data) > 0:
                    text = data[0].get("generated_text", "")
                    return {
                        "choices": [{"message": {"role": "assistant", "content": text}}],
                        "provider": "huggingface_free",
                        "model": model,
                    }
                return {"choices": [{"message": {"role": "assistant", "content": str(data)}}], "provider": "huggingface_free", "model": model}
            text = await resp.text()
            raise Exception(f"HuggingFace API returned {resp.status}: {text}")
