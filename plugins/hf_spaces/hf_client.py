"""
HuggingFace Spaces Plugin
Manages deployment and inference via HuggingFace Spaces, ZeroGPU, and Inference API
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
class HuggingFaceConfig:
    token: str = ""
    space_name: str = ""
    inference_url: str = "https://api-inference.huggingface.co"
    hub_url: str = "https://huggingface.co/api"


class HuggingFaceClient:
    """Client for HuggingFace Spaces deployment and inference."""

    def __init__(self, config: HuggingFaceConfig = None):
        self.config = config or HuggingFaceConfig()
        self._session = None

    async def initialize(self):
        if HAS_AIOHTTP:
            self._session = aiohttp.ClientSession(
                timeout=aiohttp.ClientTimeout(total=60),
                headers={"Authorization": f"Bearer {self.config.token}"},
            )

    async def inference(self, model: str, inputs: Any,
                        parameters: Optional[Dict] = None) -> Any:
        url = f"{self.config.inference_url}/models/{model}"
        payload = {"inputs": inputs}
        if parameters:
            payload["parameters"] = parameters

        if self._session:
            async with self._session.post(url, json=payload) as resp:
                return await resp.json()
        raise RuntimeError("HF client not initialized")

    async def chat_completion(self, messages: List[Dict],
                              model: str = "meta-llama/Llama-3.3-70B-Instruct",
                              temperature: float = 0.7,
                              max_tokens: int = 4096) -> Any:
        url = f"{self.config.inference_url}/models/{model}"
        payload = {
            "inputs": messages,
            "parameters": {
                "temperature": temperature,
                "max_new_tokens": max_tokens,
            },
        }
        if self._session:
            async with self._session.post(url, json=payload) as resp:
                return await resp.json()
        raise RuntimeError("HF client not initialized")

    async def embed(self, texts: List[str],
                    model: str = "BAAI/bge-small-en-v1.5") -> Any:
        return await self.inference(model, texts)

    async def list_models(self, filter_type: str = "text-generation",
                          limit: int = 20) -> List[Dict]:
        url = f"{self.config.hub_url}/models"
        params = {"filter": filter_type, "limit": limit, "sort": "downloads"}
        if self._session:
            async with self._session.get(url, params=params) as resp:
                return await resp.json()
        return []

    async def get_space_info(self) -> Dict[str, Any]:
        if not self.config.space_name:
            return {"status": "not_configured"}
        url = f"{self.config.hub_url}/spaces/{self.config.space_name}"
        if self._session:
            async with self._session.get(url) as resp:
                return await resp.json()
        return {}

    async def health_check(self) -> Dict[str, Any]:
        return {
            "status": "configured" if self.config.token else "not_configured",
            "space_name": self.config.space_name or "not_set",
            "features": [
                "ZeroGPU (free A100 access)",
                "Inference API (1000+ models)",
                "Docker Spaces (custom deployment)",
                "Model hosting",
                "Dataset hosting",
            ],
        }

    async def close(self):
        if self._session:
            await self._session.close()


def get_agent_info():
    return {
        "name": "HF Spaces Agent",
        "role": "inference",
        "status": "active",
        "description": "HuggingFace model inference and ZeroGPU management",
    }
