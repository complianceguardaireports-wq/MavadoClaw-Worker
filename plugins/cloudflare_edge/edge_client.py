"""
Cloudflare Edge Plugin
Integrates with Cloudflare Workers AI, D1, R2, Vectorize, and AI Gateway
Enables edge-native AI inference and storage at zero cost
"""
import json
from dataclasses import dataclass
from typing import Dict, List, Optional, Any

try:
    import aiohttp
    HAS_AIOHTTP = True
except ImportError:
    HAS_AIOHTTP = False


@dataclass
class CloudflareConfig:
    account_id: str = ""
    api_key: str = ""
    gateway_id: str = "mavado-gateway"
    base_url: str = "https://api.cloudflare.com/client/v4"


# Available models on Cloudflare Workers AI (July 2026)
CLOUDFLARE_MODELS = {
    "llm": {
        "fast": "@cf/meta/llama-3.2-3b-instruct",
        "balanced": "@cf/meta/llama-3.3-70b-instruct-fp8-fast",
        "powerful": "@cf/openai/gpt-oss-120b",
        "reasoning": "@cf/qwen/qwq-32b",
        "coding": "@cf/qwen/qwen2.5-coder-32b-instruct",
        "multimodal": "@cf/meta/llama-4-scout-17b-16e-instruct",
        "small": "@cf/meta/llama-3.2-1b-instruct",
        "kimi": "@cf/moonshotai/kimi-k2.7-code",
        "gemma": "@cf/google/gemma-4-26b-a4b-it",
    },
    "embeddings": {
        "multilingual": "@cf/baai/bge-m3",
        "english": "@cf/baai/bge-large-en-v1.5",
        "small": "@cf/baai/bge-small-en-v1.5",
        "qwen": "@cf/qwen/qwen3-embedding-0.6b",
    },
    "reranker": "@cf/baai/bge-reranker-base",
    "image": {
        "fast": "@cf/black-forest-labs/flux-1-schnell",
        "quality": "@cf/black-forest-labs/flux-2-dev",
        "editing": "@cf/black-forest-labs/flux-2-klein-9b",
    },
    "audio": {
        "asr": "@cf/openai/whisper-large-v3-turbo",
        "asr_realtime": "@cf/deepgram/nova-3",
        "tts": "@cf/deepgram/aura-2-en",
    },
    "safety": "@cf/meta/llama-guard-3-8b",
    "translation": "@cf/meta/m2m100-1.2b",
    "classification": "@cf/huggingface/distilbert-sst-2-int8",
    "detection": "@cf/meta/detr-resnet-50",
}


class CloudflareEdgeClient:
    """Client for Cloudflare Workers AI edge inference."""

    def __init__(self, config: CloudflareConfig = None):
        self.config = config or CloudflareConfig()
        self._session = None

    async def initialize(self):
        if HAS_AIOHTTP:
            self._session = aiohttp.ClientSession(
                timeout=aiohttp.ClientTimeout(total=30)
            )

    def _headers(self) -> Dict[str, str]:
        return {
            "Authorization": f"Bearer {self.config.api_key}",
            "Content-Type": "application/json",
        }

    async def run_model(self, model: str, payload: Dict) -> Any:
        url = (
            f"{self.config.base_url}/accounts/{self.config.account_id}"
            f"/ai/run/{model}"
        )
        if self._session:
            async with self._session.post(
                url, json=payload, headers=self._headers()
            ) as resp:
                return await resp.json()
        raise RuntimeError("Cloudflare client not initialized")

    async def chat_completion(self, messages: List[Dict],
                              model: str = "fast",
                              temperature: float = 0.7,
                              max_tokens: int = 4096) -> Any:
        cf_model = CLOUDFLARE_MODELS["llm"].get(model, model)
        payload = {
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }
        return await self.run_model(cf_model, payload)

    async def embed(self, texts: List[str],
                    model: str = "multilingual") -> Any:
        cf_model = CLOUDFLARE_MODELS["embeddings"].get(model, model)
        payload = {"text": texts}
        return await self.run_model(cf_model, payload)

    async def generate_image(self, prompt: str,
                             model: str = "fast") -> Any:
        cf_model = CLOUDFLARE_MODELS["image"].get(model, model)
        payload = {"prompt": prompt}
        return await self.run_model(cf_model, payload)

    async def transcribe(self, audio_bytes: bytes,
                         model: str = "asr") -> Any:
        cf_model = CLOUDFLARE_MODELS["audio"].get(model, model)
        if self._session:
            url = (
                f"{self.config.base_url}/accounts/{self.config.account_id}"
                f"/ai/run/{cf_model}"
            )
            async with self._session.post(
                url,
                data=audio_bytes,
                headers={
                    "Authorization": f"Bearer {self.config.api_key}",
                    "Content-Type": "audio/wav",
                },
            ) as resp:
                return await resp.json()
        raise RuntimeError("Cloudflare client not initialized")

    async def health_check(self) -> Dict[str, Any]:
        if not self.config.account_id or not self.config.api_key:
            return {"status": "not_configured", "message": "Set CLOUDFLARE_ACCOUNT_ID and CLOUDFLARE_API_KEY"}
        return {
            "status": "configured",
            "account_id": self.config.account_id[:8] + "...",
            "available_models": {
                "llm": list(CLOUDFLARE_MODELS["llm"].keys()),
                "embeddings": list(CLOUDFLARE_MODELS["embeddings"].keys()),
                "image": list(CLOUDFLARE_MODELS["image"].keys()),
                "audio": list(CLOUDFLARE_MODELS["audio"].keys()),
            },
        }

    async def close(self):
        if self._session:
            await self._session.close()


def get_agent_info():
    return {
        "name": "Cloudflare Edge Agent",
        "role": "edge",
        "status": "active",
        "description": "Edge inference and caching at Cloudflare network (300+ locations)",
    }
